from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from PIL import Image

import compile_slide_images_to_pdf as compile_mod
from slide_utils import natural_key, parse_canvas, parse_size, resolve_safe_subpath


def _make_img(path: Path, size: tuple[int, int] = (1920, 1080), color: str = "#112233") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(path)
    return path


def test_natural_key_orders_numerically(tmp_path: Path) -> None:
    files = [tmp_path / "slide-10.png", tmp_path / "slide-2.png", tmp_path / "slide-1.png"]
    assert [p.name for p in sorted(files, key=natural_key)] == [
        "slide-1.png",
        "slide-2.png",
        "slide-10.png",
    ]


def test_parse_size_and_canvas() -> None:
    assert parse_size("1920x1080") == (1920, 1080)
    assert parse_size("960X540") == (960, 540)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_size("invalid")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_size("0x1080")

    assert parse_canvas([1920, 1080]) == (1920, 1080)
    assert parse_canvas("1920x1080") == (1920, 1080)
    assert parse_canvas({"width": 960, "height": 540}) == (960, 540)
    assert parse_canvas(None) is None


def test_resolve_safe_subpath_blocks_traversal(tmp_path: Path) -> None:
    inside = resolve_safe_subpath(tmp_path, "layer-01.png")
    assert inside == (tmp_path / "layer-01.png").resolve()
    with pytest.raises(ValueError, match="escapes"):
        resolve_safe_subpath(tmp_path, "../secret.png")
    with pytest.raises(ValueError, match="escapes"):
        resolve_safe_subpath(tmp_path, "/etc/passwd")


def test_collect_images_from_dir_and_manifest(tmp_path: Path) -> None:
    slides_dir = tmp_path / "slides"
    _make_img(slides_dir / "slide-02.png")
    _make_img(slides_dir / "slide-01.png")
    collected = compile_mod.collect_images(slides_dir)
    assert [p.name for p in collected] == ["slide-01.png", "slide-02.png"]

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"slides": [{"image": "slides/slide-02.png"}, "slides/slide-01.png"]}),
        encoding="utf-8",
    )
    from_manifest = compile_mod.collect_images(manifest_path)
    assert [p.name for p in from_manifest] == ["slide-02.png", "slide-01.png"]


def test_normalize_image_fit_modes() -> None:
    src = Image.new("RGB", (1000, 1000), (255, 0, 0))
    for fit in ("contain", "cover", "stretch"):
        out = compile_mod.normalize_image(src, (192, 108), fit, (255, 255, 255))
        assert out.size == (192, 108)


def test_build_pdf_with_contact_sheet_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slides_dir = tmp_path / "slides"
    _make_img(slides_dir / "slide-01.png", (1920, 1080), "#102030")
    _make_img(slides_dir / "slide-02.png", (1920, 1080), "#203040")
    out_pdf = tmp_path / "final" / "deck.pdf"
    report_path = tmp_path / "qa" / "report.json"
    contact_path = tmp_path / "qa" / "contact-sheet.jpg"
    pages_dir = tmp_path / "pages"

    monkeypatch.setattr(
        "sys.argv",
        [
            "compile_slide_images_to_pdf.py",
            str(slides_dir),
            str(out_pdf),
            "--strict",
            "--min-width",
            "1280",
            "--report",
            str(report_path),
            "--contact-sheet",
            str(contact_path),
            "--columns",
            "2",
            "--pages-dir",
            str(pages_dir),
        ],
    )
    assert compile_mod.main() == 0
    assert out_pdf.is_file() and out_pdf.stat().st_size > 0
    assert contact_path.is_file() and contact_path.stat().st_size > 0
    assert (pages_dir / "slide-01.png").is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["slide_count"] == 2
    assert report["contact_sheet"] == str(contact_path)


def test_build_pdf_strict_rejects_bad_aspect_or_min_width(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slides_dir = tmp_path / "slides"
    _make_img(slides_dir / "slide-01.png", (1000, 1000))
    out_pdf = tmp_path / "deck.pdf"

    monkeypatch.setattr(
        "sys.argv",
        ["compile_slide_images_to_pdf.py", str(slides_dir), str(out_pdf), "--strict"],
    )
    assert compile_mod.main() == 1

    _make_img(slides_dir / "slide-01.png", (640, 360))
    monkeypatch.setattr(
        "sys.argv",
        [
            "compile_slide_images_to_pdf.py",
            str(slides_dir),
            str(out_pdf),
            "--strict",
            "--min-width",
            "1280",
        ],
    )
    assert compile_mod.main() == 1
