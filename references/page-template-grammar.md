# Page Template Grammar & Body-Slide Polish (页面版式语法与内页精修指南)

Use this reference when writing `storyboard.md` (**Phase 3**) and `prompts/slide-XX.md` (**Phase 4**), and when regenerating weak body pages during **Phase 5 (QA)**.

A common failure in AI-generated slide decks is **"Strong Cover, Weak Body"**: Slide 01 looks like a poster, while Slides 02–09 collapse into repetitive 3-card or 4-card bullet grids. To prevent layout fatigue, every slide must combine a distinct **Layout Archetype**, a **One-Sentence Claim Band**, and a **Dominant Visual/Proof Object**.

---

## 1. The 5-Layer Page Depth Formula

Every slide—especially body pages—should be composed across five deliberate depth layers:

```text
Layer 1: Background World      (paper grain, Swiss grid, obsidian stage, blueprint, or domain atmosphere)
Layer 2: Structural Chrome     (top running header, chapter tab, claim band, hairline rules, or HUD brackets)
Layer 3: Dominant Proof Object (occupies 45%–60% of the canvas: UI mockup, architecture stack, big chart, or 2.5D machine)
Layer 4: Supporting Callouts   (2–4 compact metric chips, step nodes, or comparison cards—never dense paragraphs)
Layer 5: High-Contrast Labels  (short, crisp titles, numbers, and badges inside safe margins)
```

---

## 2. The Claim Band Rule (标题即结论原则)

Never waste the main headline on a generic topic noun. Pair a small **Section Tag** with a punchy **Action Claim**:

- **Weak (Topic only)**: `项目背景` / `Product Architecture`
- **Strong (Section + Claim)**: `01 项目背景 · 碎片化工具链正在吞噬研发团队 40% 的交付时间`
- **Weak (Topic only)**: `核心功能` / `AI Features`
- **Strong (Section + Claim)**: `04 核心闭环 · 三步将非结构化会议录音转化为可执行工单`

---

## 3. Twelve Page Layout Archetypes (12 种核心页面版式)

Assign a specific archetype to each slide in `storyboard.md`. **Never use the same layout archetype on two consecutive slides.**

| # | Archetype ID | Best Slide Role | Visual Structure |
| :--- | :--- | :--- | :--- |
| 1 | `hero-stage-cover` | Cover / Opening | Huge display title + 1 positioning sentence + 1 dominant hero object (50% area) + 3 metadata/proof badges |
| 2 | `visual-route-agenda` | Agenda / Roadmap | 4–6 numbered route nodes along a path or 2-column magazine index with a miniature echo of the cover hero |
| 3 | `three-force-convergence` | Why Now / Context | Policy, market demand, and tech shift converging into one central opportunity window + trend chart |
| 4 | `journey-pain-pins` | Problem / User Pain | Left-to-right user journey or central persona with 3–5 high-contrast pain pins/warning stickers attached |
| 5 | `before-after-split` | Tension / Insight | High-contrast asymmetric split: chaotic legacy state (left, 40%) vs. structured new paradigm (right, 60%) |
| 6 | `central-product-hub` | Solution / Product | Large central product UI / 2.5D machine hub surrounded by 4 luminous or hairline value callouts |
| 7 | `input-engine-output` | Core Workflow | 3-stage horizontal conveyor: Concrete Input Artifact (left) -> Processing Core (center) -> Final Deliverable Card (right) |
| 8 | `three-tier-architecture` | Technology / System | Stacked 3-layer architecture board (Interaction Layer / Intelligence Engine / Data & Infra Base) with highlighted core module |
| 9 | `editorial-big-stat` | Evidence / Market | One massive headline number (e.g. `3.8×` or `94.2%`) occupying 40% of the canvas + 1 clean supporting chart + 3 takeaway chips |
| 10 | `demo-wall-metrics` | Validation / Case | Large realistic product result view or case board (left/center) + 3 vertical KPI metric badges (right) |
| 11 | `moat-comparison-matrix` | Differentiation | Clean comparison matrix or 4-axis radar where our column/zone is visually elevated in the deck's accent color |
| 12 | `flywheel-milestone-finale` | Business / Closing | Growth flywheel or 3-stage milestone rail leading into a confident closing slogan and call-to-action badges |

---

## 4. Standard Full-Page Prompt Spine

Use this structure for every `prompts/slide-XX.md` file:

```markdown
Create one complete 16:9 presentation slide image (1920x1080).

[Aesthetic System]
- Preset: {STYLE_ID} ({STYLE_NAME})
- Shared Design Tokens: {PASTE_CONCISE_DESIGN_SYSTEM_BLOCK}
- Layout Archetype: {ARCHETYPE_ID}

[Narrative Job]
- Slide Role: {SLIDE_ROLE}
- Core Takeaway: {ONE_SENTENCE_TAKEAWAY}

[Exact On-Slide Text — Render Clearly & Accurately]
- Section Tag: "{SECTION_TAG}"
- Headline Claim: "{HEADLINE_CLAIM}"
- Key Labels / Badges:
  1. "{LABEL_1}"
  2. "{LABEL_2}"
  3. "{LABEL_3}"

[Visual Composition & Dominant Object]
- Safe Area: Keep all text at least 96px from left/right edges and 80px from top/bottom edges.
- Dominant Focal Object (45%–60% of canvas): {CONCRETE_VISUAL_OR_PROOF_OBJECT}
- Supporting Elements: {SUPPORTING_PANELS_OR_DIAGRAM_STRUCTURE}
- Depth & Lighting: {BACKGROUND_TEXTURE_AND_LIGHTING_NOTES}

[Hard Constraints & Negative Prompt]
- Render the entire slide—background, grid, visual objects, diagrams, and typography—as one unified poster-grade image.
- Only render the exact listed text; do not invent extra paragraphs, fake watermarks, or gibberish microcopy.
- Negative prompt: generic corporate template, repetitive 4-card bullet grid, malformed or overlapping characters, tiny unreadable labels, cropped titles, unrelated domain motifs ({FORBIDDEN_MOTIFS}).
```

---

## 5. On-Slide Text Budget (字数预算铁律)

Because image generation models degrade rapidly when forced to render dense paragraphs, enforce this strict per-slide text budget:

- **1 Section Tag** (2–6 words / 4–8 Chinese chars)
- **1 Headline Claim** (under 12 words / 18 Chinese chars)
- **3–6 Short Labels, Chips, or Callouts** (2–8 words / 4–12 Chinese chars each)
- **Total visible text per slide**: keep under **80–120 Chinese characters** (or **50 English words**).
- If the source material is text-heavy, **distill prose into large numbers, short badges, directional arrows, or split one dense slide into two focused slides**.

---

## 6. Body-Page Upgrade Snippets (内页返工强化指令)

When a generated body slide looks flat, empty, or disconnected from the cover style during Phase 5 QA, append one of these upgrade blocks before regenerating:

- **For Editorial / Swiss / Magazine styles (`swiss-klein-editorial`, `monocle-ink-magazine`, `kenya-hara-zen`)**:
  ```text
  Upgrade layout authority: enforce visible grid architecture, stronger typographic scale contrast (huge display numerals paired with crisp 3-word labels), exposed hairline dividers, and intentional negative space. Remove generic floating cards.
  ```
- **For Keynote / Creative Pitch styles (`apple-keynote-bento`, `memphis-pop-playful`, `neo-brutalist-zine`)**:
  ```text
  Upgrade visual impact: enlarge the central hero object to 55% of the canvas, tighten card geometry (Bento specular borders or thick brutalist/Memphis outlines), and replace multi-line text with bold graphic badges.
  ```
- **For Roadshow / Domain styles (`dark-emerald-roadshow`, `industrial-cobalt-hud`, `clinical-ice-blue`, `heritage-parchment-gold`)**:
  ```text
  Upgrade roadshow evidence density: use a clear top chapter tab, a highlighted one-sentence claim band, one dominant domain proof object in the center, and 3 structured evidence callouts with style-authentic chrome.
  ```
