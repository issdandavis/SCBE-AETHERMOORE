from __future__ import annotations

import json

import numpy as np
import pytest

from neurogolf.arc_io import load_arc_task
from neurogolf.family_corridor import (
    ColorRemapCorridor,
    intersect_color_remap_corridors,
)
from neurogolf.solver import (
    _infer_color_remap_corridor,
    _infer_global_color_remap,
    _infer_trichromatic_component_color_mapping,
    _infer_tile_self_complement,
    _infer_upscale_corridor,
)


def test_intersect_color_remap_corridors_returns_partial_corridor():
    corridor = intersect_color_remap_corridors([{1: 3, 2: 4}, {1: 3}])

    assert corridor == ColorRemapCorridor(
        fixed_mapping={1: 3, 2: 4},
        free_sources=frozenset({0, 3, 4, 5, 6, 7, 8, 9}),
        pinned_sources=frozenset({1, 2}),
    )
    assert corridor.is_total()
    assert corridor.materialize() == {1: 3, 2: 4}
    assert corridor.materialize(identity_for_free=True) == {
        0: 0,
        1: 3,
        2: 4,
        3: 3,
        4: 4,
        5: 5,
        6: 6,
        7: 7,
        8: 8,
        9: 9,
    }


def test_intersect_color_remap_corridors_rejects_conflict():
    assert intersect_color_remap_corridors([{1: 3}, {1: 4}]) is None


def test_infer_color_remap_corridor_is_total_for_fully_pinned_task(tmp_path):
    task_path = tmp_path / "task_corridor_full.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [
                    {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
                    {"input": [[2, 1]], "output": [[4, 3]]},
                ],
                "test": [{"input": [[1, 2]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)
    corridor = _infer_color_remap_corridor(task)

    assert corridor is not None
    assert corridor.is_total()
    assert corridor.fixed_mapping == {1: 3, 2: 4}
    assert corridor.materialize() == {1: 3, 2: 4}
    assert _infer_global_color_remap(task) == {1: 3, 2: 4}


def test_trichromatic_component_color_mapping_recovers_simple_component_pairs():
    src = np.array(
        [
            [1, 1, 0, 2],
            [1, 1, 0, 2],
        ],
        dtype=np.int64,
    )
    dst = np.array(
        [
            [3, 3, 0, 4],
            [3, 3, 0, 4],
        ],
        dtype=np.int64,
    )

    mapping = _infer_trichromatic_component_color_mapping(src, dst)

    assert mapping == {1: 3, 2: 4}


def test_color_remap_corridor_can_use_trichromatic_fallback(tmp_path, monkeypatch: pytest.MonkeyPatch):
    task_path = tmp_path / "task_corridor_trichromatic.json"
    task_path.write_text(
        json.dumps(
            {
                "train": [{"input": [[1, 1, 0, 2], [1, 1, 0, 2]], "output": [[3, 3, 0, 4], [3, 3, 0, 4]]}],
                "test": [{"input": [[1, 0, 2]]}],
            }
        ),
        encoding="utf-8",
    )

    task = load_arc_task(task_path)

    monkeypatch.setattr("neurogolf.solver._infer_color_mapping", lambda _src, _dst: None)

    corridor = _infer_color_remap_corridor(task)

    assert corridor is not None
    assert corridor.fixed_mapping == {1: 3, 2: 4}
    assert _infer_global_color_remap(task) == {1: 3, 2: 4}


# ---------------------------------------------------------------------------
# UpscaleCorridor unit tests
# ---------------------------------------------------------------------------


def _make_upscale_task(tmp_path, pairs, k=2, name="upscale_task"):
    examples = []
    for inp_list, out_list in pairs:
        examples.append({"input": inp_list, "output": out_list})
    p = tmp_path / f"{name}.json"
    p.write_text(
        json.dumps({"train": examples, "test": [{"input": pairs[0][0]}]}),
        encoding="utf-8",
    )
    return load_arc_task(p)


def _upscale(grid, k):
    arr = np.array(grid)
    return np.repeat(np.repeat(arr, k, axis=0), k, axis=1).tolist()


def test_upscale_corridor_pure_upscale(tmp_path):
    """Pure pixel-repeat → is_pure_upscale() True, scale_k pinned."""
    task = _make_upscale_task(
        tmp_path,
        [
            ([[1, 2], [3, 4]], _upscale([[1, 2], [3, 4]], 2)),
            ([[2, 1], [4, 3]], _upscale([[2, 1], [4, 3]], 2)),
        ],
    )
    c = _infer_upscale_corridor(task)
    assert c is not None
    assert c.is_pure_upscale()
    assert c.scale_k == 2
    assert c.materialize_color_remap() is None


def test_upscale_corridor_with_color_remap(tmp_path):
    """Upscale + consistent recolor → corridor carries the remap."""

    def remap(grid, mapping):
        return [[mapping.get(v, v) for v in row] for row in grid]

    m = {1: 5, 2: 6, 3: 7, 4: 8}
    inp = [[1, 2], [3, 4]]
    task = _make_upscale_task(
        tmp_path,
        [(inp, remap(_upscale(inp, 2), m))],
        name="upscale_remap",
    )
    c = _infer_upscale_corridor(task)
    assert c is not None
    assert not c.is_pure_upscale()
    assert c.scale_k == 2
    mat = c.materialize_color_remap()
    assert mat is not None
    for src, dst in m.items():
        assert mat[src] == dst


def test_upscale_corridor_conflict_returns_none(tmp_path):
    """Inconsistent recolor across examples → None."""

    def remap(grid, mapping):
        return [[mapping.get(v, v) for v in row] for row in grid]

    inp = [[1, 2]]
    task = _make_upscale_task(
        tmp_path,
        [
            (inp, remap(_upscale(inp, 2), {1: 5, 2: 6})),
            (inp, remap(_upscale(inp, 2), {1: 7, 2: 6})),  # 1 maps differently
        ],
        name="upscale_conflict",
    )
    assert _infer_upscale_corridor(task) is None


def test_upscale_corridor_inconsistent_k_returns_none(tmp_path):
    """Different scale factors across examples → None."""
    inp = [[1, 2], [3, 4]]
    task = _make_upscale_task(
        tmp_path,
        [
            (inp, _upscale(inp, 2)),
            (inp, _upscale(inp, 3)),  # k=3 vs k=2
        ],
        name="upscale_inconsistent_k",
    )
    assert _infer_upscale_corridor(task) is None


def test_upscale_then_color_remap_synthesized(tmp_path):
    """End-to-end: synthesize_program produces upscale_then_color_remap solution."""
    from neurogolf.solver import synthesize_program

    def remap(grid, mapping):
        return [[mapping.get(v, v) for v in row] for row in grid]

    m = {1: 5, 2: 6, 3: 7, 4: 8}
    inp = [[1, 2], [3, 4]]
    task = _make_upscale_task(
        tmp_path,
        [
            (inp, remap(_upscale(inp, 2), m)),
            ([[2, 1], [4, 3]], remap(_upscale([[2, 1], [4, 3]], 2), m)),
        ],
        name="upscale_remap_e2e",
    )
    sol = synthesize_program(task)
    assert sol.family == "upscale_then_color_remap"
    assert sol.program.name == "upscale_then_color_remap"
    assert len(sol.program.steps) == 2
    assert sol.program.steps[0].op == "upscale"
    assert sol.program.steps[1].op == "color_remap"


# ---------------------------------------------------------------------------
# TileSelfComplement unit tests
# ---------------------------------------------------------------------------


def _complement(grid: list[list[int]], color: int) -> list[list[int]]:
    """Boolean complement: 0→color, color→0."""
    return [[0 if v != 0 else color for v in row] for row in grid]


def _tile_self_complement_output(inp: list[list[int]], color: int) -> list[list[int]]:
    """Compute expected tile_self_complement output."""
    ih = len(inp)
    iw = len(inp[0]) if ih > 0 else 0
    comp = _complement(inp, color)
    out = [[0] * (iw * iw) for _ in range(ih * ih)]
    for r in range(ih):
        for c in range(iw):
            if inp[r][c] != 0:
                for br in range(ih):
                    for bc in range(iw):
                        out[r * ih + br][c * iw + bc] = comp[br][bc]
    return out


def _make_tile_self_complement_task(tmp_path, pairs, name="tile_self_complement_task"):
    examples = [{"input": inp, "output": out} for inp, out in pairs]
    p = tmp_path / f"{name}.json"
    p.write_text(
        json.dumps({"train": examples, "test": [{"input": pairs[0][0]}]}),
        encoding="utf-8",
    )
    return load_arc_task(p)


def test_tile_self_complement_basic(tmp_path):
    """Single training example with 2×2 binary input → correct corridor recognition."""
    inp = [[1, 0], [0, 1]]
    expected = _tile_self_complement_output(inp, color=1)
    task = _make_tile_self_complement_task(tmp_path, [(inp, expected)])
    assert _infer_tile_self_complement(task)


def test_tile_self_complement_two_examples(tmp_path):
    """Two different binary inputs both obeying the complement rule."""
    inp1 = [[3, 0, 3], [0, 3, 0], [3, 0, 3]]
    inp2 = [[0, 3, 0], [3, 0, 3], [0, 3, 0]]
    task = _make_tile_self_complement_task(
        tmp_path,
        [
            (inp1, _tile_self_complement_output(inp1, color=3)),
            (inp2, _tile_self_complement_output(inp2, color=3)),
        ],
        name="tsc_two",
    )
    assert _infer_tile_self_complement(task)


def test_tile_self_complement_wrong_output_returns_false(tmp_path):
    """If output is plain tile_self (not complement), should return False."""
    inp = [[1, 0], [0, 1]]
    # tile_self output (stamp self, not complement)
    ih, iw = len(inp), len(inp[0])
    tile_self_out = [[0] * (iw * iw) for _ in range(ih * ih)]
    for r in range(ih):
        for c in range(iw):
            if inp[r][c] != 0:
                for br in range(ih):
                    for bc in range(iw):
                        tile_self_out[r * ih + br][c * iw + bc] = inp[br][bc]
    task = _make_tile_self_complement_task(tmp_path, [(inp, tile_self_out)], name="tsc_wrong")
    assert not _infer_tile_self_complement(task)


def test_tile_self_complement_synthesized(tmp_path):
    """End-to-end: synthesize_program finds tile_self_complement family."""
    from neurogolf.solver import synthesize_program

    inp1 = [[3, 0, 3], [3, 3, 0], [0, 3, 0]]
    inp2 = [[0, 3, 0], [3, 0, 3], [0, 3, 3]]
    task = _make_tile_self_complement_task(
        tmp_path,
        [
            (inp1, _tile_self_complement_output(inp1, color=3)),
            (inp2, _tile_self_complement_output(inp2, color=3)),
        ],
        name="tsc_e2e",
    )
    sol = synthesize_program(task)
    assert sol is not None
    assert sol.family == "tile_self_complement"
    assert sol.program.name == "tile_self_complement"
    assert len(sol.program.steps) == 1
    assert sol.program.steps[0].op == "tile_self_complement"
