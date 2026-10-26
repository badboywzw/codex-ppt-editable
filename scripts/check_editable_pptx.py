"""Verify editable text and source retention using only Python's standard library."""
from pathlib import Path
from collections import Counter
import argparse
import json
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pptx_package import ordered_slide_parts

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

def normalized(text):
    return re.sub(r'\s+', '', str(text or ''))

def check(pptx_path, text_json, preserved_slides=0):
    spec = json.loads(text_json.read_text(encoding='utf-8-sig'))
    sources = spec.get('slides', [])
    errors, records = [], []
    with ZipFile(pptx_path) as package:
        corrupt = package.testzip()
        if corrupt:
            errors.append(f'Corrupt ZIP member: {corrupt}')
        files = ordered_slide_parts(package)
        if len(files) != len(sources):
            errors.append(f'Slide count differs: PPTX={len(files)}, source={len(sources)}')
        for position, (file, source) in enumerate(zip(files, sources), 1):
            root = ET.fromstring(package.read(file))
            actual = []
            opaque = []
            for shape in root.findall('.//p:sp', NS):
                text = ''.join(node.text or '' for node in shape.findall('.//a:t', NS))
                if not text.strip():
                    continue
                actual.append(normalized(text))
                fill = shape.find('p:spPr/a:solidFill', NS)
                if fill is not None:
                    alpha = fill.find('.//a:alpha', NS)
                    if alpha is None or int(alpha.get('val', '100000')) > 0:
                        opaque.append(text[:60])
            expected = Counter(normalized(item.get('text')) for item in source.get('texts', [])
                               if normalized(item.get('text')))
            missing = list((expected - Counter(actual)).elements())
            extra = list((Counter(actual) - expected).elements())
            if missing:
                errors.append(f'Slide {position}: missing or changed text: {missing[:5]}')
            if extra:
                errors.append(f'Slide {position}: unexpected text: {extra[:5]}')
            if opaque and position > preserved_slides:
                errors.append(f'Slide {position}: opaque text-box fills: {opaque[:5]}')
            records.append({'page': position, 'source_slide': source.get('slide', position),
                            'native_text_objects': len(actual), 'pictures': len(root.findall('.//p:pic', NS)),
                            'missing_text': missing, 'extra_text': extra, 'opaque_text_boxes': opaque})
    return {'passed': not errors, 'slides': records, 'errors': errors,
            'native_text_objects': sum(r['native_text_objects'] for r in records),
            'visual_review_required': 'Inspect rendered slides and artwork separately; XML checks cannot detect words baked into pixels or prove visual fit.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--text-json', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--preserved-slides', type=int, default=0,
                        help='Retained native base pages may keep their user-defined text-box fills')
    args = parser.parse_args()
    report = check(args.input, args.text_json, args.preserved_slides)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'slides': len(report['slides']),
                      'native_text_objects': report['native_text_objects'], 'errors': report['errors']}, ensure_ascii=False))
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
