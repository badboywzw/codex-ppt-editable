# Continue From a User-Edited PPTX

Use when the user supplies an editable PPTX, or has manually changed a delivered
file and asks Codex to continue. The latest saved PPTX is authoritative.

The implementation keeps an immutable package snapshot as the base. Existing
pages are not reconstructed from screenshots or from stale layout JSON. Native
text is read back into `deck.json`; requested supported edits are patched into
that original package. Additional layouts are exported separately and appended
with their own layouts/masters/media relationships.

## Commands

```bash
python "${SKILL_DIR}/scripts/deck.py" inspect-pptx /path/to/latest.pptx --slide 1
python "${SKILL_DIR}/scripts/deck.py" import-pptx /path/to/latest.pptx /path/to/new-version-project
python "${SKILL_DIR}/scripts/deck.py" build /path/to/new-version-project/deck.json --node /path/to/node
```

Use a new/empty project directory in the user's chosen workspace. `import-pptx` copies the saved input
to `source/original.pptx`, records its checksum and captures native text shape
IDs, names, current wording, available positions and style. It never overwrites
the user's input or claims to recover words baked into images. `--title` can set
the project/output title. Read `qa/import-report.json` for counts and limitations.

No image generation is needed to import or continue native pages. When the
request is only to add a slide, append its layout under `slides`; leave the
`base` section alone. Keep the existing pictures, tables, charts, notes,
transitions and other package objects. The output is a separate `*-续作.pptx`.
Inspect the actual exported previews before delivering it.

## Editing Readback Fields

Each `base.slides` entry identifies an original slide `part` in actual display
order. Its `texts` entries use the stable per-slide shape `id`; names are helpful
labels, not unique identifiers. Supported edits are:

- `text`: ordinary uniformly formatted native text. Empty text clears its words.
- `x`, `y`, `w`, `h`, `rotation`: explicit ungrouped shape geometry. Coordinates
  use a width-960 canvas scaled from the base's physical dimensions.
- `size` (PowerPoint points), `typeface`, `color` (`#RRGGBB`), `bold`, `italic`,
  `align` (`left`, `center`, `right`, `justify`) and object `name`.

Unspecified fields/shapes/slides are retained, not deleted. Sparse edits can
identify only the desired slide part, shape ID and changed fields. `null` style
values mean inherited or mixed properties; leaving them unchanged preserves the
original XML. Setting an explicit style applies that requested property to the
whole selected text box, leaving other properties alone.

`text_editable:false` marks field-based/mixed-run text whose replacement needs
specialized handling to avoid losing rich formatting. It remains intact when
untouched. Geometry with `position_editable:false` is grouped/inherited and is
read-only in this first importer. Do not silently flatten rich objects or rebuild
them as approximate images. Use direct specialized edits for such exceptions.

## Appending Pages

Use the standard layout schema from [deck-project.md](deck-project.md):

```json
"slides":[
  {"id":9,"layout":"bullets","title":"Next practice",
   "bullets":["Review one problem","Practice slowly"]}
]
```

The new page marker starts after the base's page count. Existing page-marker
text is preserved; update those native fields deliberately if a new total should
be shown there. Appending currently uses `pptxgenjs` and a 16:9 base; physical
width is matched to the original (including ordinary 13.333-inch wide decks).
Native text-only patching keeps other aspect ratios unchanged.

`editable/append-text-layer.json` describes new pages; `editable/text-layer.json`
describes expected text across the complete continued deck. Export checks use
the PPTX's presentation order, so user-reordered pages stay in that order.
Original text-box fills may be retained; new generated text stays transparent.

## Preservation and Checks

- The copied source checksum is checked before builds. If it changes, import the
  latest saved file into a new project; do not retarget IDs onto another file.
- Without requested base edits, original slide, media, master and theme part
  bytes remain unchanged. With native edits, only the affected slide XML changes.
- Appending adds new dependency parts and updates presentation/content-type
  records; it does not overwrite existing media/layout/theme files with matching
  filenames. Internal package relationships are checked before output is saved.
- Fresh master/layout resource IDs avoid collisions with existing resources.
  Empty auto-generated notes on appended pages are omitted; existing user notes
  and any nonempty added notes remain preserved.
- Existing user-edit protection, successful-stage reuse, preview generation and
  visual QA remain in effect. Manually changed output should become the next
  import base rather than being overwritten from an older project.

This is saved-file readback, not live synchronization with an open Office window.
Image-only pages stay image-only unless the user requests the reconstruction route.
Signed/encrypted or unsupported complex edits require specialized handling;
preserve the input and explain the actual limitation if encountered.
