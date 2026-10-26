# Reusable Deck Projects

Use this route for a new editable deck. Export uses Python's standard library
and the installed Node/PPTX builder. Incremental previews use LibreOffice,
Poppler and the bundled `pypdf` library. The CLI never calls an image API,
installs dependencies, or regenerates artwork.

## Entry Points

Resolve `SKILL_DIR` from SKILL.md. Use the bundled Python/Node runtime paths when
they are not on PATH. Create a new project folder in the user's chosen workspace.

```bash
python "${SKILL_DIR}/scripts/deck.py" init /path/to/new-project --title "My topic"
python "${SKILL_DIR}/scripts/deck.py" layouts
python "${SKILL_DIR}/scripts/deck.py" plan /path/to/new-project/deck.json
python "${SKILL_DIR}/scripts/deck.py" build /path/to/new-project/deck.json --node /path/to/node
```

`init` creates an ownership marker and copies a working example. Replace its
content in `deck.json` before authoring the requested deck. `--example FILE`
accepts another schema-v1 JSON. An existing nonempty folder is not overwritten.

`plan` writes derived files and lists missing artwork without calling AI. Generate
the missing artwork using the built-in tool, inspect it, and copy it to the
listed asset path. `build` then prepares sources, exports, checks native text,
and renders previews in one invocation. `--no-preview` skips rendering explicitly
for diagnostics/tests; it does not satisfy final visual QA.

## Single Source

Write exact copy and design decisions once in `deck.json`. Brief, storyline,
design-system, storyboard, prompts, `editable/text-layer.json` and layout graphics
are generated views; do not maintain separate copies by hand in this route.
Keep layout-specific escapes in the same JSON rather than writing Python per deck.

```json
{
  "schema_version": 1,
  "title": "A practical first lesson",
  "audience": "Beginners",
  "objective": "Complete one small exercise",
  "language": "en",
  "storyline": "Orient → demonstrate → practice → review",
  "visual_direction": "White and technology blue, dimensional artwork, generous space",
  "theme": {"blue":"#166BFF","navy":"#0B2148"},
  "assets": {
    "hero": {
      "file":"assets/hero.png",
      "prompt":"Sculptural 3D subject on the right half, white background, left half and top margin empty"
    }
  },
  "slides": [
    {"id":1,"layout":"hero","title":"A practical first lesson",
     "subtitle":"Start small and build confidence","artwork":"hero",
     "bullets":["One concept","One exercise"],"takeaway":"Practice, then review."},
    {"id":2,"layout":"steps","title":"A repeatable routine",
     "steps":[{"title":"Observe","description":"Name the key idea"},
              {"title":"Practice","description":"Try it slowly"},
              {"title":"Review","description":"Choose one improvement"}]}
  ]
}
```

Theme keys: `font`, `background`, `navy`, `blue`, `ink`, `ice`, `rule`, `grid`,
`stripe`. Colors are `#RRGGBB`. Fonts default to Microsoft YaHei on Windows,
PingFang SC on macOS, Arial elsewhere. Coordinates are 960×540; sizes are actual
PowerPoint points. Output is 16:9. `filename` optionally sets the output basename.

## Layout Data

All slides require a unique positive integer `id`, a `title` and `layout`.
`subtitle`, `role`, `takeaway` and `risk` are optional planning fields; `takeaway`
is displayed by hero/bullets/steps/closing. `page_number:false` disables the
generated page marker. Keep a single idea per slide, varying layouts as useful.

| Layout | Content fields | Typical use |
| --- | --- | --- |
| `hero` | `subtitle`, `eyebrow`, `bullets` (up to 3), `takeaway` | Cover with right-side artwork |
| `bullets` | `sections:[{heading,items}]` (1–3), or `bullets:[strings]` | Explanation; optional right artwork |
| `columns` | `columns:[{heading,items}]` (2–3) | Side-by-side comparisons |
| `steps` | `steps:[{title,description,value}]` (2–5) | Stages; optional duration/KPI values |
| `timeline` | `events:[{title,description,value}]` (2–5) | Alternating chronological events |
| `matrix` | `headers:[strings]` (2–6), `rows:[[values]]` (1–7) | Compact table; native cell text |
| `closing` | `items:[{heading,body}]` (1–4), `takeaway` | Checklist/action closing |
| `custom` | `texts:[native frames]`, `visuals:[positioned assets]` | Precise diagrams or exceptions |

`artwork:"asset-id"` places a full-slide textless asset below the layout. For
hero/closing reserve the left area for copy; bullets with artwork uses a left
column. The script does not infer an image's composition. Plan it deliberately.
Header-only layouts such as matrix/columns do not automatically leave a right
hero region; use custom asset placement when artwork could collide with content.

Any slide can add positioned artwork:

```json
"visuals":[{"asset":"diagram","position":[480,180,400,250]}]
```

Assets use safe IDs (`hero`, `diagram-1`, etc.), PNG/JPEG/SVG files and paths
relative to deck.json, preferably under `assets/`. Absolute read paths are also
accepted. Assets are copied into the project's derived layer files and are not
rewritten when unchanged. Only assets actually used by slides are required.
Layout SVG contains no words; linguistic content is native text. Table borders
and other SVG graphics remain image objects, not native editable chart shapes.

For a custom slide, text frames follow the lower-level builder schema:

```json
{"id":3,"layout":"custom","title":"Precise example","page_number":false,
 "texts":[{"name":"diagram-label","text":"Editable label",
           "x":48,"y":48,"w":600,"h":70,"size":28,"bold":true}],
 "visuals":[{"asset":"diagram","position":[0,0,960,540]}]}
```

Custom titles are planning metadata; put the actual native title frame in
`texts`. Avoid duplicate page markers when importing existing native text.
Do not add fill/outline to native text to conceal baked wording. Graphic source
assets must be textless in the corresponding linguistic regions.

## Caching, Recovery and User Edits

See [resume-and-cache.md](resume-and-cache.md) for project/output locks, atomic
state publication and per-page invalidation. These are enabled automatically.
The default backend exports only changed pages; previews render only invalidated
pages and combine their PDFs with cached pages. The complete PPTX is repackaged
for delivery. Reports list the exact exported/rendered page positions.

The CLI records successful export hashes before previewing. Unchanged text,
layouts, used asset bytes and engine code reuse the exported file. The preview
helper separately checks its source hash, renderers and actual cached files.
Conversion stages the input and output under a short private path before copying
completed previews back, avoiding LibreOffice's long/Unicode-path stalls.
If rendering fails, fix the renderer/path issue and rerun the same command;
the checked PPTX need not be rebuilt. Logs/state live under `qa/`.

The CLI refuses to overwrite a PPTX changed outside its pipeline or an untracked
existing file. Continue the latest user-edited file through
[native-pptx-mode.md](native-pptx-mode.md) and `import-pptx`. `--out NEW_NAME.pptx`
can create an intentionally separate fresh export; it does not recover manual
changes from a different file.

Options: `--node`, `--out`, `--backend pptxgenjs|auto|artifact`, `--soffice`,
`--pdftoppm`, `--temp-dir`, `--scale`, `--timeout`, `--no-preview`.
Default backend is the installed PPTXGenJS builder. Temporary preview profiles
default to a short `.skill-install-temp/ppt` folder beside the skills installation
root; override with a short writable path on the user's preferred drive if needed.

## Delivery Check

`build` reports exported text verification, not visual approval. Layout warnings
are rough size estimates, not exact font measurement or automatic long-text
fitting. Read the rendered pages and fix wrapping/overlap as needed. Use native
text/position changes without image calls; use artwork edits only for visual
defects. Do not force the library onto a layout it cannot express: use custom
frames or the existing lower-level builder, retaining the same textless contract.

Deliver `final/*.pptx` as the editing entry, optional PDF/JPG previews, and retained
sources. Review status belongs in `qa/qa.md`. Do not replace a user-delivered deck
with a test artifact created solely to validate the skill.
