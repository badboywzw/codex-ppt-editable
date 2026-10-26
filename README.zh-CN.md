<p align="center">
  <img src="./assets/codex-ppt-hero.png" alt="Codex PPT 头图：AI-rendered slide decks, from brief to PDF and editable PPTX" width="100%">
</p>

<p align="center">
  <a href="https://github.com/qybaihe/codex-ppt/actions/workflows/tests.yml"><img src="https://github.com/qybaihe/codex-ppt/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/qybaihe/codex-ppt/releases"><img src="https://img.shields.io/github/v/release/qybaihe/codex-ppt?include_prereleases&label=version" alt="Release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-3776AB.svg" alt="Python >=3.10">
  <img src="https://img.shields.io/badge/node-%3E%3D18-339933.svg" alt="Node >=18">
</p>

<p align="center">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

# Codex PPT

**Codex PPT** 是一个制片人级（Producer-style）的 AI 演示文稿生成 Skill，用于生成精美的 **16:9 演示文稿**，支持两种互补模式：

1. **`image` 模式（默认）** — 将每一页幻灯片作为完整的 AI 视觉海报生成，通过严格 QA 后编译为标准 16:9 PDF（并自动生成全局 QA 预览拼图）。
2. **`editable-pptx` 模式** — 以通过 QA 的整页图片作为视觉准星，按页启动独立 Subagent 拆解为无字视觉图层（`visual-layers`）与原生可编辑文本框（`text-layer.json`），最终合成为可自由改字、移动图层的原生 `.pptx`。

Codex PPT 拒绝“廉价模板拼接 + 本地硬塞文字”的做法，而是让 Agent 像真正的 Deck 制片人一样工作：先写 Brief、梳理念叙事链（Storyline）、锁定设计系统（Design System）、编写逐页分镜（Storyboard）、跑严格 QA 返工循环，并自动校验最终交付产物。

---

## v0.3.0 更新亮点

- **三级画布坐标自动缩放（Canvas Auto-Normalization）**：`build_editable_ppt_from_layers.mjs` 现支持在 Deck、单页（Slide/Manifest）或单元素级别声明 `canvas: [width, height]`（如 `[1920, 1080]`），自动将视觉层与文本框坐标等比映射到 `--slide-size`（如 `960x540`），同时兼容 `[x, y, w, h]` 数组与 `{x, y, w, h}` 对象格式。
- **保留单页元数据与图层 Z-Order**：`merge_editable_slide_outputs.py` 与 PPTX 构建器完整保留每页独立的 `background`（背景色）、`canvas`、`route`（重建路径）、`zIndex` 图层叠放顺序，以及富文本样式（`italic`、`underline`、`charSpacing`、`lineSpacingMultiple`、`opacity`/`transparency`、`rotation`）。
- **一键生成 QA 预览拼图（`--contact-sheet`）**：`compile_slide_images_to_pdf.py` 支持直接输出带页码、文件名与分辨率标注的多列网格预览图（`qa/contact-sheet.jpg`），方便一眼排查整套 Deck 的风格漂移与排版问题。
- **自动化交付校验器（`verify_deck_outputs.py`）**：新增命令行校验工具，自动检查图片比例与最低分辨率、可编辑文本层越界与高重叠（IoU）风险、拦截图层清单路径穿越（Path Traversal），并直接解析 `.pptx` 内部 `ppt/slides/slide*.xml` 验证每页均包含原生可编辑 `<a:t>` 文本节点。
- **完整单元测试与 GitHub Actions CI**：补齐 Python（`pytest`）与 Node.js（`node:test`）测试套件及自动化流水线。

---

## 两种输出模式对比

| 维度 | `image` 模式（默认） | `editable-pptx` 模式 |
| :--- | :--- | :--- |
| **适用场景** | 产品 Pitch、概念提案、发布材料、强视觉风格汇报 | 需要后续在 PowerPoint / Keynote 中改字、调位置或团队二次编辑 |
| **视觉还原度** | 100% 整页海报级 AI 构图（字体与图形光影完全融合） | 无字 PNG 视觉层 + 原生可编辑文本框，兼顾视觉冲击力与可编辑性 |
| **QA 准则** | 出现错字或构图缺陷时，重写 Prompt 重新生成整页，禁止本地打补丁 | 先通过整页图 QA 锁定视觉目标，再抹除烘培文字并替换为原生文本框 |
| **交付产物** | `slides/*.png`、`qa/contact-sheet.jpg`、`final/deck.pdf` | 全部图片模式产物 + `editable/visual-layers/`、`text-layer.json`、`final/deck.editable.pptx` |

---

## 工作流

<p align="center">
  <img src="./assets/codex-ppt-workflow.png" alt="Codex PPT workflow diagram" width="100%">
</p>

核心原则非常简单：**在图片模式中，如果某一页未通过 QA，重写 Prompt 并重新生成整页，绝不在本地硬修文字或版式。** 可编辑模式仅在整页图片通过 QA 后启动，并将所有重建派生文件隔离在 `editable/` 目录下。

### Skill 的 7 阶段制片逻辑

1. **Brief（`brief.md`）**：明确受众、目标、页数、输出模式、语气、必含内容与约束。
2. **Storyline（`storyline.md`）**：在画页面之前先构建叙事链（`Hook -> Context -> Tension -> Insight -> Solution -> Evidence -> Action`）。
3. **Design System（`design-system.md`）**：锁定色彩角色、字号层级、安全边距、版式变体、图像风格与反向提示词。
4. **Storyboard（`storyboard.md`）**：规划每一页的叙事角色、标题、核心结论、上屏短文案、视觉主体与 QA 风险点。
5. **Generation（`prompts/` & `slides/`）**：逐页生成独立 Prompt 并渲染 16:9 完整页面图。
6. **QA Loop（`qa/qa.md` & `contact-sheet.jpg`）**：拒绝错字乱码、风格漂移、裁切拥挤或弱封面/弱收尾，返工直到全部通过。
7. **Export & Verification（`final/`）**：编译严格 16:9 PDF，或启动逐页 Subagent 图层拆解、合并、构建 `.pptx`，并通过 `verify_deck_outputs.py` 完成自动验收。

---

## 安装与使用

### 1. 安装 Skill

将仓库克隆到对应 Agent 的 Skills 目录（支持 **Codex**、**Claude Code**、**Antigravity** 等）：

```bash
# OpenAI Codex
git clone https://github.com/qybaihe/codex-ppt.git ~/.codex/skills/codex-ppt

# Claude Code / Antigravity
git clone https://github.com/qybaihe/codex-ppt.git ~/.gemini/antigravity/skills/codex-ppt
```

安装本地脚本依赖：

```bash
pip install -r ~/.codex/skills/codex-ppt/requirements.txt
npm install --prefix ~/.codex/skills/codex-ppt
```

### 2. 触发使用

**生成海报级图片 / PDF 演示文稿（默认）：**

```text
Use $codex-ppt to make a 10-page product pitch deck about my app idea.
```

**生成原生可编辑 PPTX（`editable-pptx` 模式）：**

```text
Use $codex-ppt to make an editable PPTX deck about my app idea with selectable text and movable layers.
```

---

## 命令行工具参考

### 1. 编译 16:9 PDF 与 QA 预览拼图

```bash
python scripts/compile_slide_images_to_pdf.py \
  /path/to/deck/slides \
  /path/to/deck/final/deck.pdf \
  --strict \
  --min-width 1280 \
  --contact-sheet /path/to/deck/qa/contact-sheet.jpg \
  --report /path/to/deck/qa/compile-report.json
```

### 2. 合并单页 Subagent 重建产物

```bash
python scripts/merge_editable_slide_outputs.py \
  /path/to/deck/editable/subagents \
  --out-layers-root /path/to/deck/editable/visual-layers \
  --out-text-json /path/to/deck/editable/text-layer.json \
  --canvas 1920x1080 \
  --force
```

### 3. 从视觉层与文本层构建可编辑 PPTX

```bash
node scripts/build_editable_ppt_from_layers.mjs \
  --backend auto \
  --layers-root /path/to/deck/editable/visual-layers \
  --text-json /path/to/deck/editable/text-layer.json \
  --out /path/to/deck/final/deck.editable.pptx \
  --slide-size 960x540 \
  --fail-on-text-fill
```

### 4. 自动校验交付物（图片、图层坐标与 PPTX 内部 XML）

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

## 示例效果

仓库内附带一套真实生成的 10 页孟菲斯风格产品提案（**SHIT APP Memphis Pitch**）：

- [最终 PDF](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pdf)
- [最终 PPTX](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pptx)
- [规划源文件（`brief`、`storyline`、`design-system`、`storyboard`、`qa`）](./examples/shit-app-memphis-pitch/source/)

### 部分页面预览

![SHIT APP cover](./examples/shit-app-memphis-pitch/slides/slide-01-cover.png)

![Product idea slide](./examples/shit-app-memphis-pitch/slides/slide-03-product-idea.png)

![Core flow slide](./examples/shit-app-memphis-pitch/slides/slide-05-core-flow.png)

![AI playbook slide](./examples/shit-app-memphis-pitch/slides/slide-07-ai-playbook.png)

![Roadmap closing slide](./examples/shit-app-memphis-pitch/slides/slide-10-roadmap-closing.png)

---

## 仓库结构

```text
.
├── SKILL.md                                    # 核心 Skill 工作流与硬性约束
├── agents/openai.yaml                          # Codex Skill 界面元数据
├── references/
│   ├── slide-quality-checklist.md              # 页面图片 QA 与重生规则
│   ├── editable-pptx-mode.md                   # 可编辑 PPTX 重建协议与质量门禁
│   └── editable-slide-subagent-prompt.md       # 单页重建 Subagent 提示词模版
├── scripts/
│   ├── compile_slide_images_to_pdf.py          # 16:9 PDF 编译器 + QA 预览拼图生成
│   ├── merge_editable_slide_outputs.py         # 单页图层与元数据合并脚本
│   ├── build_editable_ppt_from_layers.mjs      # 双后端可编辑 PPTX 构建器
│   ├── verify_deck_outputs.py                  # 图片/图层/PPTX 自动化验收脚本
│   ├── slide_utils.py                          # Python 公共工具与安全路径校验
│   └── lib/json_io.mjs                         # Node JSON 读写工具
├── tests/                                      # Pytest 与 Node 单元测试套件
├── assets/                                     # 头图与工作流架构图
└── examples/shit-app-memphis-pitch/            # 10 页完整示例 Deck
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
npm install
npm run test:all
```

## License

[MIT](./LICENSE)
