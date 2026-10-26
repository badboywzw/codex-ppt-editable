---
name: codex-ppt
description: >-
  Create polished 16:9 decks from a topic, outline, report, or notes, and continue user-edited PPTX files while preserving existing pages. Default to textless AI artwork and native editable text; also reconstruct slide images or create image-only decks when requested. Use for 做PPT, 修改PPT, 追加幻灯片, presentations, slide decks, or editable PowerPoint output.
---

# Codex PPT

Deliver an editable PPTX by default. New decks combine directly generated
textless artwork with native PowerPoint text. The PPTX is the user's editing
entry in PowerPoint/WPS; raster picture internals need not be editable.

## Choose the Route

Read only the relevant reference:

- **New editable deck:** [deck-project.md](references/deck-project.md).
  Prefer the reusable project CLI and layouts over writing a deck-specific
  generator. Exact copy, theme, storyline and layout choices live in `deck.json`.
- **New artwork or precise custom composition:** also read
  [textless-first-mode.md](references/textless-first-mode.md).
- **Continue a user-edited / existing editable PPTX:**
  [native-pptx-mode.md](references/native-pptx-mode.md). Import the latest saved
  file as a preserved base, read its native text/style, and patch or append there.
- **Existing slide images / image-only PPTX:**
  [editable-pptx-mode.md](references/editable-pptx-mode.md). Reconstruct the
  existing material; do not generate a new text-bearing page first.
- **Explicit full-page image / image-only PDF request:**
  [image-mode.md](references/image-mode.md). Its whole-page AI contract applies
  only to that mode.

## New-Deck Workflow

1. Use the user's brief and sources; infer routine choices. Default to 16:9,
   the user's language, and 8–12 slides if no length is specified.
2. Initialize a new project with `scripts/deck.py init`, then write `deck.json`:
   audience, objective, storyline, theme, exact copy and varied slide layouts.
   The CLI generates brief/storyboard/style documents from this single source.
3. Run `plan`. It prepares native text, textless layout graphics, asset manifests
   and prompts, and lists missing artwork. Generate only the needed artwork
   with the built-in image tool, inspect it, and save it at the planned path.
   Reuse a visual when its subject and composition remain appropriate.
4. Run `build` to plan, export, verify native text, and render previews. The
   default backend caches individual pages and renders only invalidated pages.
   Project/output locks and atomic publication protect concurrent/interrupted
   runs; rerun the same command to recover checked work.
5. Read [slide-quality-checklist.md](references/slide-quality-checklist.md)
   and inspect the actual renders. Fix native text layout in the source and
   regenerate images only for artwork defects. Record visual review in `qa/qa.md`.

Resolve script paths from this SKILL.md. Locate installed runtimes through
`load_workspace_dependencies` when available; otherwise use configured Python,
Node and renderer paths. Use existing dependencies and honor the user's chosen
drive and workspace for skill files, project output, caches and temporary files.

## Essential Invariants

- Plan text regions before generating artwork. Titles, body copy, labels,
  numbers, letters and page markers are transparent native text objects.
- Do not bake words into a new editable page and erase them afterward.
  Do not cover old words with rectangles and call the result editable.
- Simple accurate diagrams can use textless SVG; AI illustrations provide the
  visual character. Do not replace requested rich artwork with generic boxes.
- Keep a coherent palette, type hierarchy, spacing and image language. Choose
  layouts from the content; the library is reusable components, not a mandatory
  sequence. Use `custom` or the lower-level builder for precise exceptions.
- Text-only revisions reuse artwork. Do not spawn reconstruction workers or
  make image calls merely to change words, type, color or position.
- The latest user-edited PPTX is authoritative. Use `import-pptx` to continue it;
  do not regenerate stale JSON into a new filename and treat that as preserving
  the user's changes. Manual edits are read back when importing the saved file.
- Preserve source JSON, artwork, prompts, native text/layer files and QA evidence.
  Preview PDF/JPG files may be flattened; deliver the PPTX as the editable file.
- Automated checks do not prove visual quality or detect words inside pixels.
  Review page count/order, approved copy, wrapping, overlap and artwork before
  delivery. Do not claim scripts performed that visual review.

## Tools

- `scripts/deck.py`: `init`, `layouts`, `plan`, `build`, `inspect-pptx`, `import-pptx`.
- `scripts/deck_layouts.py`: shared layouts and native text-frame composition.
- `assets/examples/starter.json`: working, offline project example.
- `scripts/build_editable_ppt_from_layers.mjs`: lower-level/custom assembly.
- `scripts/check_editable_pptx.py`: source/native-text retention and fill checks.
- `scripts/render_editable_preview.py`: cached private-profile PDF/JPG previews.
- `scripts/pptx_edit.py` / `pptx_package.py`: native readback, sparse edits and
  dependency-preserving continuation of existing PPTX packages.
- `scripts/project_io.py` / `slide_cache.py`: kernel locks, atomic checkpoints,
  per-page exports and selective preview caching; see
  [resume-and-cache.md](references/resume-and-cache.md) when diagnosing a run.
- Reconstruction merge and full-page PDF tools are documented in their routes.
