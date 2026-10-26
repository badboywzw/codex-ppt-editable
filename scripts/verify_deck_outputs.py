#!/usr/bin/env python3
"""Automated QA verifier for Codex PPT slide images, editable layers, and PPTX deliverables."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from compile_slide_images_to_pdf import aspect_error, collect_images
from merge_editable_slide_outputs import validate_page_manifest
from slide_utils import (
    load_json,
    natural_key,
    parse_canvas,
    parse_size,
    run_cli,
    write_json,
)

DRAWINGML_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PRESENTATIONML_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _box_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Compute intersection-over-union of two (x, y, w, h) rectangles."""
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = (aw * ah) + (bw * bh) - inter
    return inter / union if union > 0 else 0.0


def inspect_slides_dir(
    slides_dir: Path,
    target_size: tuple[int, int] = (1920, 1080),
    tolerance: float = 0.01,
    min_width: int = 1280,
) -> dict[str, Any]:
    """Verify ordered slide images for aspect ratio, resolution, and readability."""
    images = collect_images(slides_dir)
    errors: list[str] = []
    warnings: list[str] = []
    items: list[dict[str, Any]] = []

    if not images:
        errors.append(f"No slide images found in {slides_dir}")

    for idx, img_path in enumerate(images, start=1):
        try:
            with Image.open(img_path) as raw_img:
                img = ImageOps.exif_transpose(raw_img)
                w, h = img.size
        except (UnidentifiedImageError, OSError) as exc:
            errors.append(f"Slide {idx:02d} ({img_path.name}) is unreadable: {exc}")
            continue

        err = aspect_error((w, h), target_size)
        slide_issues: list[str] = []
        if err > tolerance:
            msg = f"Slide {idx:02d} ({img_path.name}) is {w}x{h} (aspect error {err:.2%} > {tolerance:.2%})"
            errors.append(msg)
            slide_issues.append(msg)
        if min_width > 0 and w < min_width:
            msg = f"Slide {idx:02d} ({img_path.name}) width {w}px < {min_width}px"
            warnings.append(msg)
            slide_issues.append(msg)

        items.append(
            {
                "slide": idx,
                "file": img_path.name,
                "size": f"{w}x{h}",
                "aspect_error": round(err, 6),
                "issues": slide_issues,
            }
        )

    return {
        "slide_count": len(images),
        "slides": items,
        "errors": errors,
        "warnings": warnings,
    }


def inspect_editable_layers(
    text_json_path: Path,
    layers_root: Path | None = None,
    default_canvas: tuple[int, int] = (960, 540),
    disallow_text_fill: bool = False,
) -> dict[str, Any]:
    """Verify text-layer.json and optional visual-layers root for bounds, overlaps, and assets."""
    data = load_json(text_json_path)
    errors: list[str] = []
    warnings: list[str] = []
    slide_reports: list[dict[str, Any]] = []

    if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
        errors.append(f"text-layer.json must contain a 'slides' array: {text_json_path}")
        return {"slide_count": 0, "slides": [], "errors": errors, "warnings": warnings}

    deck_canvas = parse_canvas(data.get("canvas") or data.get("sourceCanvas")) or default_canvas

    for idx, slide in enumerate(data["slides"], start=1):
        slide_no = int(slide.get("slide", idx))
        slide_canvas = (
            parse_canvas(slide.get("canvas") or slide.get("sourceCanvas")) or deck_canvas
        )
        cw, ch = slide_canvas
        texts = slide.get("texts", [])
        if not isinstance(texts, list):
            errors.append(f"Slide {slide_no:02d}: 'texts' must be a list")
            continue

        boxes: list[tuple[int, str, tuple[float, float, float, float]]] = []
        for t_idx, item in enumerate(texts, start=1):
            name = str(item.get("name") or f"text-{t_idx}")
            text_val = str(item.get("text") or "").strip()
            if not text_val:
                warnings.append(f"Slide {slide_no:02d} {name}: empty text string")

            item_canvas = (
                parse_canvas(item.get("canvas") or item.get("sourceCanvas")) or slide_canvas
            )
            icw, ich = item_canvas
            x = float(item.get("x", item.get("left", 0)))
            y = float(item.get("y", item.get("top", 0)))
            w = float(item.get("w", item.get("width", 0)))
            h = float(item.get("h", item.get("height", 0)))

            if w <= 0 or h <= 0:
                errors.append(
                    f"Slide {slide_no:02d} {name}: non-positive box dimensions ({w}x{h})"
                )
            if x < -icw * 0.05 or y < -ich * 0.05 or (x + w) > icw * 1.08 or (y + h) > ich * 1.08:
                warnings.append(
                    f"Slide {slide_no:02d} {name}: box ({x:.1f},{y:.1f},{w:.1f},{h:.1f}) extends outside canvas {icw}x{ich}"
                )

            if disallow_text_fill:
                fill = item.get("fill")
                line = item.get("line")
                if fill not in (None, "", "none", "transparent", "#00000000"):
                    errors.append(f"Slide {slide_no:02d} {name}: disallowed text fill {fill!r}")
                if line not in (None, "", "none", "transparent", "#00000000"):
                    errors.append(f"Slide {slide_no:02d} {name}: disallowed text line {line!r}")

            norm_box = (x / icw * cw, y / ich * ch, max(1.0, w / icw * cw), max(1.0, h / ich * ch))
            for prev_idx, prev_name, prev_box in boxes:
                iou = _box_iou(norm_box, prev_box)
                if iou > 0.75:
                    warnings.append(
                        f"Slide {slide_no:02d}: text boxes '{prev_name}' (#{prev_idx}) and '{name}' (#{t_idx}) overlap heavily (IoU={iou:.2f})"
                    )
            boxes.append((t_idx, name, norm_box))

        asset_count = 0
        if layers_root is not None:
            page_dir = layers_root / f"slide-{slide_no:02d}"
            if not page_dir.is_dir():
                errors.append(f"Slide {slide_no:02d}: missing visual layer directory {page_dir}")
            else:
                try:
                    manifest = validate_page_manifest(page_dir, check_assets=True)
                    asset_count = len(manifest.get("assets", []))
                except Exception as exc:
                    errors.append(f"Slide {slide_no:02d}: {exc}")

        slide_reports.append(
            {
                "slide": slide_no,
                "canvas": f"{cw}x{ch}",
                "text_count": len(texts),
                "asset_count": asset_count,
            }
        )

    return {
        "slide_count": len(data["slides"]),
        "slides": slide_reports,
        "errors": errors,
        "warnings": warnings,
    }


def inspect_pptx(pptx_path: Path, require_editable_text: bool = False) -> dict[str, Any]:
    """Open a .pptx ZIP archive and inspect slide count, semantic text runs, and embedded images."""
    errors: list[str] = []
    warnings: list[str] = []
    slide_summaries: list[dict[str, Any]] = []

    if not pptx_path.is_file():
        return {
            "slide_count": 0,
            "slides": [],
            "errors": [f"PPTX file not found: {pptx_path}"],
            "warnings": [],
        }

    try:
        with zipfile.ZipFile(pptx_path, "r") as zf:
            names = zf.namelist()
            if "[Content_Types].xml" not in names:
                errors.append(f"Missing [Content_Types].xml in {pptx_path}")
            slide_files = sorted(
                [
                    name
                    for name in names
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ],
                key=natural_key,
            )
            if not slide_files:
                errors.append(f"No slide XML files found inside {pptx_path}")

            for idx, slide_xml_name in enumerate(slide_files, start=1):
                raw_xml = zf.read(slide_xml_name)
                root = ET.fromstring(raw_xml)
                texts = [
                    node.text.strip()
                    for node in root.iter(f"{DRAWINGML_NS}t")
                    if node.text and node.text.strip()
                ]
                pics = list(root.iter(f"{PRESENTATIONML_NS}pic"))
                if require_editable_text and not texts:
                    errors.append(
                        f"PPTX slide {idx:02d} ({slide_xml_name}) contains no editable text runs (<a:t>)"
                    )
                slide_summaries.append(
                    {
                        "slide": idx,
                        "xml": slide_xml_name,
                        "text_run_count": len(texts),
                        "image_count": len(pics),
                        "sample_texts": texts[:5],
                    }
                )
    except zipfile.BadZipFile as exc:
        errors.append(f"Invalid PPTX zip archive {pptx_path}: {exc}")
    except ET.ParseError as exc:
        errors.append(f"Corrupted XML inside {pptx_path}: {exc}")

    return {
        "slide_count": len(slide_summaries),
        "slides": slide_summaries,
        "errors": errors,
        "warnings": warnings,
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify Codex PPT slide images, editable layer specs, and final PPTX deliverables."
    )
    parser.add_argument("--slides-dir", help="Directory of slide images to verify.")
    parser.add_argument(
        "--target-size",
        type=parse_size,
        default=(1920, 1080),
        help="Target slide image dimensions, default: 1920x1080.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Relative aspect-ratio tolerance for slide images, default: 0.01.",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        default=1280,
        help="Minimum recommended image width in pixels, default: 1280.",
    )
    parser.add_argument("--text-json", help="Path to consolidated text-layer.json.")
    parser.add_argument("--layers-root", help="Path to consolidated visual-layers folder.")
    parser.add_argument(
        "--disallow-text-fill",
        action="store_true",
        help="Fail when any text box in text-layer.json defines a visible fill or outline.",
    )
    parser.add_argument("--pptx", help="Path to exported .pptx file to inspect.")
    parser.add_argument(
        "--require-editable-text",
        action="store_true",
        help="Fail if any slide in --pptx has zero editable <a:t> text runs.",
    )
    parser.add_argument(
        "--expected-slides",
        type=int,
        help="Expected number of slides across all provided artifacts.",
    )
    parser.add_argument("--report", help="Optional path to write the JSON verification report.")
    return parser


def _run_verify() -> int:
    parser = make_parser()
    args = parser.parse_args()

    if not any([args.slides_dir, args.text_json, args.pptx]):
        parser.error("Provide at least one of --slides-dir, --text-json, or --pptx")

    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {"ok": True}
    counts: dict[str, int] = {}

    if args.slides_dir:
        slides_res = inspect_slides_dir(
            Path(args.slides_dir).expanduser(),
            target_size=args.target_size,
            tolerance=args.tolerance,
            min_width=args.min_width,
        )
        summary["slides_dir"] = slides_res
        counts["slides_dir"] = slides_res["slide_count"]
        errors.extend(slides_res["errors"])
        warnings.extend(slides_res["warnings"])

    if args.text_json:
        layers_root = Path(args.layers_root).expanduser() if args.layers_root else None
        editable_res = inspect_editable_layers(
            Path(args.text_json).expanduser(),
            layers_root=layers_root,
            disallow_text_fill=args.disallow_text_fill,
        )
        summary["editable_layers"] = editable_res
        counts["editable_layers"] = editable_res["slide_count"]
        errors.extend(editable_res["errors"])
        warnings.extend(editable_res["warnings"])

    if args.pptx:
        pptx_res = inspect_pptx(
            Path(args.pptx).expanduser(),
            require_editable_text=args.require_editable_text,
        )
        summary["pptx"] = pptx_res
        counts["pptx"] = pptx_res["slide_count"]
        errors.extend(pptx_res["errors"])
        warnings.extend(pptx_res["warnings"])

    if args.expected_slides is not None:
        for section, count in counts.items():
            if count != args.expected_slides:
                errors.append(
                    f"{section} has {count} slides, expected {args.expected_slides}"
                )
    elif len(set(counts.values())) > 1:
        errors.append(f"Slide count mismatch across artifacts: {counts}")

    summary["errors"] = errors
    summary["warnings"] = warnings
    summary["ok"] = len(errors) == 0

    if args.report:
        write_json(Path(args.report).expanduser(), summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


def main() -> int:
    return run_cli(_run_verify)


if __name__ == "__main__":
    raise SystemExit(main())
