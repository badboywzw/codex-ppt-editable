# Codex PPT — Editable Edition

## Let AI make the slides. Edit the words yourself.

**The original default workflow makes each whole slide one image. This edition
keeps pictures and text separate, so you can change the words directly in
PowerPoint or WPS after the deck is generated.**

> Based on the open-source Skill by **[@qybaihe](https://github.com/qybaihe)**.
> Original Skill: **https://github.com/qybaihe/codex-ppt**.
> Original MIT license and copyright retained. [Attribution](ATTRIBUTION.md)

**English** · [简体中文](README.md)

## What can it do?

- **Make a presentation:** give Codex a topic, page count and style, or an outline/report.
- **Let you edit the words:** change titles, body copy, labels, numbers and page markers in PowerPoint or WPS.
- **Continue after your edits:** give AI your latest saved PPTX to revise content or add slides while preserving your work.
- **Avoid repeating finished work:** reuse suitable images/pages and resume completed work after an interruption.

## What is easier now?

| You want to… | Original default workflow | This edition |
| --- | --- | --- |
| Fix a typo | Words are part of a whole-slide image | Double-click the text in PowerPoint/WPS |
| Keep the visual and change the wording | Ask AI to reprocess the page | Keep the picture and edit the words yourself |
| Add slides after manual editing | Manual changes are hard to carry into generation | Continue from the latest saved PPTX |

**Editing words yourself needs no new AI call.** Complex illustrations can stay
images and be replaced as a whole; their internal details are not native shapes.
Longer wording may need a larger text box or smaller font.

## Just ask

```text
Use $codex-ppt to make an 8-slide beginner piano deck.
White background, technology blue, 16:9. I want to edit the words myself.
```

```text
Here is the PPTX I edited. Keep my changes, update the practice tip,
and add a slide called “Next practice” in the same style.
```

Open the delivered `.pptx` in PowerPoint or WPS, double-click text to edit, and
save. When asking AI to continue, supply that latest saved file.

## Install

Give Codex this repository URL and ask it to install the Skill. Its installed
name remains **`codex-ppt`**, invoked as **`$codex-ppt`**.

<details>
<summary>Manual setup and technical documentation</summary>

Keep the directory containing `SKILL.md` named `codex-ppt` and place/link it
in a discovery location supported by your Codex setup. From the Skill directory:

```bash
python -m pip install -r requirements.txt
npm ci
```

The project CLI needs Python 3.11+ and Node.js. Previews also need LibreOffice,
Poppler (`pdfinfo`, `pdftoppm`) and `pypdf`. Reuse existing dependencies when
available. Override paths with `--node`, `--soffice`, `--pdftoppm`, `--temp-dir`.

```bash
python scripts/deck.py init /path/to/project --title "Piano basics"
# Edit deck.json and provide the planned artwork.
python scripts/deck.py plan /path/to/project/deck.json
python scripts/deck.py build /path/to/project/deck.json

python scripts/deck.py import-pptx /path/to/my-edited.pptx /path/to/continued-project
python scripts/deck.py build /path/to/continued-project/deck.json
```

Codex generates artwork through its available image tool. The project CLI
does not call image APIs or install dependencies itself.

- [Projects and layouts](references/deck-project.md)
- [Textless artwork first](references/textless-first-mode.md)
- [Continue an existing PPTX](references/native-pptx-mode.md)
- [Caching and recovery](references/resume-and-cache.md)
- [Existing-image reconstruction](references/editable-pptx-mode.md)
- [Image-only output](references/image-mode.md)
- [Quality checklist](references/slide-quality-checklist.md)
- [Release description](RELEASE_NOTES.md)

Manual edits do not update old JSON; import the latest saved PPTX to continue.
Appending pages currently requires a 16:9 base. Mixed-format text and grouped
shapes have edit restrictions. Caches are per project. Shared image/theme/page
number changes can invalidate several pages; the final PPTX is still assembled
as a complete file. Automated checks do not replace visual review.

```bash
python -m unittest discover -s tests -v
```

Tests needing missing external tools are skipped. Set `CODEX_PPT_NODE` and
`CODEX_PPT_TEST_DIR` for explicit tool/temp paths. Windows has been tested
locally; other systems need validation in their own environment.

</details>

## Attribution and license

Original author: **[@qybaihe](https://github.com/qybaihe)**.
Original Skill: **[qybaihe/codex-ppt](https://github.com/qybaihe/codex-ppt)**.

Comparisons refer to the imported upstream revision recorded in [ATTRIBUTION.md](ATTRIBUTION.md).
Promotional assets and the [SHIT APP example](examples/shit-app-memphis-pitch/README.md)
were inherited from that repository.

The original [MIT LICENSE](LICENSE) is retained unchanged:
`Copyright (c) 2026 qybaihe`.
