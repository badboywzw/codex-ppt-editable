#!/usr/bin/env python3
"""Merge per-slide editable reconstruction outputs into one builder input."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from slide_utils import (
    load_json,
    natural_key,
    parse_canvas,
    resolve_safe_subpath,
    run_cli,
    write_json,
)


def slide_number(path: Path, fallback: int) -> int:
    match = re.search(r"(\d+)", path.name)
    return int(match.group(1)) if match else fallback


def find_text_layer(slide_dir: Path) -> Path:
    candidates = [
        slide_dir / "text-layer.json",
        slide_dir / "editable" / "text-layer.json",
        slide_dir / "output" / "text-layer.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = sorted(slide_dir.glob("**/text-layer.json"), key=natural_key)
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No text-layer.json found under {slide_dir}")


def _locate_slide_node(data: dict[str, Any], slide_no: int) -> dict[str, Any]:
    """Return the dictionary representing the target slide inside text-layer.json."""
    if isinstance(data.get("texts"), list):
        return data

    slides = data.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("Text layer must contain texts or slides")

    for slide in slides:
        if (
            isinstance(slide, dict)
            and int(slide.get("slide", slide_no)) == slide_no
            and isinstance(slide.get("texts"), list)
        ):
            return slide

    first = slides[0]
    if isinstance(first, dict) and isinstance(first.get("texts"), list):
        return first
    raise ValueError("No texts array found in text layer")


def extract_texts(text_layer: Path, slide_no: int) -> list[dict[str, Any]]:
    data = load_json(text_layer)
    if not isinstance(data, dict):
        raise ValueError(f"Text layer root must be a JSON object: {text_layer}")
    try:
        node = _locate_slide_node(data, slide_no)
    except ValueError as exc:
        raise ValueError(f"{exc}: {text_layer}") from exc
    return node["texts"]


def extract_slide_entry(
    text_layer: Path,
    slide_no: int,
    manifest_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract the slide's texts plus optional per-slide metadata (background, canvas, route)."""
    data = load_json(text_layer)
    if not isinstance(data, dict):
        raise ValueError(f"Text layer root must be a JSON object: {text_layer}")
    try:
        node = _locate_slide_node(data, slide_no)
    except ValueError as exc:
        raise ValueError(f"{exc}: {text_layer}") from exc

    entry: dict[str, Any] = {
        "slide": slide_no,
        "texts": node["texts"],
    }

    background = (
        node.get("background")
        or data.get("background")
        or (manifest_data.get("background") if isinstance(manifest_data, dict) else None)
    )
    if background:
        entry["background"] = background

    raw_canvas = (
        node.get("canvas")
        or node.get("sourceCanvas")
        or data.get("canvas")
        or data.get("sourceCanvas")
        or (
            manifest_data.get("canvas") or manifest_data.get("sourceCanvas")
            if isinstance(manifest_data, dict)
            else None
        )
    )
    if raw_canvas is not None:
        parsed = parse_canvas(raw_canvas)
        if parsed:
            entry["canvas"] = [parsed[0], parsed[1]]

    route = node.get("route") or data.get("route") or (
        manifest_data.get("route") if isinstance(manifest_data, dict) else None
    )
    if route:
        entry["route"] = route

    return entry


def validate_page_manifest(page_dir: Path, check_assets: bool = True) -> dict[str, Any]:
    """Load and validate manifest.json inside page_dir, checking asset paths."""
    manifest_path = page_dir / "manifest.json"
    data = load_json(manifest_path)
    if not isinstance(data, dict):
        raise ValueError(f"Visual layer manifest must be a JSON object: {manifest_path}")
    assets = data.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError(f"Manifest 'assets' must be a list: {manifest_path}")
    for asset in assets:
        if not isinstance(asset, dict) or not asset.get("file"):
            raise ValueError(f"Manifest asset entry missing 'file' in {manifest_path}: {asset!r}")
        resolved = resolve_safe_subpath(page_dir, str(asset["file"]))
        if check_assets and not resolved.is_file():
            raise FileNotFoundError(
                f"Visual layer asset '{asset['file']}' referenced in {manifest_path} does not exist"
            )
    return data


def find_page_dir(slide_dir: Path, slide_no: int) -> Path:
    candidates = [
        slide_dir / "visual-layers" / f"slide-{slide_no:02d}",
        slide_dir / "visual-layers" / f"{slide_no:02d}",
        slide_dir / "visual-layers" / "slide-01",
        slide_dir / "visual-layers",
        slide_dir / "layers" / f"slide-{slide_no:02d}",
        slide_dir / "layers" / "slide-01",
    ]
    for candidate in candidates:
        if (candidate / "manifest.json").is_file():
            return candidate

    roots = [slide_dir / "visual-layers", slide_dir / "layers", slide_dir]
    for root in roots:
        if not root.is_dir():
            continue
        matches = sorted(
            [path.parent for path in root.glob("**/manifest.json")],
            key=natural_key,
        )
        if matches:
            return matches[0]
    raise FileNotFoundError(f"No visual layer manifest found under {slide_dir}")


def collect_slide_dirs(slides_root: Path, pattern: str) -> list[Path]:
    if not slides_root.is_dir():
        raise NotADirectoryError(f"Slides root is not a directory: {slides_root}")
    dirs = sorted(
        [path for path in slides_root.glob(pattern) if path.is_dir()],
        key=natural_key,
    )
    if not dirs:
        dirs = sorted(
            [path for path in slides_root.iterdir() if path.is_dir()],
            key=natural_key,
        )
    if not dirs:
        raise ValueError(f"No slide directories found under {slides_root}")
    return dirs


def _run_merge() -> int:
    parser = argparse.ArgumentParser(
        description="Merge one editable reconstruction folder per slide into a consolidated visual-layers root and text-layer.json."
    )
    parser.add_argument(
        "slides_root", help="Folder containing per-slide reconstruction folders."
    )
    parser.add_argument(
        "--slide-glob",
        default="slide-*",
        help="Glob for slide folders, default: slide-*.",
    )
    parser.add_argument(
        "--out-layers-root", required=True, help="Output visual-layers folder."
    )
    parser.add_argument(
        "--out-text-json", required=True, help="Output consolidated text-layer.json."
    )
    parser.add_argument(
        "--background", default="#FFFFFF", help="Deck background color metadata."
    )
    parser.add_argument(
        "--canvas",
        help="Optional default source canvas size (e.g. 1920x1080) recorded in text-layer.json.",
    )
    parser.add_argument(
        "--skip-asset-check",
        action="store_true",
        help="Do not fail when an image file listed in manifest.json is missing on disk.",
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing output page folders."
    )
    args = parser.parse_args()

    slides_root = Path(args.slides_root).expanduser()
    out_layers_root = Path(args.out_layers_root).expanduser()
    out_text_json = Path(args.out_text_json).expanduser()
    slide_dirs = collect_slide_dirs(slides_root, args.slide_glob)

    out_layers_root.mkdir(parents=True, exist_ok=True)
    out_text_json.parent.mkdir(parents=True, exist_ok=True)

    slides: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []
    seen_slides: dict[int, Path] = {}

    for index, slide_dir in enumerate(slide_dirs, start=1):
        number = slide_number(slide_dir, index)
        if number in seen_slides:
            raise ValueError(
                f"Duplicate slide number {number:02d}: {slide_dir} conflicts with {seen_slides[number]}"
            )
        seen_slides[number] = slide_dir

        page_name = f"slide-{number:02d}"
        text_layer = find_text_layer(slide_dir)
        page_dir = find_page_dir(slide_dir, number)
        manifest_data = validate_page_manifest(
            page_dir, check_assets=not args.skip_asset_check
        )

        dest = out_layers_root / page_name
        if dest.exists():
            if not args.force:
                raise FileExistsError(f"Output page folder already exists: {dest}")
            shutil.rmtree(dest)
        shutil.copytree(page_dir, dest)

        slide_entry = extract_slide_entry(text_layer, number, manifest_data)
        texts = slide_entry["texts"]
        slides.append(slide_entry)
        report.append(
            {
                "slide": number,
                "source_dir": str(slide_dir),
                "visual_layers": str(dest),
                "text_layer": str(text_layer),
                "asset_count": len(manifest_data.get("assets", [])),
                "text_count": len(texts),
                **({"route": slide_entry["route"]} if "route" in slide_entry else {}),
            }
        )

    deck: dict[str, Any] = {"background": args.background, "slides": slides}
    if args.canvas:
        parsed_canvas = parse_canvas(args.canvas)
        if parsed_canvas:
            deck["canvas"] = [parsed_canvas[0], parsed_canvas[1]]

    write_json(out_text_json, deck)
    print(
        json.dumps(
            {
                "slides": report,
                "text_json": str(out_text_json),
                "layers_root": str(out_layers_root),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    return run_cli(_run_merge)


if __name__ == "__main__":
    raise SystemExit(main())
