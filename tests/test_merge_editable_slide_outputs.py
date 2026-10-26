from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

import merge_editable_slide_outputs as merge_mod


def _create_subagent_slide(
    root: Path,
    folder_name: str,
    slide_no: int,
    *,
    background: str | None = None,
    canvas: list[int] | None = None,
    route: str | None = None,
    asset_file: str = "bg.png",
    create_asset: bool = True,
) -> Path:
    slide_dir = root / folder_name
    layer_dir = slide_dir / "visual-layers" / f"slide-{slide_no:02d}"
    layer_dir.mkdir(parents=True, exist_ok=True)
    if create_asset and not asset_file.startswith(".."):
        img_path = layer_dir / asset_file
        img_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (64, 36), (0, 0, 0, 0)).save(img_path)

    manifest: dict = {"assets": [{"file": asset_file, "position": [0, 0, 1920, 1080]}]}
    if canvas:
        manifest["canvas"] = canvas
    (layer_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    text_data: dict = {
        "slide": slide_no,
        "texts": [{"name": "title", "text": f"Slide {slide_no}", "x": 100, "y": 80, "w": 600, "h": 60}],
    }
    if background:
        text_data["background"] = background
    if canvas:
        text_data["canvas"] = canvas
    if route:
        text_data["route"] = route
    (slide_dir / "text-layer.json").write_text(json.dumps(text_data), encoding="utf-8")
    return slide_dir


def test_merge_preserves_per_slide_metadata_and_validates_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subagents = tmp_path / "subagents"
    _create_subagent_slide(
        subagents,
        "slide-01",
        1,
        background="#000000",
        canvas=[1920, 1080],
        route="component-layer",
    )
    _create_subagent_slide(
        subagents,
        "slide-02",
        2,
        background="#FFFFFF",
        canvas=[1920, 1080],
        route="hybrid",
    )

    out_layers = tmp_path / "visual-layers"
    out_text = tmp_path / "text-layer.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "merge_editable_slide_outputs.py",
            str(subagents),
            "--out-layers-root",
            str(out_layers),
            "--out-text-json",
            str(out_text),
            "--canvas",
            "1920x1080",
            "--force",
        ],
    )
    assert merge_mod.main() == 0
    merged = json.loads(out_text.read_text(encoding="utf-8"))
    assert merged["canvas"] == [1920, 1080]
    assert len(merged["slides"]) == 2
    assert merged["slides"][0]["background"] == "#000000"
    assert merged["slides"][0]["canvas"] == [1920, 1080]
    assert merged["slides"][0]["route"] == "component-layer"
    assert merged["slides"][1]["route"] == "hybrid"
    assert (out_layers / "slide-01" / "bg.png").is_file()


def test_merge_rejects_duplicate_slide_numbers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subagents = tmp_path / "subagents"
    _create_subagent_slide(subagents, "slide-01-first", 1)
    _create_subagent_slide(subagents, "slide-01-second", 1)

    monkeypatch.setattr(
        "sys.argv",
        [
            "merge_editable_slide_outputs.py",
            str(subagents),
            "--out-layers-root",
            str(tmp_path / "layers"),
            "--out-text-json",
            str(tmp_path / "text.json"),
            "--force",
        ],
    )
    assert merge_mod.main() == 1


def test_merge_rejects_missing_or_unsafe_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subagents = tmp_path / "subagents"
    _create_subagent_slide(subagents, "slide-01", 1, asset_file="../escape.png", create_asset=False)

    monkeypatch.setattr(
        "sys.argv",
        [
            "merge_editable_slide_outputs.py",
            str(subagents),
            "--out-layers-root",
            str(tmp_path / "layers"),
            "--out-text-json",
            str(tmp_path / "text.json"),
        ],
    )
    assert merge_mod.main() == 1
