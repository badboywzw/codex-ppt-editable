<p align="center">
  <img src="./assets/codex-ppt-hero.png" alt="Codex PPT hero: AI-rendered slide decks, from brief to PDF and editable PPTX" width="100%">
</p>

<p align="center">
  <a href="https://github.com/qybaihe/codex-ppt/actions/workflows/tests.yml"><img src="https://github.com/qybaihe/codex-ppt/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/qybaihe/codex-ppt/releases"><img src="https://img.shields.io/github/v/release/qybaihe/codex-ppt?include_prereleases&label=version" alt="Release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-3776AB.svg" alt="Python >=3.10">
  <img src="https://img.shields.io/badge/node-%3E%3D18-339933.svg" alt="Node >=18">
</p>

<p align="center">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

# Codex PPT

**Codex PPT** is a producer-style AI agent skill for creating polished **16:9 presentation decks** in two complementary modes:

1. **`image` mode (default)** — Generates each slide as a cohesive, full-page AI poster image and compiles approved pages into a strict 16:9 PDF (plus a visual QA contact sheet).
2. **`editable-pptx` mode** — Uses the QA-approved slide images as the visual ground truth, dispatches per-slide reconstruction subagents to separate textless visual layers from semantic text boxes, and compiles a native editable `.pptx`.

Instead of stitching together generic templates or locally patching broken text, **Codex PPT** makes your agent act like a deck producer: write the brief, lock the narrative chain and design system, storyboard every page, enforce strict QA regeneration loops, and verify the final deliverables automatically.

---

## What's New in v0.3.0

- **Automatic 3-Level Canvas Coordinate Scaling**: `build_editable_ppt_from_layers.mjs` now normalizes both visual layer assets and native text boxes from source image coordinates (e.g. `1920x1080` at deck, slide, or item level) to `--slide-size` (`960x540`), supporting both array `[x, y, w, h]` and object `{x, y, w, h}` geometries.
- **Per-Slide Metadata & Layer Z-Order**: `merge_editable_slide_outputs.py` and the PPTX builder now preserve per-slide `background`, `canvas`, `route`, `zIndex` stacking order, and rich typography (`italic`, `underline`, `charSpacing`, `lineSpacingMultiple`, `opacity`/`transparency`, `rotation`).
- **Automated Visual Contact Sheet (`--contact-sheet`)**: `compile_slide_images_to_pdf.py` can render a captioned multi-column grid of all slides (`qa/contact-sheet.jpg`) to inspect deck-wide style consistency at a glance.
- **Automated Deliverable Verifier (`verify_deck_outputs.py`)**: New CLI tool that validates slide aspect ratios/resolutions, checks editable text-layer bounds and high-IoU overlaps, blocks path traversal in layer manifests, and inspects `.pptx` XML (`ppt/slides/slide*.xml`) to confirm semantic `<a:t>` text runs exist on every slide.
- **Full Test Suite & CI**: Added `pytest` and `node:test` suites with GitHub Actions CI.

---

## Output Modes Comparison

| Dimension | `image` Mode (Default) | `editable-pptx` Mode |
| :--- | :--- | :--- |
| **Best For** | Pitch decks, concept decks, visual reports, mood-driven storytelling | Decks requiring downstream copy edits, layout tweaks, or team handoff |
| **Visual Fidelity** | 100% poster-grade AI composition (typography + graphics unified) | High visual fidelity via textless PNG layers + native PowerPoint text |
| **QA Rule** | Reject & regenerate full slide prompt on text/layout defects | Approve visual target first, then replace baked text with native text boxes |
| **Deliverables** | `slides/*.png`, `qa/contact-sheet.jpg`, `final/deck.pdf` | All `image` artifacts + `editable/visual-layers/`, `text-layer.json`, `final/deck.editable.pptx` |

---

## Workflow

<p align="center">
  <img src="./assets/codex-ppt-workflow.png" alt="Codex PPT workflow diagram" width="100%">
</p>

The core principle is simple: **in image mode, if a slide fails QA, rewrite the prompt and regenerate the whole slide—never locally patch text or layout.** Editable mode starts only after the slide images pass QA and stores derived reconstruction artifacts cleanly under `editable/`.

### How the Skill Thinks (7 Phases)

1. **Brief (`brief.md`)**: Define audience, objective, slide count, output mode, tone, and constraints.
2. **Storyline (`storyline.md`)**: Establish the narrative arc (`Hook -> Context -> Tension -> Insight -> Solution -> Evidence -> Action`) before designing visuals.
3. **Design System (`design-system.md`)**: Lock color palette, typography hierarchy, safe margins, layout variants, and negative prompts.
4. **Storyboard (`storyboard.md`)**: Specify every slide's role, title, takeaway, exact on-slide copy, visual subject, and QA risks.
5. **Generation (`prompts/` & `slides/`)**: Write one self-contained prompt per slide and generate 16:9 full-page images.
6. **QA Loop (`qa/qa.md` & `contact-sheet.jpg`)**: Reject malformed copy, style drift, or cropped edges; regenerate until every slide passes.
7. **Export & Verification (`final/`)**: Compile the strict 16:9 PDF, or run per-slide subagent layer reconstruction, merge, build `.pptx`, and verify with `verify_deck_outputs.py`.

---

## Installation & Usage

### 1. Install the Skill

Clone into your agent's skills directory (supports **Codex**, **Claude Code**, **Antigravity**, etc.):

```bash
# For OpenAI Codex
git clone https://github.com/qybaihe/codex-ppt.git ~/.codex/skills/codex-ppt

# Or for Claude Code / Antigravity
git clone https://github.com/qybaihe/codex-ppt.git ~/.gemini/antigravity/skills/codex-ppt
```

Install script dependencies:

```bash
pip install -r ~/.codex/skills/codex-ppt/requirements.txt
npm install --prefix ~/.codex/skills/codex-ppt
```

### 2. Trigger the Skill

**Image / PDF Deck (Default):**

```text
Use $codex-ppt to make a 10-page product pitch deck about my app idea.
```

**Editable PowerPoint Deck (`editable-pptx`):**

```text
Use $codex-ppt to make an editable PPTX deck about my app idea with selectable text and movable layers.
```

---

## CLI Scripts Reference

### 1. Compile Slide Images to PDF & Contact Sheet

```bash
python scripts/compile_slide_images_to_pdf.py \
  /path/to/deck/slides \
  /path/to/deck/final/deck.pdf \
  --strict \
  --min-width 1280 \
  --contact-sheet /path/to/deck/qa/contact-sheet.jpg \
  --report /path/to/deck/qa/compile-report.json
```

### 2. Merge Per-Slide Editable Reconstructions

```bash
python scripts/merge_editable_slide_outputs.py \
  /path/to/deck/editable/subagents \
  --out-layers-root /path/to/deck/editable/visual-layers \
  --out-text-json /path/to/deck/editable/text-layer.json \
  --canvas 1920x1080 \
  --force
```

### 3. Build Editable PPTX from Visual & Text Layers

```bash
node scripts/build_editable_ppt_from_layers.mjs \
  --backend auto \
  --layers-root /path/to/deck/editable/visual-layers \
  --text-json /path/to/deck/editable/text-layer.json \
  --out /path/to/deck/final/deck.editable.pptx \
  --slide-size 960x540 \
  --fail-on-text-fill
```

### 4. Verify Deck Deliverables (Slides, Layers, and PPTX XML)

```bash
python scripts/verify_deck_outputs.py \
  --slides-dir /path/to/deck/slides \
  --layers-root /path/to/deck/editable/visual-layers \
  --text-json /path/to/deck/editable/text-layer.json \
  --disallow-text-fill \
  --pptx /path/to/deck/final/deck.editable.pptx \
  --require-editable-text \
  --report /path/to/deck/editable/qa/verify-report.json
```

---

## Example Output

The repository includes a complete 10-slide generated deck (**SHIT APP Memphis Pitch**):

- [Final PDF](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pdf)
- [Final PPTX](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pptx)
- [Planning Source (`brief`, `storyline`, `design-system`, `storyboard`, `qa`)](./examples/shit-app-memphis-pitch/source/)

### Selected Pages

![SHIT APP cover](./examples/shit-app-memphis-pitch/slides/slide-01-cover.png)

![Product idea slide](./examples/shit-app-memphis-pitch/slides/slide-03-product-idea.png)

![Core flow slide](./examples/shit-app-memphis-pitch/slides/slide-05-core-flow.png)

![AI playbook slide](./examples/shit-app-memphis-pitch/slides/slide-07-ai-playbook.png)

![Roadmap closing slide](./examples/shit-app-memphis-pitch/slides/slide-10-roadmap-closing.png)

---

## Repository Structure

```text
.
├── SKILL.md                                    # Core skill workflow & hard constraints
├── agents/openai.yaml                          # Codex skill metadata
├── references/
│   ├── slide-quality-checklist.md              # Image QA & regeneration rules
│   ├── editable-pptx-mode.md                   # Editable PPTX pipeline & QA gates
│   └── editable-slide-subagent-prompt.md       # Per-slide reconstruction subagent template
├── scripts/
│   ├── compile_slide_images_to_pdf.py          # 16:9 PDF compiler + QA contact sheet
│   ├── merge_editable_slide_outputs.py         # Per-slide layer & metadata merger
│   ├── build_editable_ppt_from_layers.mjs      # Dual-backend editable PPTX builder
│   ├── verify_deck_outputs.py                  # Automated QA verifier for slides/layers/PPTX
│   ├── slide_utils.py                          # Shared Python utilities & path validation
│   └── lib/json_io.mjs                         # Shared Node JSON I/O utilities
├── tests/                                      # Pytest & Node test suites
├── assets/                                     # Hero & workflow diagrams
└── examples/shit-app-memphis-pitch/            # Full 10-page example deck
```

## Development & Testing

```bash
pip install -r requirements-dev.txt
npm install
npm run test:all
```

## License

[MIT](./LICENSE)
