from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

import verify_deck_outputs as verify_mod


def _make_dummy_pptx(path: Path, slides_texts: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        for idx, texts in enumerate(slides_texts, start=1):
            runs = "".join(f"<a:t>{t}</a:t>" for t in texts)
            xml = (
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f"<p:cSld><p:spTree>{runs}<p:pic/></p:spTree></p:cSld></p:sld>"
            )
            zf.writestr(f"ppt/slides/slide{idx}.xml", xml)
    return path


def test_verify_deck_outputs_all_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir()
    Image.new("RGB", (1920, 1080), "#000000").save(slides_dir / "slide-01.png")

    layers_root = tmp_path / "visual-layers"
    page_dir = layers_root / "slide-01"
    page_dir.mkdir(parents=True)
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(page_dir / "card.png")
    (page_dir / "manifest.json").write_text(
        json.dumps({"canvas": [1920, 1080], "assets": [{"file": "card.png", "position": [0, 0, 400, 300]}]}),
        encoding="utf-8",
    )

    text_json = tmp_path / "text-layer.json"
    text_json.write_text(
        json.dumps(
            {
                "canvas": [1920, 1080],
                "slides": [
                    {
                        "slide": 1,
                        "texts": [
                            {"name": "title", "text": "Hello World", "x": 120, "y": 100, "w": 600, "h": 80}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    pptx_path = _make_dummy_pptx(tmp_path / "deck.pptx", [["Hello World"]])
    report_path = tmp_path / "verify-report.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_deck_outputs.py",
            "--slides-dir",
            str(slides_dir),
            "--text-json",
            str(text_json),
            "--layers-root",
            str(layers_root),
            "--disallow-text-fill",
            "--pptx",
            str(pptx_path),
            "--require-editable-text",
            "--expected-slides",
            "1",
            "--report",
            str(report_path),
        ],
    )
    assert verify_mod.main() == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["pptx"]["slides"][0]["text_run_count"] == 1


def test_verify_detects_missing_editable_text_and_text_fill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text_json = tmp_path / "text-layer.json"
    text_json.write_text(
        json.dumps(
            {
                "slides": [
                    {
                        "slide": 1,
                        "texts": [
                            {
                                "name": "patched",
                                "text": "Bad box",
                                "x": 10,
                                "y": 10,
                                "w": 100,
                                "h": 40,
                                "fill": "#FF0000",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pptx_path = _make_dummy_pptx(tmp_path / "flat.pptx", [[]])

    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_deck_outputs.py",
            "--text-json",
            str(text_json),
            "--disallow-text-fill",
            "--pptx",
            str(pptx_path),
            "--require-editable-text",
        ],
    )
    assert verify_mod.main() == 1
