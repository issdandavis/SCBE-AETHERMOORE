"""The cross-language mountain map: verified construct grid + data-derived similarity.

Checks the map is complete and that the similarity ridge is sensible (computed from the
table, not asserted): TypeScript is JavaScript's closest face; C is closer to C++ than to
Haskell. Spot-checks a few cells that are easy to get wrong. Pure data + generator, no
toolchain needed.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "mountain_map"))

import build_mountain_map as M  # noqa: E402

DATA = M.load()
GRID = DATA["grid"]
LANGS = DATA["meta"]["languages"]
CONSTRUCTS = DATA["meta"]["constructs"]


def test_map_is_complete():
    assert len(LANGS) == 18
    assert len(CONSTRUCTS) == 32
    cells = sum(len(GRID[k]) for k in CONSTRUCTS)
    assert cells == 18 * 32  # 576, no holes
    assert all(lang in DATA["pipeline"] for lang in LANGS)


def test_known_cells_are_right():
    assert GRID["line_comment"]["haskell"]["code"].startswith("--")
    assert GRID["null_literal"]["go"]["code"] == "nil"
    assert GRID["var_const"]["javascript"]["code"].startswith("const")
    assert "for x in xs" in GRID["for_each"]["rust"]["code"]
    assert GRID["string_interp"]["c"]["code"] == "n/a"  # C has no string interpolation


def test_similarity_ridge_is_data_derived_and_sensible():
    sim = M.similarity(DATA)
    # TypeScript is JavaScript's nearest face (it is a JS superset)
    js_nearest = max((b for b in LANGS if b != "javascript"), key=lambda b: sim["javascript"][b])
    assert js_nearest == "typescript"
    assert sim["javascript"]["typescript"] > 0.8
    # C is closer to C++ than to Haskell (brace family vs an outlier)
    assert sim["c"]["cpp"] > sim["c"]["haskell"]


def test_generator_writes_all_views(tmp_path):
    M.write_table_csv(DATA, tmp_path / "t.csv")
    M.write_pipeline(DATA, tmp_path / "p.md")
    M.write_mountain(DATA, M.similarity(DATA), tmp_path / "m.dot", tmp_path / "m.md")
    for name in ("t.csv", "p.md", "m.dot", "m.md"):
        assert (tmp_path / name).stat().st_size > 0
    assert "graph mountain" in (tmp_path / "m.dot").read_text(encoding="utf-8")


def test_cross_check_against_old_table_runs():
    xc = M.cross_check(DATA)
    assert "error" not in xc
    assert xc["agree"] > 0  # the two tables agree on the simple shared cells
