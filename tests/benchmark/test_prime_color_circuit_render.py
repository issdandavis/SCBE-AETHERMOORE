from pathlib import Path

from scripts.research.prime_color_circuit_render import (
    build_panels,
    color_palette,
    render_svg,
    trim_to_circuits,
)


def test_color_palette_has_stable_hex_colors() -> None:
    palette = color_palette()

    assert len(palette) == 26
    assert all(color.startswith("#") and len(color) == 7 for color in palette)
    assert len(set(palette)) == 26


def test_trim_to_circuits_uses_676_symbol_blocks() -> None:
    symbols = list(range(2000))

    assert len(trim_to_circuits(symbols, 2)) == 1352


def test_render_svg_writes_rects(tmp_path: Path) -> None:
    path = tmp_path / "panel.svg"

    render_svg([0, 1, 2, 3], "demo", path, cell_size=4, columns=2)

    text = path.read_text(encoding="utf-8")
    assert "<svg" in text
    assert text.count("<rect") >= 5


def test_build_panels_writes_expected_files(tmp_path: Path) -> None:
    report = build_panels(
        limit=20_000,
        max_primes=2_000,
        circuits=1,
        out_dir=tmp_path,
        encodings=("value_mod26",),
    )

    panels = report["panels"]
    assert len(panels) == 2
    assert (tmp_path / panels[0]["svg_path"]).exists()
