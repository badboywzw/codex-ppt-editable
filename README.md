# Codex PPT 可编辑版

## AI 帮你做 PPT，生成后你还能自己改字

**以前，一整页都是图片，想改一个字也不方便。这个改进版把图片和文字分开：
生成的 PPT 中，文字可以直接在 PowerPoint 或 WPS 里自由修改。**

> 基于 **[@qybaihe](https://github.com/qybaihe)** 的开源项目改进。
> 原 Skill 地址：**[github.com/qybaihe/codex-ppt](https://github.com/qybaihe/codex-ppt)**。
> 感谢原作者，原 MIT 许可证及版权声明完整保留。[查看来源](ATTRIBUTION.md)

[English](README.en.md) · **简体中文**

## 它能帮你做什么？

- **帮你做 PPT**：告诉 AI 主题、页数和风格，或给它一份提纲、报告，就能开始制作。
- **做好后自己改字**：标题、正文、字母、数字和页码都可以选中修改，调字号、改颜色、挪位置也可以。
- **改完还能接着做**：把你保存的 PPT 再交给 AI，可以接着改内容、加页面，保留你已经改好的部分。
- **小修改少走回头路**：能复用的页面和图片就继续用；中途打断后，也能接着已完成的部分继续。

## 比以前方便在哪里？

| 你想做的事 | 原版默认流程 | 这个改进版 |
| --- | --- | --- |
| 改一个错字 | 整页是图片，不能直接选中文字 | 打开 PPT，双击文字就能改 |
| 保留好看的画面，换一下文案 | 往往需要让 AI 再处理页面 | 图片保留，文字自己改 |
| 自己改过后，再让 AI 加两页 | 手动改动不容易带入后续制作 | 以你最新保存的 PPT 接着做 |

**自己改字时，不需要再次调用 AI，也不用每改一个词都等它重新生成。**

## 怎么用？直接这样说

```text
用 $codex-ppt 做一份8页钢琴入门PPT。
白底、科技蓝、16:9，给我能自己修改文字的PPT。
```

也可以做课程讲义、工作汇报、产品介绍等内容。想要别的风格，直接说明。

如果你已经手动改过：

```text
这是我改过的PPT。保留我的修改，把练习提示改一下，
再加一页“下次练习计划”，风格和前面一致。
```

## 做好后，我怎么自己改？

1. 用 **PowerPoint 或 WPS** 打开生成的 `.pptx` 文件。
2. 双击文字，直接修改；选中文字框，可以移动位置或调整字号、颜色。
3. 保存。以后需要 AI 继续做时，把**最新保存的文件**交给它。

图片仍然是图片，可以整体替换；人物、光影和复杂插画内部不能像文字一样逐项修改。
把文字写得更长时，可能需要自己拉大文字框或调小字号。

## 安装

把本仓库地址交给 Codex，让它安装其中的 `codex-ppt` Skill。
安装后的名称是 **`codex-ppt`**，所以使用时写 **`$codex-ppt`**。

<details>
<summary>给需要手动安装或维护的人：环境、命令和技术文档</summary>

下载本仓库，保留包含 `SKILL.md` 的文件夹，将其命名为 `codex-ppt`，
接入你当前 Codex 配置支持的 Skill 发现位置。实际文件可放其他磁盘，通过目录链接发现。

在 Skill 目录安装依赖：

```bash
python -m pip install -r requirements.txt
npm ci
```

项目脚本需要 Python 3.11+、Node.js；预览还需要 LibreOffice、Poppler
（`pdfinfo`、`pdftoppm`）及 `pypdf`。已有运行环境时直接复用。

```bash
python scripts/deck.py init /path/to/project --title "钢琴入门"
# 修改项目中的 deck.json，再补齐所需素材。
python scripts/deck.py plan /path/to/project/deck.json
python scripts/deck.py build /path/to/project/deck.json

# 接着手动改过的文件继续：
python scripts/deck.py import-pptx /path/to/my-edited.pptx /path/to/continued-project
python scripts/deck.py build /path/to/continued-project/deck.json
```

可用 `--node`、`--soffice`、`--pdftoppm`、`--temp-dir` 指定本机路径。
图片由 Codex 调用可用的图像工具生成，CLI 自身不会调用图像 API 或自动安装依赖。

- [项目与布局](references/deck-project.md)
- [直接生成无字素材](references/textless-first-mode.md)
- [接着已有 PPT 制作](references/native-pptx-mode.md)
- [缓存、中断和并发](references/resume-and-cache.md)
- [已有图片的重建](references/editable-pptx-mode.md)
- [纯图片输出](references/image-mode.md)
- [质量检查](references/slide-quality-checklist.md)
- [发布介绍](RELEASE_NOTES.md)

手动改 PPTX 不会自动更新旧项目的 JSON，续作时应导入最新文件。
追加页目前需要 16:9 文件；混合格式文字、组合内对象有编辑限制。
缓存按项目保存；共享图片、主题和页码变化可能影响多页，完整 PPTX 仍需组装。
自动检查不能替代人工检查最终画面。

```bash
python -m unittest discover -s tests -v
```

Node 或渲染器缺失时，对应测试会跳过；可设置 `CODEX_PPT_NODE` 和
`CODEX_PPT_TEST_DIR`。Windows 已做本机验证，其他系统仍需在对应环境验证。

</details>

## 来源与许可证

原作者：**[@qybaihe](https://github.com/qybaihe)**。
原 Skill：**[qybaihe/codex-ppt](https://github.com/qybaihe/codex-ppt)**。

这里的对比针对本版本基于的原版流程，[具体来源版本](ATTRIBUTION.md)已记录。
仓库中的宣传图和 [SHIT APP 示例](examples/shit-app-memphis-pitch/README.md)来自原仓库。

原 [MIT LICENSE](LICENSE) 完整保留：`Copyright (c) 2026 qybaihe`。
