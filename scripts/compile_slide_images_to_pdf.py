#!/usr/bin/env python3
"""Compile ordered 16:9 slide images into a single PDF and optional QA contact sheet."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageColor, ImageDraw, ImageOps, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow is required. Install it with: python -m pip install Pillow"
    ) from exc

from slide_utils import (
    load_json,
    natural_key,
    parse_size,
    run_cli,
    write_json,
)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def load_manifest(path: Path) -> list[Path]:
    data = load_json(path)
    base = path.parent

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("slides"), list):
        items = data["slides"]
    else:
        raise ValueError("Manifest must be a JSON list or an object with a slides list")

    images: list[Path] = []
    for item in items:
        if isinstance(item, str):
            raw = item
        elif isinstance(item, dict):
            raw = item.get("image") or item.get("path") or item.get("file")
        else:
            raw = None

        if not raw:
            raise ValueError(f"Manifest item lacks an image path: {item!r}")

        candidate = Path(raw).expanduser()
        images.append(candidate if candidate.is_absolute() else base / candidate)

    return images


def collect_images(source: Path) -> list[Path]:
    source = source.expanduser()
    if source.is_dir():
        images = [
            path
            for path in source.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        return sorted(images, key=natural_key)

    if source.is_file() and source.suffix.lower() == ".json":
        return load_manifest(source)

    if source.is_file() and source.suffix.lower() in SUPPORTED_EXTENSIONS:
        return [source]

    raise FileNotFoundError(
        f"Input must be a directory, JSON manifest, or image file: {source}"
    )


def aspect_error(size: tuple[int, int], target: tuple[int, int]) -> float:
    width, height = size
    target_width, target_height = target
    return abs((width / height) - (target_width / target_height)) / (
        target_width / target_height
    )


def normalize_image(
    image: Image.Image,
    target_size: tuple[int, int],
    fit: str,
    background: tuple[int, int, int],
) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    target_width, target_height = target_size

    if fit == "stretch":
        return image.resize(target_size, Image.Resampling.LANCZOS)

    source_width, source_height = image.size
    if fit == "cover":
        scale = max(target_width / source_width, target_height / source_height)
        resized = image.resize(
            (round(source_width * scale), round(source_height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = (resized.width - target_width) // 2
        top = (resized.height - target_height) // 2
        return resized.crop((left, top, left + target_width, top + target_height))

    canvas = Image.new("RGB", target_size, background)
    image.thumbnail(target_size, Image.Resampling.LANCZOS)
    left = (target_width - image.width) // 2
    top = (target_height - image.height) // 2
    canvas.paste(image, (left, top))
    return canvas


def build_contact_sheet(
    pages: list[Image.Image],
    labels: list[str],
    columns: int = 3,
    thumb_size: tuple[int, int] = (480, 270),
) -> Image.Image:
    """Render a grid contact sheet of normalized slide images with captions."""
    if not pages:
        raise ValueError("Cannot build contact sheet from empty slide list")
    cols = max(1, min(columns, len(pages)))
    rows = math.ceil(len(pages) / cols)
    pad = 24
    header_h = 32
    thumb_w, thumb_h = thumb_size
    cell_w = thumb_w
    cell_h = header_h + thumb_h
    sheet_w = pad + cols * (cell_w + pad)
    sheet_h = pad + rows * (cell_h + pad)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)

    for idx, page in enumerate(pages):
        row = idx // cols
        col = idx % cols
        x0 = pad + col * (cell_w + pad)
        y0 = pad + row * (cell_h + pad)
        label = labels[idx] if idx < len(labels) else f"Slide {idx + 1:02d}"
        draw.text((x0 + 4, y0 + 8), label[:52], fill=(230, 234, 240))
        thumb = page.resize(thumb_size, Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x0, y0 + header_h))
        draw.rectangle(
            [x0, y0 + header_h, x0 + thumb_w - 1, y0 + header_h + thumb_h - 1],
            outline=(68, 74, 86),
            width=1,
        )

    return sheet


def build_pdf(args: argparse.Namespace) -> int:
    source = Path(args.input)
    output_pdf = Path(args.output_pdf).expanduser()
    target_size = args.target_size
    background = ImageColor.getrgb(args.background)
    image_paths = collect_images(source)

    if not image_paths:
        raise ValueError(f"No supported images found in {source}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    pages_dir = Path(args.pages_dir).expanduser() if args.pages_dir else None
    if pages_dir:
        pages_dir.mkdir(parents=True, exist_ok=True)

    min_width = getattr(args, "min_width", 0) or 0
    pages: list[Image.Image] = []
    labels: list[str] = []
    report: dict[str, Any] = {
        "input": str(source),
        "output_pdf": str(output_pdf),
        "target_size": f"{target_size[0]}x{target_size[1]}",
        "fit": args.fit,
        "strict": args.strict,
        "slide_count": len(image_paths),
        "slides": [],
    }

    for index, image_path in enumerate(image_paths, start=1):
        image_path = image_path.expanduser()
        if not image_path.exists():
            raise FileNotFoundError(f"Slide image not found: {image_path}")

        try:
            with Image.open(image_path) as image:
                image = ImageOps.exif_transpose(image)
                original_size = image.size
                error = aspect_error(original_size, target_size)
                warnings: list[str] = []

                if error > args.tolerance:
                    warnings.append(
                        f"aspect ratio differs by {error:.2%}; normalized with {args.fit}"
                    )

                if args.strict and error > args.tolerance:
                    raise ValueError(
                        f"{image_path.name} is {original_size[0]}x{original_size[1]}, "
                        f"not within {args.tolerance:.2%} of 16:9"
                    )

                if min_width > 0 and original_size[0] < min_width:
                    msg = (
                        f"width {original_size[0]}px is below minimum {min_width}px"
                    )
                    if args.strict:
                        raise ValueError(f"{image_path.name} {msg}")
                    warnings.append(msg)

                page = normalize_image(image, target_size, args.fit, background)
        except UnidentifiedImageError as exc:
            raise ValueError(f"Cannot read image file: {image_path}") from exc

        if pages_dir:
            normalized_name = f"slide-{index:02d}.png"
            page.save(pages_dir / normalized_name, "PNG")

        pages.append(page)
        labels.append(
            f"#{index:02d} {image_path.name} ({original_size[0]}x{original_size[1]})"
        )
        report["slides"].append(
            {
                "index": index,
                "source": str(image_path),
                "original_size": f"{original_size[0]}x{original_size[1]}",
                "aspect_error": round(error, 6),
                "warnings": warnings,
            }
        )

    first, rest = pages[0], pages[1:]
    first.save(
        output_pdf,
        "PDF",
        save_all=True,
        append_images=rest,
        resolution=args.dpi,
        quality=95,
    )

    contact_sheet_arg = getattr(args, "contact_sheet", None)
    if contact_sheet_arg:
        contact_path = Path(contact_sheet_arg).expanduser()
        contact_path.parent.mkdir(parents=True, exist_ok=True)
        columns = getattr(args, "columns", 3) or 3
        sheet = build_contact_sheet(pages, labels, columns=columns)
        sheet.save(contact_path, quality=92)
        report["contact_sheet"] = str(contact_path)
        print(f"Wrote contact sheet to {contact_path}")

    if args.report:
        report_path = Path(args.report).expanduser()
        write_json(report_path, report)

    print(f"Wrote {len(pages)} slides to {output_pdf}")
    if args.report:
        print(f"Wrote report to {args.report}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile ordered slide images into a 16:9 PDF."
    )
    parser.add_argument(
        "input",
        help="Directory of slide images, one image file, or JSON manifest.",
    )
    parser.add_argument("output_pdf", help="Output PDF path.")
    parser.add_argument(
        "--target-size",
        type=parse_size,
        default=(1920, 1080),
        help="Normalized slide size, default: 1920x1080.",
    )
    parser.add_argument(
        "--fit",
        choices=("contain", "cover", "stretch"),
        default="contain",
        help="How to normalize non-matching image sizes, default: contain.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when an image is not within the aspect-ratio tolerance.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Allowed relative aspect-ratio difference, default: 0.01.",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        default=0,
        help="Minimum source image width in pixels (warns or fails with --strict).",
    )
    parser.add_argument(
        "--background",
        default="#FFFFFF",
        help="Padding color for --fit contain, default: #FFFFFF.",
    )
    parser.add_argument(
        "--dpi",
        type=float,
        default=144.0,
        help="PDF image DPI, default: 144.",
    )
    parser.add_argument(
        "--pages-dir",
        help="Optional folder to write normalized PNG pages.",
    )
    parser.add_argument(
        "--contact-sheet",
        help="Optional output path for a visual QA contact-sheet grid image (PNG/JPG).",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=3,
        help="Number of columns in --contact-sheet grid, default: 3.",
    )
    parser.add_argument(
        "--report",
        help="Optional JSON report path.",
    )
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return run_cli(lambda: build_pdf(args))


if __name__ == "__main__":
    raise SystemExit(main())
