---
name: codex-ppt
description: Create polished 16:9 presentation decks from a topic, outline, report, or rough notes in two modes: image mode with fully AI-rendered slide images, or editable PPTX mode that first generates approved slide images and then reconstructs each slide through per-slide subagents into editable PowerPoint text boxes and movable visual layers. Includes 10 curated aesthetic presets (Swiss Klein Blue, Monocle Magazine, Apple Keynote Bento, Kenya Hara Zen, Memphis Pop, Neo-Brutalist Zine, Dark Emerald Roadshow, Industrial Cobalt HUD, Clinical Ice Blue, Heritage Parchment Gold) and 12 layout archetypes. Use when the user asks to 自动做PPT, 做PPT, 生成PPT, 创赛PPT, 路演PPT, 指定PPT风格, make slides, create a slide deck, create a fully AI-generated image-based deck, or produce an editable PowerPoint deck.
---

# Codex PPT

Create a complete presentation as ordered 16:9 slide images, then either compile them into one PDF or use them as the approved visual target for an editable PPTX reconstruction pass. The skill is for deck-making where planning, visual consistency, full-page AI generation, quality review, and delivery format all matter.

## Output Modes

- `image` mode: generate approved slide images. This is the default unless the user asks for editable PowerPoint output; compile a PDF as the standard package unless the user only wants image files.
- `editable-pptx` mode: generate and QA the slide images first, then launch one per-slide reconstruction subagent for each approved image, merge the resulting visual layers and text layers, and build a final editable `.pptx`.

## Default Assumptions

- Output mode defaults to `image`.
- If the user asks for editable PPT, editable PowerPoint, selectable text, movable objects, or "图片转可编辑", use `editable-pptx`.
- In `image` mode, output is the ordered slide image set; compile a PDF unless the user asks to stop at images.
- In `editable-pptx` mode, output is a final editable `.pptx`; optionally also keep the image-mode PDF as a visual reference.
- Preserve the working files: brief, storyline, design system, storyboard, prompts, generated images, QA notes, and final deliverable.
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
8. In `image` mode: approved slide images, plus a final PDF unless the user asks for images only
9. In `editable-pptx` mode: per-slide reconstruction artifacts, merged visual/text layers, QA notes, and a final editable PPTX

## Hard Constraints

These constraints govern the approved slide images and the `image` deliverable. In `editable-pptx` mode, deterministic reconstruction is allowed only after the slide images are approved, and the derived PPTX artifacts must live separately under `editable/`.

- Do not generate slide images before the narrative chain, design system, and storyboard are written.
- Do not create final pages by generating a background and then adding text, shapes, charts, icons, screenshots, logos, arrows, or layout elements with HTML/CSS, canvas, Pillow, Keynote, PowerPoint, SVG, or any deterministic renderer.
- Do not use local composition to fix malformed text. Rewrite the prompt and regenerate the full slide page.
- Do not accept any final slide unless the whole visible page is the AI-generated output, apart from non-content-preserving file operations such as copying, format conversion, compression, or strict 16:9 verification.
- Do not treat "pretty images" as sufficient; each slide must have a job in the deck.
- Do not let each slide drift into a different style. Reuse the same visual system, margins, type hierarchy, and image language.
- In `image` mode, do not accept malformed AI-rendered text. In `editable-pptx` mode, rough or imperfect baked text is acceptable only if the reconstruction removes or avoids it and replaces it with correct native editable text before delivery.
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

If an `image` mode slide cannot pass because the AI model keeps rendering text poorly, reduce the text, make the slide more visual, split it into multiple slides, or ask the user to approve editable PPTX mode. Do not silently switch image-mode final slides to deterministic text composition.

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
├── editable/   # only for editable-pptx mode
└── final/
```

Write `brief.md` with:

- topic
- target audience
- objective
- desired slide count
- output mode: `image` or `editable-pptx`
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

- **Sales**: pain -> cost -> new way -> proof -> offer -> next step
- **Strategy**: current state -> pressure -> options -> decision logic -> roadmap -> ask
- **Education**: curiosity -> concept -> examples -> practice -> recap
- **Product**: user problem -> product idea -> workflow -> differentiators -> trust -> call to action
- **Report**: question -> method -> findings -> interpretation -> recommendation
- **Competition / Roadshow (创赛 / 路演)**: credible problem -> why now -> decisive insight -> one-sentence solution -> product workflow -> core tech innovation -> demo validation -> moat/comparison -> business/growth -> team & ask

### Phase 2. Select Aesthetic Preset & Lock the Visual System

Read `references/aesthetic-style-library.md` before writing `design-system.md`.

First, select the best aesthetic preset (or honor the user's explicit choice) from the **10 curated archetypes**:

- **Editorial & Minimalist**: `swiss-klein-editorial` (瑞士克莱因蓝网格), `monocle-ink-magazine` (独立杂志电子墨水), `apple-keynote-bento` (暗调旗舰 Bento 发布会), `kenya-hara-zen` (东方留白“空”之美学)
- **Bold Creative & Pitch**: `memphis-pop-playful` (暗盒孟菲斯高饱和贴纸), `neo-brutalist-zine` (新粗野主义创客海报)
- **Roadshow & Domain Evidence**: `dark-emerald-roadshow` (深翠流金 AI 科创路演), `industrial-cobalt-hud` (深海钴蓝工业智造), `clinical-ice-blue` (冰川澄蓝医疗/智慧教育), `heritage-parchment-gold` (宋锦宣纸非遗人文)

Then write `design-system.md` with:

- selected aesthetic preset ID, family, and rationale
- exact HEX color palette with functional roles (background, surface, border, primary ink, accent)
- typography direction and scale hierarchy
- recurring grid, margins, page chrome, and safe areas
- cover formula and body-slide layout rules
- chart/data and dominant proof-object treatment
- **Contamination Guard**: explicitly list forbidden cross-domain motifs (e.g. no crops outside agriculture, no robots outside manufacturing, no stethoscopes in education decks) and forbid unrelated template carryover words/logos
- pasteable Prompt DNA and negative prompt block

### Phase 3. Build the Storyboard

Read `references/page-template-grammar.md` and write `storyboard.md` as the source of truth. Every slide must have:

- slide number and filename
- slide role in the narrative chain
- **layout archetype ID** (chosen from the 12 archetypes in `references/page-template-grammar.md`, such as `hero-stage-cover`, `three-force-convergence`, `journey-pain-pins`, `before-after-split`, `central-product-hub`, `input-engine-output`, `three-tier-architecture`, `editorial-big-stat`, `demo-wall-metrics`, `moat-comparison-matrix`, `flywheel-milestone-finale`) — **never repeat the same layout archetype on two consecutive slides**
- section tag + **one-sentence claim headline** (state the conclusion, not just a topic noun)
- exact on-slide copy within the text budget (< 80–120 Chinese chars or < 50 English words)
- **dominant visual / proof object** (occupying 45%–60% of the canvas)
- generation prompt notes and QA risks

Minimum deck structure:

1. Cover (`hero-stage-cover`): topic, positioning sentence, dominant hero object, and metadata/proof badges
2. Agenda or orientation slide (`visual-route-agenda`) when the deck is longer than 8 slides
3. Body slides, each with one dominant idea, one claim band, one concrete proof object, and varied layout archetypes
4. Synthesis, validation, or moat comparison slide near the end
5. Closing slide (`flywheel-milestone-finale`) with takeaway, call to action, or memorable final line

### Phase 4. Generate Slide Images

Create one prompt file per slide under `prompts/slide-XX.md` following the **Standard Full-Page Prompt Spine** in `references/page-template-grammar.md`.

Each prompt must include:

- the selected aesthetic preset ID and shared design-system block (including exact HEX tokens and Prompt DNA)
- the slide's role, layout archetype, and one-sentence takeaway
- exact 16:9 (`1920x1080`) requirement and safe-area margins
- exact on-slide text (Section Tag, Headline Claim, and 3–6 short labels/badges)
- dominant visual/proof object (45%–60% area) and supporting callout structure
- Contamination Guard and negative prompt
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

The image-mode PDF and the approved visual reference for editable mode must use the AI-generated full-slide images directly.

### Phase 5. QA and Regenerate

Before compiling the PDF, read `references/slide-quality-checklist.md`.

Create `qa/qa.md` with a table:

```text
Slide | Status | Issue | Fix | Final file
```

Check every slide for:

- 16:9 aspect ratio
- full-page AI-generated provenance
- readable and accurate text in `image` mode; in `editable-pptx` mode, record any AI-rendered text problems that must be removed and replaced during reconstruction
- consistent style
- correct slide order
- one clear idea per slide
- no overlaps, clipped text, awkward artifacts, broken charts, or random symbols
- cover and closing quality

Regenerate any slide marked `fix` or `regenerate`. Use AI edit/regeneration only; do not locally repair the page. Do not continue to PDF until every slide is marked `pass`.

### Phase 6. Package Image Mode

Use the bundled script to combine final slide images, generate a visual QA contact sheet, and write a preflight report:

```bash
python /path/to/codex-ppt/scripts/compile_slide_images_to_pdf.py \
  /path/to/deck-name/slides \
  /path/to/deck-name/final/deck.pdf \
  --strict \
  --min-width 1280 \
  --contact-sheet /path/to/deck-name/qa/contact-sheet.jpg \
  --report /path/to/deck-name/qa/compile-report.json
```

If slide images are not exact 16:9 yet, regenerate them as 16:9 AI images. Do not add padding, borders, cropping, or letterboxing as a substitute for correct generation.

After compiling, verify:

- PDF page count equals slide image count
- PDF page order matches storyboard
- pages are landscape 16:9
- no important content is cropped or padded unintentionally

If the selected output mode is `image`, stop after this verification and deliver the images, optional PDF, and source artifacts.

### Phase 7. Build Editable PPTX Mode

Use this phase only when the selected output mode is `editable-pptx`. Read `references/editable-pptx-mode.md` before starting this phase, and use `references/editable-slide-subagent-prompt.md` as the per-slide subagent template.

Process:

1. Keep the approved slide images in `slides/` unchanged.
2. Create `editable/subagents/`.
3. Launch one subagent per approved slide when subagents are available. If subagents are unavailable, process the same per-slide contract sequentially.
4. Each slide worker must produce textless visual layers plus native editable text metadata (`canvas`, `background`, `route`, and `texts`), not a single baked screenshot with duplicated editable overlay text.
5. Merge the per-slide outputs:

```bash
python /path/to/codex-ppt/scripts/merge_editable_slide_outputs.py \
  /path/to/deck-name/editable/subagents \
  --out-layers-root /path/to/deck-name/editable/visual-layers \
  --out-text-json /path/to/deck-name/editable/text-layer.json \
  --canvas 1920x1080 \
  --force
```

6. Build the final editable PPTX:

```bash
node /path/to/codex-ppt/scripts/build_editable_ppt_from_layers.mjs \
  --backend auto \
  --layers-root /path/to/deck-name/editable/visual-layers \
  --text-json /path/to/deck-name/editable/text-layer.json \
  --out /path/to/deck-name/final/deck.editable.pptx \
  --workspace /path/to/deck-name/editable/workspace \
  --preview-dir /path/to/deck-name/editable/preview \
  --layout-dir /path/to/deck-name/editable/layout \
  --slide-size 960x540 \
  --fail-on-text-fill
```

7. Run automated QA verification on the slide images, merged layers, and final `.pptx`:

```bash
python /path/to/codex-ppt/scripts/verify_deck_outputs.py \
  --slides-dir /path/to/deck-name/slides \
  --layers-root /path/to/deck-name/editable/visual-layers \
  --text-json /path/to/deck-name/editable/text-layer.json \
  --disallow-text-fill \
  --pptx /path/to/deck-name/final/deck.editable.pptx \
  --require-editable-text \
  --report /path/to/deck-name/editable/qa/verify-report.json
```

Run `npm install` in the skill folder before using the fallback PPTX builder. Use `--fail-on-text-fill` during strict QA when text-layer data should be rejected if any text box still has fill or outline styling.

Before delivery, verify the PPTX opens, slide count matches, `ppt/slides/slide*.xml` contains editable semantic text, and no obvious duplicate baked/editable text remains.

## Bundled Resources

- `scripts/compile_slide_images_to_pdf.py`: compile ordered slide images into a 16:9 PDF, render a QA contact-sheet grid, and write a JSON preflight report.
- `scripts/merge_editable_slide_outputs.py`: validate and merge one reconstruction folder per slide into one visual-layers root and one deck-level `text-layer.json` while preserving per-slide `background`, `canvas`, and `route`.
- `scripts/build_editable_ppt_from_layers.mjs`: assemble textless visual layers and editable text objects into a PPTX with automatic coordinate scaling from source `canvas` to `--slide-size`.
- `scripts/verify_deck_outputs.py`: automated QA verifier for slide image dimensions/aspect ratios, editable layer bounds/overlaps, and `.pptx` XML semantic text runs.
- `references/aesthetic-style-library.md`: 10 curated aesthetic presets across 3 style families with routing matrix, HEX tokens, Prompt DNA, and Contamination Guard.
- `references/page-template-grammar.md`: 5-layer page depth formula, Claim Band rules, 12 non-repetitive page layout archetypes, Full-Page Prompt Spine, and body-slide upgrade snippets.
- `references/slide-quality-checklist.md`: QA checklist and regeneration rules for slide images.
- `references/editable-pptx-mode.md`: editable mode folder contract, subagent workflow, build commands, and QA gates.
- `references/editable-slide-subagent-prompt.md`: reusable prompt template for the per-slide reconstruction subagents.
