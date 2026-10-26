"""Render PPTX previews with a private LibreOffice profile and verified cache."""
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from zipfile import ZipFile
from project_io import ResourceLock,atomic_copy,atomic_json
from pptx_package import ordered_slide_parts

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def executable(explicit, names, fallback=None):
    if explicit:
        target = Path(explicit).resolve()
        if target.is_file():
            return str(target)
        raise FileNotFoundError(target)
    for name in names:
        target = shutil.which(name)
        if target:
            return target
    if fallback and Path(fallback).is_file():
        return fallback
    raise FileNotFoundError(f'Missing executable: {names[0]}')

def run(command, timeout, env):
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace', env=env, creationflags=flags)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # This PID belongs to the private conversion started immediately above.
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        else:
            process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        raise RuntimeError(f'{Path(command[0]).name} timed out after {timeout}s') from None
    if process.returncode:
        raise RuntimeError(f'{Path(command[0]).name} failed: {(stderr or stdout).strip()[:1000]}')

def renderer_identity(args):
    soffice=executable(args.soffice,['soffice.com','soffice','libreoffice'] if os.name=='nt' else ['soffice','libreoffice'],
                       'F:/codex/tools/LibreOffice/program/soffice.exe')
    if os.name=='nt' and Path(soffice).name.lower()=='soffice.exe' and Path(soffice).with_suffix('.com').is_file():
        soffice=str(Path(soffice).with_suffix('.com'))
    poppler=executable(args.pdftoppm,['pdftoppm'])
    return {'tools':[{'path':str(Path(t).resolve()),'mtime_ns':Path(t).stat().st_mtime_ns} for t in [soffice,poppler]],
            'scale':args.scale,'renderer_protocol':3}

def _render(args):
    source = args.input.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    renderer=renderer_identity(args)
    soffice,poppler=[t['path'] for t in renderer['tools']]
    with ZipFile(source) as package: count=len(ordered_slide_parts(package))
    selected=None
    if getattr(args,'pages',None):
        pieces=str(args.pages).split(',')
        if any(not p.isdigit() for p in pieces): raise ValueError('--pages requires ascending comma-separated page numbers')
        selected=[int(p) for p in pieces]
        if selected!=sorted(set(selected)) or any(p<1 or p>count for p in selected):
            raise ValueError('--pages contains duplicate, out-of-range or unordered numbers')
    identity = {'pptx_sha256': digest(source), **renderer, 'selected_pages':selected}
    receipt = output / 'preview-report.json'
    if receipt.exists():
        try: old = json.loads(receipt.read_text(encoding='utf-8'))
        except (OSError,ValueError): old={}
        if old.get('identity') == identity and old.get('files') and all(
            Path(item['path']).is_file() and digest(Path(item['path'])) == item['sha256']
            for item in old['files']):
            return {'cached':True,'pdf':old['pdf'],'pages':old['pages'],'selected_pages':selected}
    # Different source/render settings use a different artifact folder, preventing stale pages.
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    artifacts = output / f'render-{key}'
    artifacts.mkdir(exist_ok=True)
    # LO creates deeply nested extension-cache paths; long deck folders can
    # exceed Windows path limits even after conversion has finished.
    temporary = (args.temp_dir or Path(gettempdir()) / 'codex-ppt').resolve()
    temporary.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='lo-', dir=temporary) as temporary_path:
        profile = Path(temporary_path).resolve()
        if temporary.resolve() not in profile.parents:
            raise RuntimeError('Preview profile escaped the selected temporary directory')
        env = dict(os.environ, TEMP=str(profile), TMP=str(profile), TMPDIR=str(profile))
        # LibreOffice can stall on long/Unicode source and conversion paths.
        # Stage both ends under the short private directory; only Python copies
        # completed files back to the user's project path.
        staged = profile / 'source.pptx'
        converted = profile / 'render'
        converted.mkdir()
        shutil.copy2(source, staged)
        if digest(staged)!=identity['pptx_sha256']: raise RuntimeError('PPTX changed during preview staging')
        # Official PDF CLI filter: https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html
        options={'ExportHiddenSlides':{'type':'boolean','value':'true'}}
        if selected: options['PageRange']={'type':'string','value':','.join(map(str,selected))}
        pdf_filter='pdf:impress_pdf_Export:'+json.dumps(options,separators=(',',':'))
        run([soffice, '-env:UserInstallation=' + profile.as_uri(), '--headless', '--convert-to',
             pdf_filter, '--outdir', str(converted), str(staged)], args.timeout, env)
        staged_pdf = converted / 'source.pdf'
        if not staged_pdf.is_file() or not staged_pdf.stat().st_size:
            raise RuntimeError('LibreOffice did not produce a PDF')
        pdf = artifacts / source.with_suffix('.pdf').name
        atomic_copy(staged_pdf, pdf)
        run([poppler, '-jpeg', '-scale-to', str(args.scale), str(staged_pdf), str(converted / 'slide')], args.timeout, env)
        staged_pages = sorted(converted.glob('slide-*.jpg'), key=lambda p: int(p.stem.rsplit('-', 1)[1]))
        pages = []
        if len(staged_pages)!=(len(selected) if selected else count):
            raise RuntimeError('Renderer did not honor the requested page selection')
        for index,page in enumerate(staged_pages):
            target = artifacts / (f'slide-{selected[index]}.jpg' if selected else page.name)
            atomic_copy(page, target)
            pages.append(target)
    if not pages:
        raise RuntimeError('No preview pages were rendered')
    report = {'identity': identity, 'pdf': str(pdf), 'pages': [str(p) for p in pages],
              'files': [{'path': str(p), 'sha256': digest(p)} for p in [pdf, *pages]],
              'visual_review': 'Not performed by this script; review these page images before delivery.'}
    if digest(source)!=identity['pptx_sha256']: raise RuntimeError('PPTX changed while its preview was rendering')
    atomic_json(receipt,report)
    return {'cached':False,'pdf':str(pdf),'pages':report['pages'],'selected_pages':selected}

def render(args):
    with ResourceLock(args.output_dir,'preview'):
        return _render(args)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--soffice')
    parser.add_argument('--pdftoppm')
    parser.add_argument('--temp-dir', type=Path)
    parser.add_argument('--pages',help='Export only these ascending page numbers, e.g. 2,5')
    parser.add_argument('--scale',type=int,default=1600)
    parser.add_argument('--timeout',type=int,default=45)
    args=parser.parse_args()
    if args.scale<=0 or args.timeout<=0: parser.error('Scale and timeout must be positive')
    print(json.dumps(render(args),ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
