# Editable PPTX: Textless Artwork First

Use for new decks in the default `editable-pptx` mode. The visual strategy is `textless-first`.

The deliverable is a normal PPTX whose words can be selected and changed in PowerPoint/WPS. AI artwork supplies the visual style; native text supplies precise wording and editability. Do not promise that raster illustrations are editable internally.

## Plan Both Layers Together

For normal new decks, use [deck-project.md](deck-project.md) and its reusable CLI.
Write the brief, storyline, visual direction, theme and slide content once in
`deck.json`; generated Markdown documents are views of that source. The direct
layer schema below remains available for precise/custom or legacy compositions.
Before generating artwork, record the exact text, hierarchy, intended type size,
and reserved region for each title, paragraph, label, number, and page marker.
Allocate space from the actual copy; a background designed without accounting
for text often makes later placement crowded.

When the user asks for the previous B look, preserve its white/technology-blue
palette, dimensional illustrations, lighting, restrained technical graphics,
and spacing. Adapt the subject to the new topic rather than adding piano keys
to unrelated presentations. Typography is native and may differ from AI glyphs.

## Generate Textless Visuals Directly

Use the available built-in image-generation tool for each needed visual asset;
reuse it across pages when its subject and composition fit. Do not assume one
new AI call is necessary per page. Follow local-image inspection and save
requirements for referenced images.

- Describe the subject, composition, palette, lighting and reserved text areas.
- Explicitly exclude all words, letters, numerals, labels, page counters,
  placeholder copy, watermarks and accidental letter-like markings.
- Keep exact presentation wording in the text source, not in the image prompt.
  Describe its meaning and space instead, to avoid the model rendering it.
- For a keyboard diagram, request unlettered keys and blank number badges;
  the C–G names and finger numbers will be native text. Nonverbal music-note
  artwork can remain part of the picture.
- Inspect the result for accidental text. Repair only the affected artwork
  when necessary. Do not generate a full text-bearing page as an intermediate.
- Small decorative differences do not justify repeated image calls when the
  text area, visual meaning and required quality are already sound.

## Compose Editable Text

Keep the builder's existing layer format:

```text
editable/
  visual-layers/slide-01/background.png
  visual-layers/slide-01/manifest.json
  text-layer.json
  qa/
```

A full-page artwork manifest can be:

```json
{"assets":[{"file":"background.png","name":"Textless artwork","position":[0,0,960,540],"canvas":[960,540]}]}
```

The matching text source uses the same coordinate canvas:

```json
{
  "background":"#FFFFFF",
  "slides":[{
    "slide":1,
    "texts":[{
      "name":"title",
      "text":"Your approved title",
      "x":56,"y":48,"w":760,"h":70,
      "size":32,"typeface":"Microsoft YaHei",
      "color":"#122C54","bold":true,"align":"left"
    }]
  }]
}
```

These coordinates illustrate the schema, not a mandatory slide layout.
`size` is actual PowerPoint points, not canvas pixels. The PPTXGenJS backend
uses a 10-inch-wide output: 960 coordinate units map to 720 points. Use an
installed typeface, one text box per semantic unit, adequate wrapping headroom,
and transparent text boxes with no fill or outline. Put all linguistic labels
in this layer, including labels embedded in diagrams.

There is no image-to-text reconstruction pass in this route. Per-slide
reconstruction subagents are unnecessary; delegate only if the deck's actual
complexity warrants additional work.

## Efficient Revisions

- Give text objects stable, descriptive `name` values (for example `title`,
  `practice-duration`, or a meaningful Chinese label). These appear in the
  PowerPoint selection pane and make individual text objects easier to find.
- A wording, font, color, line-break, or position change normally changes only
  `text-layer.json`; reuse existing artwork and rebuild without image generation.
- Reuse an existing visual asset when the subject and layout genuinely recur.
  New artwork is warranted when the visual meaning or reserved region changes,
  not merely because the page number or wording changed.
- If the user edited the PPTX manually, treat that latest file as authoritative.
  Do not rebuild stale source over it. Preserve a new version or reconcile the
  manual edits first; manual PPT edits do not automatically update JSON.

## Build and Check

Resolve `SKILL_DIR` from the installed SKILL.md location. Use the installed Node
runtime and existing dependencies; no new runtime is required for this route.
The builder validates slide IDs, text-frame bounds, font sizes, manifests and
image paths before loading a rendering backend. `--check-only` runs that check
without writing a PPTX; `--out` is optional in that mode. Windows defaults to
Microsoft YaHei, macOS to PingFang SC; explicit per-object fonts take priority.

```bash
node "${SKILL_DIR}/scripts/build_editable_ppt_from_layers.mjs" \
  --backend auto \
  --layers-root /path/to/deck/editable/visual-layers \
  --text-json /path/to/deck/editable/text-layer.json \
  --out /path/to/deck/final/deck.editable.pptx \
  --workspace /path/to/deck/editable/workspace \
  --slide-size 960x540 \
  --fail-on-text-fill
```

Verify the actual exported file against its text source:

```bash
python "${SKILL_DIR}/scripts/check_editable_pptx.py" \
  --input /path/to/deck/final/deck.editable.pptx \
  --text-json /path/to/deck/editable/text-layer.json \
  --report /path/to/deck/editable/qa/editability.json
```

When LibreOffice and Poppler are available, create previews with the bundled
helper instead of reusing a potentially locked Office profile:

```bash
python "${SKILL_DIR}/scripts/render_editable_preview.py" \
  --input /path/to/deck/final/deck.editable.pptx \
  --output-dir /path/to/deck/editable/qa/preview
```

It uses a private temporary profile and
caches previews by PPTX bytes, renderer executable identity and image scale.
On Windows, pass `--temp-dir` with a short writable path on the user's preferred
drive to keep deep LibreOffice cache paths short and control temporary-file storage.
The system temporary directory is otherwise used. The Windows console launcher
is preferred when available so conversion
finishes before its private profile is removed.
Unchanged verified previews can be reused; the visual judgment is still the
agent's responsibility. A timeout is reported rather than treated as success.
Use `--soffice` / `--pdftoppm` for explicit executable paths when needed.

`--backend pptxgenjs` can use the same sources with the installed fallback
dependency. Render its PPTX with an available presentation renderer for review.

Before delivery, verify that the expected pages and approved wording are present,
semantic text exists in every slide XML, the artwork contains no corresponding
baked words, and native text remains separate from images. Inspect actual
renders for wrapping, overlap, legibility and alignment. Repair text layout in
the text source; regenerate artwork only for an artwork defect. Record material
differences and retain both sources.

Deliver the editable PPTX as the primary editing entry. Optional PDF/PNG previews
may be flattened; do not substitute them for the editable deliverable. Future
manual text edits in PowerPoint/WPS require no AI call. More text can still
require resizing its text box or changing its type size.
