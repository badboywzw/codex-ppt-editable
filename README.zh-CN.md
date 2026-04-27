<p align="center">
  <img src="./assets/codex-ppt-hero.png" alt="Codex PPT 头图：AI-rendered slide decks, from brief to PDF" width="100%">
</p>

<p align="center">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

# Codex PPT

**Codex PPT** 是一个用于生成精美 16:9 演示文稿的 Codex Skill。它会把每一页 PPT 当作一张完整的 AI 生成页面图来制作，逐页检查后再编译成 PDF。

它适合那种“不能只是生成几页模板”的场景：你需要先讲清故事、锁定视觉系统、写好逐页提示词、跑 QA，再交付一套可以拿去讲的 deck。Codex PPT 会让 Codex 像一个小型 PPT 制片人一样工作：先规划，再定风格，再整页生成，再挑刺返工，最后导出。

## 它能做什么

- 把选题、提纲、报告或粗糙笔记变成完整的 PPT 生成计划。
- 自动写出 brief、storyline、design system、storyboard 和逐页 prompt。
- 把每一页最终幻灯片生成为一张完整 AI 图片，包括版式、文字、图表和视觉主体。
- 在交付前强制 QA：比例、可读性、页序、风格一致性、文字准确性。
- 把通过 QA 的页面图编译成严格 16:9 的 PDF。

## 工作流

<p align="center">
  <img src="./assets/codex-ppt-workflow.png" alt="Codex PPT workflow diagram" width="100%">
</p>

核心原则很简单：**如果某一页没有通过 QA，就重写 prompt 并重新生成整页。不要在本地修补文字或版式。**

## 安装

把仓库克隆到 Codex skills 目录：

```bash
git clone https://github.com/qybaihe/codex-ppt.git ~/.codex/skills/codex-ppt
```

然后对 Codex 说：

```text
Use $codex-ppt to make a 10-page product pitch deck about my app idea.
```

## 示例效果

仓库里包含一套真实生成过的示例 deck：

- [最终 PDF](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pdf)
- [最终 PPTX](./examples/shit-app-memphis-pitch/final/shit-app-memphis-pitch.pptx)
- [规划源文件](./examples/shit-app-memphis-pitch/source/)

### 部分页面

![SHIT APP cover](./examples/shit-app-memphis-pitch/slides/slide-01-cover.png)

![Product idea slide](./examples/shit-app-memphis-pitch/slides/slide-03-product-idea.png)

![Core flow slide](./examples/shit-app-memphis-pitch/slides/slide-05-core-flow.png)

![AI playbook slide](./examples/shit-app-memphis-pitch/slides/slide-07-ai-playbook.png)

![Roadmap closing slide](./examples/shit-app-memphis-pitch/slides/slide-10-roadmap-closing.png)

## 仓库结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/slide-quality-checklist.md
├── scripts/compile_slide_images_to_pdf.py
├── assets/
└── examples/shit-app-memphis-pitch/
```

## Skill 的思路

Codex PPT 会把 PPT 生产拆成几个阶段：

1. **Brief**：定义受众、目标、页数、语气、素材来源和约束。
2. **Storyline**：先写叙事链，再开始设计页面。
3. **Design system**：锁定配色、字号层级、网格、页面变体、图像语言和反模式。
4. **Storyboard**：明确每一页的角色、标题、主结论、文案计划、版式、视觉内容和 QA 风险。
5. **Generation**：为每一页写 prompt，并生成完整页面图。
6. **QA**：拒绝错字、风格漂移、拥挤构图、裁切内容和弱封面/弱结尾。
7. **Export**：把通过检查的页面图编译成 16:9 PDF。

## 为什么是图片型 PPT？

很多 AI PPT 方案会失败，是因为它们把通用模板、本地叠字和风格不一致的图形拼在一起。Codex PPT 反过来：每一页都先被当作一张完整的视觉海报来生成。

这让它特别适合产品提案、概念 deck、发布材料、视觉报告、创意方案和风格强烈的项目叙事。

## License

MIT
