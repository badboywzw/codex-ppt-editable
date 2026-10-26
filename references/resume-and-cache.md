# Interrupted Runs, Concurrency and Page Caches

These protections are enabled by the `deck.py` project entry for `init`,
`import-pptx`, `plan` and `build`. Use that entry to publish a project, rather than
running multiple low-level assembly tools against the same delivery path.

## Concurrency

One mutating command at a time owns the project. Builds also lock the output
path, so different projects cannot concurrently publish the same PPTX. Preview
generation has its own resource lock, including standalone preview-helper runs.

The operating system owns the lock. Normal exit or termination of the actual
holding process releases it; leftover diagnostic files are not live locks.
Do not infer lock ownership from PID age or delete lock files to force entry.
`Project busy` / `Output busy` means another holder is still active. Wait for it
to exit and rerun. If terminating a process for an authorized diagnostic, verify
it is your own actual worker; Windows launchers/shells can have separate PIDs.

Sidecars are small files under `.codex-ppt-locks` beside the selected resource.
New-project/import scaffolds are prepared in a private sibling directory and
published as a complete directory, so interruption does not expose a half-project.

## Atomic Publication and Recovery

Derived text/asset files, JSON state and cache receipts are written to sibling
temporary files, flushed, then atomically replaced. Cached-page receipts appear
only after native text has passed validation and the file checksum is recorded.

A final PPTX is checked in a private file before publication. A flushed intent
under `qa/publications` links the old/new hashes and the next state. If a process
stops between replacing the PPTX and committing its state, the next build repairs
that state from the matching journal. A checked staged export can also resume
when the source and previous output still match.

If the user changes the input or output meanwhile, an old staged file is not
blindly published. Manual PPT edits remain authoritative and use the native
import route. A source JSON change during an active build stops stale publication.
Successful page caches remain usable after a later page/export/preview failure.

## What Is Cached

The default `pptxgenjs` backend caches checked single-page PPTX files under
`editable/page-cache`. Keys include native text, visual bytes/placement, physical
size and generation/runtime identity. Only changed/missing/corrupt entries are
exported. Imported base pages are preserved as package objects; added pages use
the same cache. Other explicit backends retain their normal full export path.

The final PPTX is still assembled into one complete, atomic delivery file.
Page caching avoids repeating page authoring/export; it does not patch a ZIP
container in place or overwrite a manually changed output.

Preview PDFs/JPGs are cached per page under `editable/preview-cache`. The key
tracks visible XML, image/layout/master/theme dependencies, relevant global
styles and renderer settings, independent of ZIP timestamps and allocated media
filenames. Notes and cross-slide navigation do not pull unrelated page content
into that page's visual key. Slide-number fields and time fields include their
rendering context in invalidation.

All missing pages are exported as one LibreOffice `PageRange` batch, split into
single-page PDFs, then joined with the existing cached PDFs in the current page
order. The bundled `pypdf` library performs PDF splitting/assembly; no image API
is used. Short private staging paths avoid LibreOffice Unicode/long-path stalls.
QA previews include hidden slides so their count/order matches the full deck.

Shared artwork changes invalidate every referencing page. Theme/font changes,
page numbering changes or other shared dependencies can invalidate multiple
pages. Per-project caches do not transfer automatically to a fresh import project.
Derived caches can be removed between runs; missing entries will be regenerated.

## Evidence

`qa/pipeline-report.json` includes:

- `exported_pages`, `export_cache_hits`: logical positions authored/reused this run.
- `preview.rendered_pages`, `preview.preview_cache_hits`: positions actually
  sent to the renderer versus reused previews.
- `build_cached`, `preview.cached`: complete artifact reuse when applicable.
- `recovery`: an interrupted publication repaired on this run, when applicable.

Checksums validate reused files. A corrupt image/PDF invalidates that page only.
Automated status remains separate from preserved human notes in `qa/qa.md`;
cached success is not a new visual approval. Inspect changed pages before delivery.
