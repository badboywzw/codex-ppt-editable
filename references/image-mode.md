# Full-Page Image Mode

Use only for an explicit full-page AI image / image-only PDF request. New editable
PPTX decks use the project/textless-first route instead. This mode's final pages
include AI-rendered typography and are flattened.

## Plan Before Generation

Keep the deck brief, narrative chain, visual system and storyboard in the project.
Choose audience, objective, exact short copy, slide roles and varied layouts
before generating images. A topic alone can use a practical 8–12 slide structure.
Use 16:9; prefer 1920×1080 or higher. Maintain palette, typography hierarchy,
margins and image language across cover, body and closing pages.

Useful narrative chains include question → explanation → example → practice →
recap for teaching, or current state → options → evidence → recommendation →
action for decisions. Each slide needs one clear job and a dominant takeaway.

Create `prompts/slide-XX.md`, including the common visual system, subject,
composition, safe regions, exact concise on-slide copy and negative constraints.
Generate a complete slide as one AI image using the available built-in tool.
Save selected output under `slides/slide-XX-topic.png` in presentation order.

## Whole-Page Contract

Permitted after generation:

- Copy/rename the selected file into the project.
- Inspect it, record QA and create contact sheets.
- Perform non-content-changing format conversion/compression/aspect verification.
- Reject/regenerate a defective page and compile approved images into a PDF.

Do not overlay titles, body text, captions, page counters, logos, charts or
decorations with deterministic composition. Do not patch malformed words with
local drawing. Do not pad, crop or letterbox a page to rescue its aspect ratio.
The final whole-page image must remain the selected AI output.

When text is unreliable, shorten it, split the page, or improve the prompt before
regeneration. If an editable deliverable would be better, explain that option;
do not silently switch an explicit image-mode request to native text overlays.

## Review and Package

Read [slide-quality-checklist.md](slide-quality-checklist.md). Check spelling,
legibility, content coverage, anatomy/diagrams, consistency, slide order and 16:9.
Record slide status, issue, fix and final file in `qa/qa.md`. Regenerate defective
pages using the image tool; image-mode pages do not use native-text repairs.

```bash
python "${SKILL_DIR}/scripts/compile_slide_images_to_pdf.py" \
  /path/to/project/slides /path/to/project/final/deck.pdf \
  --strict --report /path/to/project/qa/compile-report.json
```

Inspect the compiled PDF for correct count/order, cropping and readability.
Deliver the images and PDF unless the user requested images only. Preserve the
source plan, prompts and QA. If the user then asks to reconstruct these existing
pages, follow [editable-pptx-mode.md](editable-pptx-mode.md).
