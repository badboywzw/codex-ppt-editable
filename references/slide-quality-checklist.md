# Slide Quality Checklist

Use this checklist for the selected output mode. New editable decks combine textless artwork and native text. Full-page AI text requirements apply only to `image` mode.

## Preflight

- All expected slides exist and match the storyboard count.
- Filenames sort in the intended order, such as `slide-01-cover.png`, `slide-02-agenda.png`.
- Every page is landscape 16:9. Prefer 1920x1080 or higher.
- In `image` mode, every final page is a full-slide AI-generated image. In editable modes, linguistic text is native and the corresponding artwork regions are free of baked words.
- Slide content stays inside a safe area; no title, label, logo, or page number touches the edge.
- The cover and closing slide feel intentionally designed, not like generic placeholders.

## Story and Content

- The deck has a visible chain: hook, context, tension, insight, evidence, conclusion, action.
- Each slide has one main takeaway.
- The title states the point, not just the topic.
- Body copy is concise enough to read in a presentation setting.
- Data, claims, and examples match the user's source material.
- No slide introduces an unexplained term, random statistic, or unsupported claim.

## Visual System

- Palette, type scale, margins, grid, icon style, and image treatment are consistent.
- Layout variants repeat intentionally instead of changing randomly.
- Visual density fits the audience and purpose.
- Important information is not buried under decorative images.
- Charts and diagrams have clear labels, enough contrast, and no fake precision.

## AI Image Issues

Repair the affected artwork when you see the following; regenerate a full page only when that page is the image-mode deliverable or the entire artwork is defective:

- misspelled, nonsensical, or warped text
- random symbols, fake logos, or stray marks
- distorted UI, charts, hands, faces, buildings, or products
- inconsistent style compared with the rest of the deck
- blur, low contrast, tiny text, or unreadable labels
- crowded composition with no clear focal point
- important content cropped near the edges

## Text Handling

- In editable modes, fix words, line breaks, sizes and positions in the native text source. Reuse the artwork; do not call image generation for a text-only correction.
- Run `check_editable_pptx.py` against the text source to check native text retention and transparent boxes. This does not replace visual inspection of raster layers or line wrapping.
- In `image` mode, visible text belongs in the AI-rendered page. Do not repair it with deterministic overlays; revise and regenerate that page.
- Keep titles short and legible.
- Preserve the user's terminology exactly.
- Check Chinese punctuation, line breaks, and mixed Chinese/English spacing.

## Regeneration Rules

- Regenerate when the composition, style, or image quality is wrong.
- In editable modes, repair text placement/alignment/labels in the text source. In `image` mode, regenerate the page instead of adding overlays.
- Rewrite the prompt before regenerating; do not repeat a failed vague prompt.
- Tighten the prompt with the exact slide role, composition, safe area, and negative prompt.
- Shorten or split a slide when the image model cannot render dense text legibly.
- Update `qa/qa.md` after every fix so the final PDF has an auditable trail.

## PDF Final Check

- Page count equals the approved slide count.
- Page order matches `storyboard.md`.
- All pages have the same 16:9 dimensions.
- No slide has accidental padding, letterboxing or cropping. Editable previews can contain the intended native text composition; image-mode pages cannot use corrective overlays.
- The first page works as a cover and the last page works as a confident ending.
