---
name: codex-ppt
description: Create polished 16:9 presentation decks as fully AI-rendered image-based PDF deliverables from a topic, outline, report, or rough notes. Use when the user asks to 自动做PPT, 做PPT, 生成PPT, make slides, create a slide deck, create a fully AI-generated image-based deck, or produce a presentation by first planning the narrative chain, deciding every slide including cover and closing pages, locking a unified style and layout system, generating each complete slide page as one AI-created bitmap image including layout, text, charts, and visuals, checking and regenerating weak pages, then combining the final slide images into one PDF.
---

# Codex PPT

Create a complete presentation as ordered 16:9 slide images, then compile them into one PDF. The skill is for deck-making where planning, visual consistency, full-page AI generation, quality review, and PDF delivery all matter.

## Default Assumptions

- Output is a single PDF composed of full-slide images.
- Preserve the working files: brief, storyline, design system, storyboard, prompts, generated images, QA notes, and final PDF.
- Use 16:9 throughout. Prefer 1920x1080 PNGs unless the user asks for another 16:9 size.
- Default language follows the user's request; use Chinese when the user asks in Chinese.
- If the user gives only a topic, choose a practical 8-12 slide structure.
- Generate each final slide as one complete AI-created page image. The AI image must include the background, layout, typography, diagrams, icons, charts, and on-slide text in the same generated bitmap.
- Keep on-slide copy short enough for the image model to render. If exact text becomes unreliable, shorten, split, or re-prompt the slide instead of adding deterministic text afterward.

## Required Outcome

A successful run leaves behind:

1. A compact deck brief
2. A clear narrative chain
3. A unified visual style and layout system
4. A slide-by-slide storyboard covering cover, body, and closing pages
5. One generation prompt per slide
6. A complete set of final 16:9 slide images, each sourced from full-page AI generation
7. A QA log showing which pages passed or were regenerated
8. A final PDF compiled from the approved slide images

## Hard Constraints

- Do not generate slide images before the narrative chain, design system, and storyboard are written.
- Do not create final pages by generating a background and then adding text, shapes, charts, icons, screenshots, logos, arrows, or layout elements with HTML/CSS, canvas, Pillow, Keynote, PowerPoint, SVG, or any deterministic renderer.
- Do not use local composition to fix malformed text. Rewrite the prompt and regenerate the full slide page.
- Do not accept any final slide unless the whole visible page is the AI-generated output, apart from non-content-preserving file operations such as copying, format conversion, compression, or strict 16:9 verification.
- Do not treat "pretty images" as sufficient; each slide must have a job in the deck.
- Do not let each slide drift into a different style. Reuse the same visual system, margins, type hierarchy, and image language.
- Do not accept malformed AI-rendered text. Regenerate, shorten, split, or simplify the slide until the AI-rendered page is acceptable.
- Do not crop away important slide content when compiling to PDF.
- Do not deliver before checking page order, page count, aspect ratio, legibility, and content coverage.

## Full-Page AI Generation Contract

Treat every slide as a finished image-generation target, not as a canvas for later assembly.

Allowed after AI generation:

- copy or move the generated file into the workspace
- rename files into slide order
- inspect images and create QA notes/contact sheets
- convert formats without changing visible content
- reject and regenerate slides
- compile approved slide images into PDF

Not allowed for final slide images:

- overlaying or redrawing titles, subtitles, body copy, page numbers, logos, charts, UI, arrows, frames, or captions
- compositing AI backgrounds with locally rendered text
- repairing text with local drawing tools
- using a deterministic slide renderer as the source of the final image
- adding padding, letterboxing, or decorative borders to rescue the aspect ratio

If a slide cannot pass because the AI model keeps rendering text poorly, reduce the text, make the slide more visual, split it into multiple slides, or ask the user to approve a different delivery mode. Do not silently switch to deterministic text composition.

## Workflow

### Phase 0. Create the Deck Workspace

Create a named folder for the deck. Recommended structure:

```text
deck-name/
├── brief.md
├── storyline.md
├── design-system.md
├── storyboard.md
├── prompts/
├── slides/
├── qa/
└── final/
```

Write `brief.md` with:

- topic
- target audience
- objective
- desired slide count
- language
- tone
- must-include content
- constraints and source materials

If crucial inputs are missing and cannot be safely inferred, ask only the minimum question needed. Otherwise proceed with explicit assumptions.

### Phase 1. Plan the Narrative Chain

Write `storyline.md` before thinking about page visuals.

Use a chain such as:

```text
Hook -> Context -> Tension -> Key Insight -> Solution / Argument -> Evidence -> Implications -> Action / Closing
```

Adapt the chain to the deck type:

- Sales: pain -> cost -> new way -> proof -> offer -> next step
- Strategy: current state -> pressure -> options -> decision logic -> roadmap -> ask
- Education: curiosity -> concept -> examples -> practice -> recap
- Product: user problem -> product idea -> workflow -> differentiators -> trust -> call to action
- Report: question -> method -> findings -> interpretation -> recommendation

### Phase 2. Lock the Visual System

Write `design-system.md` before slide prompts.

Include:

- visual atmosphere
- color palette with roles
- typography direction and hierarchy
- recurring grid, margins, and safe areas
- cover layout
- section divider layout if needed
- body slide layout variants
- chart/data treatment
- image style
- icon/illustration style
- footer/page-number rules
- negative prompt and anti-patterns

Keep the design system specific enough to paste into every slide prompt. Avoid generic one-note palettes, default gradients, visual clutter, and decorative elements that do not support the deck's story.

### Phase 3. Build the Storyboard

Write `storyboard.md` as the source of truth. Every slide must have:

- slide number and filename
- slide role in the narrative chain
- title
- main takeaway
- exact on-slide copy or copy plan
- layout type
- visual content
- generation prompt notes
- QA risks

Minimum deck structure:

1. Cover: topic, audience promise, date/context if useful
2. Agenda or orientation slide when the deck is longer than 8 slides
3. Body slides, each with one dominant idea
4. Synthesis or recommendation slide near the end
5. Closing slide with takeaway, call to action, or memorable final line

### Phase 4. Generate Slide Images

Create one prompt file per slide under `prompts/slide-XX.md`.

Each prompt must include:

- the shared design-system block
- the slide's role and takeaway
- exact 16:9 requirement
- composition and safe-area instructions
- exact on-slide text, kept short
- visual subject and mood
- negative prompt
- explicit instruction that the whole slide, including text and layout, must be AI-rendered in one complete image

Use available AI image generation for each slide. Generate each slide as a complete finished page, sequentially or in small batches, then save the selected AI output as:

```text
slides/slide-01-cover.png
slides/slide-02-agenda.png
slides/slide-03-...
```

For text-heavy slides:

1. Shorten on-slide text to the fewest necessary words.
2. Convert dense lists into visual hierarchy, labels, badges, or one-line callouts.
3. Split the slide if the model cannot render it legibly.
4. Regenerate the full slide page until the AI-rendered text is acceptable.

The final PDF must use the AI-generated full-slide images directly.

### Phase 5. QA and Regenerate

Before compiling the PDF, read `references/slide-quality-checklist.md`.

Create `qa/qa.md` with a table:

```text
Slide | Status | Issue | Fix | Final file
```

Check every slide for:

- 16:9 aspect ratio
- full-page AI-generated provenance
- readable and accurate text
- consistent style
- correct slide order
- one clear idea per slide
- no overlaps, clipped text, awkward artifacts, broken charts, or random symbols
- cover and closing quality

Regenerate any slide marked `fix` or `regenerate`. Use AI edit/regeneration only; do not locally repair the page. Do not continue to PDF until every slide is marked `pass`.

### Phase 6. Compile the PDF

Use the bundled script to combine final slide images:

```bash
python /path/to/codex-ppt/scripts/compile_slide_images_to_pdf.py \
  /path/to/deck-name/slides \
  /path/to/deck-name/final/deck.pdf \
  --strict \
  --report /path/to/deck-name/qa/compile-report.json
```

If slide images are not exact 16:9 yet, regenerate them as 16:9 AI images. Do not add padding, borders, cropping, or letterboxing as a substitute for correct generation.

After compiling, verify:

- PDF page count equals slide image count
- PDF page order matches storyboard
- pages are landscape 16:9
- no important content is cropped or padded unintentionally

## Bundled Resources

- `scripts/compile_slide_images_to_pdf.py`: compile ordered slide images into a 16:9 PDF and write a JSON preflight report.
- `references/slide-quality-checklist.md`: QA checklist and regeneration rules for slide images.
