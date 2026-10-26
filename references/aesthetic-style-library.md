# Aesthetic Style Library (审美风格预设库)

Use this reference during **Phase 2 (Select Style & Lock Design System)** before writing `design-system.md` or any slide prompt.

When an AI agent invents a slide palette from scratch without a strong art-direction archetype, it easily drifts into generic dark-blue gradients, muddy colors, or lifeless corporate card grids. This library provides **10 battle-tested aesthetic presets** across **3 style families**, with exact HEX color tokens, typography rules, recurring page chrome, hero-object grammar, and copy-paste prompt DNA.

---

## 1. Style Selection & Routing Matrix

1. **Honor explicit user preference first**: If the user names a style (e.g., "瑞士网格风", "孟菲斯", "Apple 发布会风", "Monocle 杂志风", "创赛深绿/工业蓝"), select that preset.
2. **Auto-route by deck purpose and domain** when the user does not specify a style:

| Style ID | Family | Aesthetic Name | Best For (适用场景) | Avoid When (不适用场景) |
| :--- | :--- | :--- | :--- | :--- |
| `swiss-klein-editorial` | Editorial & Minimalist | **瑞士国际主义 · 克莱因蓝网格** | AI/Tech launches, strategy decks, design shares, data-heavy reports | Warm cultural heritage, playful kids/gaming topics |
| `monocle-ink-magazine` | Editorial & Minimalist | **独立杂志 · 电子墨水人文风** | Industry insights, research narratives, book/cultural reviews, founder essays | Heavy industrial hardware, neon gaming |
| `apple-keynote-bento` | Editorial & Minimalist | **暗调旗舰 · Bento 发布会风** | Flagship product launches, SaaS releases, developer tools, hardware keynotes | Traditional government/medical compliance reports |
| `kenya-hara-zen` | Editorial & Minimalist | **东方留白 · 原研哉“空”之美学** | Architecture, lifestyle brands, speculative design, philosophy, luxury aesthetics | High-density competition evidence boards |
| `memphis-pop-playful` | Bold Creative & Pitch | **暗盒孟菲斯 · 高饱和波普贴纸** | Consumer apps, Gen-Z products, creative pitches, gamified experiences | Serious clinical medical or financial audit reports |
| `neo-brutalist-zine` | Bold Creative & Pitch | **新粗野主义 · 创客先锋海报** | Indie hackers, Web3/AI agents, design tools, hackathon demos, bold marketing | Conservative enterprise or traditional heritage |
| `dark-emerald-roadshow` | Roadshow & Domain | **深翠流金 · AI 与科创路演** | Innovation competitions (创赛), AI platforms, data intelligence, SaaS roadshows | Pure cultural heritage or clinical nursing |
| `industrial-cobalt-hud` | Roadshow & Domain | **深海钴蓝 · 工业智造与机器人** | Robotics, smart manufacturing, autonomous hardware, IoT sensors, auto tech | Soft lifestyle, humanities, rural ecology |
| `clinical-ice-blue` | Roadshow & Domain | **冰川澄蓝 · 医疗健康与智慧教育** | MedTech, wearables, healthcare, smart education, campus platforms, EdTech | Dark cyberpunk or playful party apps |
| `heritage-parchment-gold` | Roadshow & Domain | **宋锦宣纸 · 非遗文旅与东方人文** | Intangible cultural heritage (非遗), museums, cultural tourism, crafts, history | Pure cloud SaaS or semiconductor hardware |

> **Rule of Thumb**: Never mix color tokens across two presets in the same deck. One deck = one unified aesthetic world from cover to closing page.

---

## 2. Family A: Editorial & Minimalist Design (杂志级排版与极简设计派)

### 2.1 `swiss-klein-editorial` — 瑞士国际主义 · 克莱因蓝网格

Inspired by Josef Müller-Brockmann, Massimo Vignelli, and Pentagram editorial systems. Built on mathematical grids, stark black-and-white contrast, and **one single high-saturation anchor color**.

- **Color Tokens**:
  - Paper Background: `#FAFAF8` (Warm Off-White)
  - Structural Block Grey: `#F0F0EE`
  - Hairline Divider Grey: `#D4D4D2`
  - Muted Meta Grey: `#737373`
  - Primary Ink: `#0A0A0A` (Near Black)
  - Single Accent Anchor (pick ONE per deck):
    - **IKB Klein Blue (Default)**: `#002FA7` (text on accent: `#FFFFFF`)
    - **Cadmium Lemon**: `#FFD500` (text on accent: `#0A0A0A`)
    - **Highlighter Green**: `#C5E803` (text on accent: `#0A0A0A`)
    - **Safety Orange**: `#FF6B35` (text on accent: `#FFFFFF`)
- **Typography & Grid**:
  - Grotesque sans-serif (Helvetica / Inter / HarmonyOS Sans SC Black).
  - Strict 8pt mathematical grid, visible 1px hairline cell borders (`#D4D4D2`), sharp 90° corners (no rounded cards, no drop shadows, no gradients).
  - Oversized KPI numerals (`120pt+` visual scale) acting as architectural anchors.
  - 55%+ strategic whitespace.
- **Prompt DNA**:
  ```text
  Josef Müller-Brockmann and Pentagram Swiss International Style 16:9 editorial slide. Warm off-white paper background (#FAFAF8), exposed 1px mathematical grid lines (#D4D4D2), sharp 90-degree rectangular color blocks, stark near-black grotesque typography (#0A0A0A), and a single International Klein Blue (#002FA7) accent block. Zero gradients, zero drop shadows, zero rounded corners, 60% whitespace, architectural data visualization.
  ```

---

### 2.2 `monocle-ink-magazine` — 独立杂志 · 电子墨水人文风

Inspired by *Monocle*, *Bloomberg Businessweek*, and *A Book Apart*. Combines tactile print warmth with razor-sharp editorial hierarchy.

- **Color Tokens** (Default Ink Classic; sub-themes allowed):
  - Paper Background: `#F1EFEA` (Warm Newsprint Ivory)
  - Secondary Panel Tint: `#E8E5DE`
  - Primary Ink: `#0A0A0B` (Deep Press Black)
  - Secondary Ink: `#3A3A3C`
  - Editorial Accent: `#C84B31` (Terracotta Vermilion) or `#0A1F3D` (Indigo Porcelain)
- **Typography & Grid**:
  - High-contrast editorial serif or Songti/Mincho display headlines paired with crisp sans-serif body labels and monospace issue tags (`Vol. 01 · Insight`).
  - Top newspaper running header with thin double rules (`2px` + `1px`).
  - Warm cartographic charts, fine-line editorial illustrations, and pull-quote callout blocks.
- **Prompt DNA**:
  ```text
  Monocle and Bloomberg Businessweek print magazine spread aesthetic, 16:9 presentation slide. Warm e-ink ivory paper texture (#F1EFEA), deep printing-press black ink (#0A0A0B), subtle terracotta red accent (#C84B31). Top editorial running header with fine horizontal rules, high-contrast serif/sans-serif Chinese typography, refined infographic chart, tactile print warmth, no glowing neon or 3D plastic.
  ```

---

### 2.3 `apple-keynote-bento` — 暗调旗舰 · Bento 发布会风

Inspired by Apple Special Event keynotes and Linear dark-mode craftsmanship. Dramatic lighting, modular Bento grids, and hardware/UI precision.

- **Color Tokens**:
  - Stage Background: `#090A0F` (Obsidian Pitch)
  - Bento Card Surface: `#141720` to `#1C202E` (Subtle top-lit metallic surface)
  - Card Hairline Border: `#2A2F42` (1px specular edge)
  - Primary Text: `#F5F7FA` (Crisp White)
  - Muted Label Text: `#8E96AA`
  - Spotlight Accent: `#5E6AD2` (Indigo Glow) + `#F5A623` (Warm Titanium Gold for key metrics)
- **Typography & Grid**:
  - Heavy geometric sans-serif headlines (`SF Pro Display` / `PingFang SC Semibold`), tight tracking, centered or modular Bento alignment.
  - Asymmetric Bento Grid (1 hero 2x2 cell + 3–4 compact metric/diagram cells).
  - Studio rim lighting on central product mockups or 3D glass/metal objects.
- **Prompt DNA**:
  ```text
  Apple Keynote flagship launch slide with dark Bento grid architecture, 16:9. Obsidian dark stage (#090A0F), matte titanium dark-grey rounded Bento cards (#161822) with 1px subtle specular rim borders (#2A2F42), studio rim lighting, crisp white typography, one dominant 3D product/UI hero cell and three high-impact metric cells. Sleek, minimal, cinematic product launch quality.
  ```

---

### 2.4 `kenya-hara-zen` — 东方留白 · 原研哉“空”之美学

Inspired by Kenya Hara (*Designing Design* / MUJI), Takram speculative diagrams, and Neo Shen digital ink wash. Design by subtraction.

- **Color Tokens**:
  - Primary Canvas: `#F7F5F0` (Tactile Washi / Xuan Paper White)
  - Secondary Layer White: `#ECE9E1`
  - Charcoal Ink: `#1C1B19`
  - Stone Grey: `#7A766E`
  - Seal Vermilion Accent (used on < 3% of canvas): `#B83B2B`
- **Typography & Grid**:
  - Refined Songti / Mincho or light-to-medium sans-serif with generous line height and letter spacing.
  - 70%+ open breathing space; ultra-thin `0.5pt` diagram connectors and subtle ink-wash tonal gradients.
  - One contemplative physical or conceptual object per slide with soft natural daylight shadow.
- **Prompt DNA**:
  ```text
  Kenya Hara MUJI and Takram Japanese minimalist presentation slide, 16:9. Tactile warm washi paper background (#F7F5F0), 75% intentional empty space, charcoal black typography (#1C1B19), ultra-fine hairlines, one tiny vermilion seal accent (#B83B2B), soft natural shadow, serene museum-catalogue precision, zero visual clutter.
  ```

---

## 3. Family B: Bold Creative & Product Pitch (先锋创意与高能量提案派)

### 3.1 `memphis-pop-playful` — 暗盒孟菲斯 · 高饱和波普贴纸

Inspired by Ettore Sottsass's Memphis Group and playful consumer-app storytelling (featured in the bundled `examples/shit-app-memphis-pitch` deck).

- **Color Tokens**:
  - Stage Background: `#000000` (Pure Black Stage)
  - Primary Text & Header: `#FFFFFF`
  - Electric Yellow: `#FFE600` (Primary CTA / Key Highlight)
  - Hot Pink: `#FF006E` (Tension / Alert / Emotion Tag)
  - Cyan Pool: `#00CFFF` (Flow / Resolution)
  - Mint Green: `#00FFB2` (Success / Playbook)
  - Tangelo Orange: `#FF6B35` (Energy / Action)
- **Typography & Grid**:
  - Restrained white brand header bar at the top (`110px` safe zone) contrasting with an explosive central stage.
  - Extra-bold poster display titles + tilted die-cut sticker labels (2–5 words max).
  - Polka dots, zig-zag lightning bolts, bold black outlines, and 2.5D toy-like interactive machines or characters.
- **Prompt DNA**:
  ```text
  Black-stage Memphis Pop product pitch slide, 16:9. Pure black background (#000000) with clean white top header bar, explosive high-saturation Memphis geometry in electric yellow (#FFE600), hot pink (#FF006E), cyan (#00CFFF), and mint (#00FFB2). 2.5D toy-like central product machine, bold die-cut sticker badges with thick black outlines, halftone polka dots, playful poster typography.
  ```

---

### 3.2 `neo-brutalist-zine` — 新粗野主义 · 创客先锋海报

Inspired by Gumroad, Figma Config, and indie maker zines. Honest borders, hard offset shadows, and punchy editorial energy.

- **Color Tokens**:
  - Canvas Background: `#FFFDF5` (Warm Cream)
  - Structural Stroke & Shadow: `#000000` (Solid 3px border + 6px 45° hard offset shadow)
  - Card Fills: `#FFFFFF`, `#FEF08A` (Post-it Yellow), `#E9D5FF` (Soft Violet), `#BBF7D0` (Mint)
  - Primary Accent: `#7C3AED` (Vivid Violet) or `#FF5722` (Brutalist Orange)
- **Typography & Grid**:
  - Heavy grotesque display headlines paired with monospace pill badges (`[STEP 01]`, `v2.0`).
  - Exposed window-chrome frames (title bar with three dots) around product UI mockups and diagrams.
- **Prompt DNA**:
  ```text
  Neo-Brutalist indie maker pitch slide, 16:9. Warm cream background (#FFFDF5), crisp white and pastel yellow/violet cards with solid 3px black borders (#000000) and hard 45-degree black offset drop shadows (no blur). Bold grotesque Chinese display title, monospace pill tags, browser-window framed UI mockup, energetic Figma Config aesthetic.
  ```

---

## 4. Family C: High-Stakes Roadshow & Domain Evidence (高规格路演与行业创赛派)

### 4.1 `dark-emerald-roadshow` — 深翠流金 · AI 与科创路演

Built for high-stakes innovation competitions (挑战杯 / 国创赛 / 科技路演), AI platforms, and data intelligence products.

- **Color Tokens**:
  - Deep Stage: `#061A17` to `#0B2924` (Deep Emerald Teal)
  - Panel Surface: Translucent emerald glass `#0F3830` with cyan border `#00F0FF`
  - Primary Text: `#F4FBF9`
  - Claim & Award Gold: `#F3C663` (Warm Gold)
  - Tech Cyan Accent: `#00F0FF`
- **Typography & Grid**:
  - Top chapter navigation strip + gold-highlighted one-sentence Claim Band (`核心结论带`).
  - One dominant proof object (product dashboard, architecture stack, or benchmark board) occupying 45%–60% of the slide, flanked by 2–4 evidence cards and proof badges.
- **Prompt DNA**:
  ```text
  High-stakes Chinese AI innovation roadshow slide, 16:9. Deep emerald-teal stage (#061A17), translucent emerald glass evidence panels with fine cyan HUD brackets (#00F0FF) and warm gold claim band (#F3C663). Top navigation strip, one dominant product dashboard / architecture proof object occupying half the canvas, crisp high-contrast Chinese labels.
  ```

---

### 4.2 `industrial-cobalt-hud` — 深海钴蓝 · 工业智造与机器人

Built for robotics, smart manufacturing, industrial AI inspection, autonomous hardware, and engineering systems.

- **Color Tokens**:
  - Deep Navy Base: `#071326`
  - Cobalt Panel: `#102A52`
  - Steel Silver: `#C8D4E3`
  - Cyan HUD Line: `#00D4FF`
  - Amber Warning / Highlight: `#FFB800`
- **Typography & Grid**:
  - Brushed-metal chapter tabs, technical blueprint grid in the background, concrete industrial hero objects (robotic arm, vision camera, sensor module, digital-twin production line), and structured engineering evidence boards.
- **Prompt DNA**:
  ```text
  Industrial AI and smart manufacturing roadshow slide, 16:9. Deep navy and cobalt blue engineering stage (#071326), metallic HUD panel frames, cyan technical telemetry lines (#00D4FF), amber gold highlights (#FFB800), concrete industrial robot/sensor hero object, digital-twin factory evidence board, crisp white Chinese technical labels.
  ```

---

### 4.3 `clinical-ice-blue` — 冰川澄蓝 · 医疗健康与智慧教育

Built for MedTech, smart wearables, clinical diagnostics, smart education platforms, and campus knowledge graphs. Airy, trustworthy, and highly legible.

- **Color Tokens**:
  - Airy Background: `#F6FAFD` (Ice White-Blue)
  - Floating Panel: `#FFFFFF` with soft sky border `#DCEBFA`
  - Primary Title Blue: `#0F52BA` (Academic / Medical Sapphire)
  - Cyan Data Line: `#00A8E8`
  - Key Emphasis Accent: `#FF7A00` (Warm Orange for key metrics/callouts)
- **Typography & Grid**:
  - Bright, high-key lighting with soft elevation shadows; rounded white-blue evidence panels; clean curves, wearable sensor / digital textbook / knowledge-graph hero objects.
- **Prompt DNA**:
  ```text
  Clean ice-blue technology presentation slide for healthcare or smart education, 16:9. Bright airy white-blue background (#F6FAFD), floating white rounded panels with thin sapphire borders (#0F52BA) and orange emphasis tags (#FF7A00), precise data charts and concrete device/dashboard hero object, clinical clarity and high legibility.
  ```

---

### 4.4 `heritage-parchment-gold` — 宋锦宣纸 · 非遗文旅与东方人文

Built for intangible cultural heritage (非遗), museums, cultural tourism, traditional crafts, and digital humanities.

- **Color Tokens**:
  - Parchment Base: `#F3EAD8` (Aged Xuan / Silk Parchment)
  - Deep Walnut Panel: `#2C1D14`
  - Bronze Gold: `#C59B5F`
  - Ink Black: `#1A1615`
  - Cinnabar Red Stamp: `#9E2A2B`
- **Typography & Grid**:
  - Calligraphic brush display titles paired with Songti/serif labels, carved scroll-inspired panel frames, authentic craft/artifact photography or illustration (embroidery, ceramics, woodwork, ancient architecture), warm editorial lighting.
- **Prompt DNA**:
  ```text
  Warm Chinese cultural heritage and museum editorial presentation slide, 16:9. Aged silk parchment texture (#F3EAD8) with deep walnut brown (#2C1D14) and bronze gold (#C59B5F) frames, cinnabar red seal accent (#9E2A2B), brush calligraphy title, authentic traditional craft/artifact hero imagery, refined cultural infographic layout.
  ```

---

## 5. Contamination Guard (防串味与防幻觉护栏)

When locking `design-system.md`, always include an explicit **Contamination Guard** section and paste it into every slide's negative prompt:

1. **No Cross-Domain Motifs**:
   - Do not render crops/leaves/farmland unless the topic is agriculture/ecology.
   - Do not render factory robotic arms unless the topic is manufacturing/robotics.
   - Do not render stethoscopes/doctors/medical crosses unless the topic is healthcare (especially when using `clinical-ice-blue` for an education project!).
   - Do not render generic glowing AI brain spheres when a concrete product UI, hardware device, or data chart can serve as the focal object.
2. **No Unrelated Template Carryover**:
   - Never carry over project names, institution logos, fake award titles, or domain terms from reference templates or unrelated examples (e.g., do not leak `SHIT APP`, `AttraX`, or unrelated competition titles into a new user's deck).
3. **Style Consistency Beyond Slide 1**:
   - The chosen preset's background texture, border geometry, color tokens, and typography hierarchy must remain unmistakably visible on **every body slide (Slides 2 to N-1)**, not only on the cover page.
