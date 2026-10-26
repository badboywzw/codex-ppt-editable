#!/usr/bin/env python3
"""Shared utilities for Codex PPT Python scripts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any


def debug_enabled() -> bool:
    """Return True when CODEX_PPT_DEBUG is set to a truthy value."""
    return os.environ.get("CODEX_PPT_DEBUG", "").strip().lower() not in (
        "",
        "0",
        "false",
        "no",
    )


def natural_key(path: Path | str) -> list[Any]:
    """Return a natural-sort key that orders embedded numbers numerically."""
    name = path.name if isinstance(path, Path) else str(path)
    parts = re.split(r"(\d+)", name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def parse_size(value: str) -> tuple[int, int]:
    """Parse a 'WIDTHxHEIGHT' string into a positive (width, height) tuple."""
    match = re.fullmatch(r"(\d+)[xX](\d+)", str(value).strip())
    if not match:
        raise argparse.ArgumentTypeError("Size must look like 1920x1080")
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size values must be positive")
    return width, height


def parse_canvas(value: Any) -> tuple[int, int] | None:
    """Parse canvas dimensions from [w, h], 'WxH', or {'width': w, 'height': h}."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return parse_size(value)
        except argparse.ArgumentTypeError as exc:
            raise ValueError(f"Invalid canvas size string: {value!r}") from exc
    if isinstance(value, (list, tuple)) and len(value) == 2:
        width, height = int(value[0]), int(value[1])
        if width <= 0 or height <= 0:
            raise ValueError(f"Canvas dimensions must be positive: {value!r}")
        return width, height
    if isinstance(value, dict) and "width" in value and "height" in value:
        width, height = int(value["width"]), int(value["height"])
        if width <= 0 or height <= 0:
            raise ValueError(f"Canvas dimensions must be positive: {value!r}")
        return width, height
    raise ValueError(f"Unsupported canvas specification: {value!r}")


def resolve_safe_subpath(base_dir: Path, relative_file: str) -> Path:
    """Resolve a relative asset path and ensure it does not escape base_dir."""
    if not isinstance(relative_file, str) or not relative_file.strip():
        raise ValueError(f"Invalid asset file entry: {relative_file!r}")
    resolved_base = base_dir.expanduser().resolve()
    resolved_target = (resolved_base / relative_file).resolve()
    try:
        rel = resolved_target.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(
            f"Asset path escapes its slide folder ({base_dir}): {relative_file}"
        ) from exc
    if str(rel) in ("", "."):
        raise ValueError(
            f"Asset path must point to a file inside {base_dir}: {relative_file}"
        )
    return resolved_target


def load_json(path: Path) -> Any:
    """Read and parse a UTF-8 JSON file with a descriptive error on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    """Write data as pretty-printed UTF-8 JSON, creating parent folders if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_cli(func: Callable[[], int]) -> int:
    """Execute a CLI entry callable with standardized error output."""
    try:
        return func()
    except Exception as exc:
        if debug_enabled():
            traceback.print_exc()
        print(f"error: {exc}", file=sys.stderr)
        return 1
