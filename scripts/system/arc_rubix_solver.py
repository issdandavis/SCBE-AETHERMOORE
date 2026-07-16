#!/usr/bin/env python3
"""ARC Rubix solver: reusable ARC grid-rule candidate generator.

This is the bridge from NeuroGolf/Rubix identity work into ARC-AGI JSON output.
It learns exact rule templates from train pairs, applies matching templates to test
inputs, and writes exactly two attempts per test item.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

Grid = list[list[int]]
ROOT = Path(r"C:\Users\issda\kaggle\arc_agi2_2026")
DEFAULT_COMP = ROOT / "competition"


def shape(g: Grid) -> tuple[int, int]:
    return (len(g), len(g[0]) if g else 0)


def clone(g: Grid) -> Grid:
    return [list(r) for r in g]


def zeros(h: int, w: int) -> Grid:
    return [[0 for _ in range(w)] for _ in range(h)]


def const_grid(h: int, w: int, v: int) -> Grid:
    return [[int(v) for _ in range(w)] for _ in range(h)]


def flatten(g: Grid) -> list[int]:
    return [v for row in g for v in row]


def bg_color(g: Grid) -> int:
    vals = flatten(g)
    return Counter(vals).most_common(1)[0][0] if vals else 0


def most_common_output_color(pairs: Sequence[dict]) -> int:
    vals: list[int] = []
    for p in pairs:
        vals.extend(flatten(p["output"]))
    return Counter(vals).most_common(1)[0][0] if vals else 0


def rotate90(g: Grid) -> Grid:
    return [list(row) for row in zip(*g[::-1])]


def rotate180(g: Grid) -> Grid:
    return [list(reversed(row)) for row in reversed(g)]


def rotate270(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)][::-1]


def flip_h(g: Grid) -> Grid:
    return [list(reversed(row)) for row in g]


def flip_v(g: Grid) -> Grid:
    return [list(row) for row in reversed(g)]


def transpose(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)] if g else []


def crop_bbox(g: Grid, background: int | None = None) -> Grid:
    if background is None:
        background = bg_color(g)
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != background]
    if not cells:
        return clone(g)
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    return [row[c0 : c1 + 1] for row in g[r0 : r1 + 1]]


def crop_nonzero(g: Grid) -> Grid:
    return crop_bbox(g, 0)


def scale_cells(g: Grid, sy: int, sx: int) -> Grid:
    out: Grid = []
    for row in g:
        wide: list[int] = []
        for v in row:
            wide.extend([v] * sx)
        for _ in range(sy):
            out.append(list(wide))
    return out


def tile_grid(g: Grid, ty: int, tx: int) -> Grid:
    return [list(row) * tx for _ in range(ty) for row in g]


def pad_to_shape(g: Grid, h: int, w: int, fill: int = 0) -> Grid:
    gh, gw = shape(g)
    out = const_grid(h, w, fill)
    for r in range(min(h, gh)):
        for c in range(min(w, gw)):
            out[r][c] = g[r][c]
    return out


def infer_color_map(srcs: Sequence[Grid], outs: Sequence[Grid]) -> dict[int, int] | None:
    mapping: dict[int, int] = {}
    for src, out in zip(srcs, outs):
        if shape(src) != shape(out):
            return None
        for r in range(len(src)):
            for c in range(len(src[0])):
                a, b = src[r][c], out[r][c]
                if a in mapping and mapping[a] != b:
                    return None
                mapping[a] = b
    return mapping


def apply_color_map(g: Grid, mapping: dict[int, int]) -> Grid:
    return [[mapping.get(v, v) for v in row] for row in g]


def infer_constant_shape(pairs: Sequence[dict]) -> tuple[int, int] | None:
    if not pairs:
        return None
    counts = Counter(shape(p["output"]) for p in pairs)
    return counts.most_common(1)[0][0]


BASE_TRANSFORMS: list[tuple[str, Callable[[Grid], Grid]]] = [
    ("identity", clone),
    ("rot90", rotate90),
    ("rot180", rotate180),
    ("rot270", rotate270),
    ("flip_h", flip_h),
    ("flip_v", flip_v),
    ("transpose", transpose),
    ("crop_nonzero", crop_nonzero),
    ("crop_bbox_bg", lambda g: crop_bbox(g, bg_color(g))),
]


@dataclass
class Rule:
    name: str
    apply: Callable[[Grid], Grid]
    train_hits: int


def learn_rules(task: dict) -> list[Rule]:
    pairs = task.get("train", [])
    if not pairs:
        return []
    inputs = [p["input"] for p in pairs]
    outputs = [p["output"] for p in pairs]
    rules: list[Rule] = []

    for name, fn in BASE_TRANSFORMS:
        try:
            preds = [fn(g) for g in inputs]
        except Exception:
            continue
        if preds == outputs:
            rules.append(Rule(name, fn, len(pairs)))
        cmap = infer_color_map(preds, outputs)
        if cmap is not None:
            rules.append(Rule(f"{name}+color_map", lambda g, fn=fn, cmap=cmap: apply_color_map(fn(g), cmap), len(pairs)))

    scale_candidates = set()
    tile_candidates = set()
    for p in pairs:
        ih, iw = shape(p["input"])
        oh, ow = shape(p["output"])
        if ih and iw and oh % ih == 0 and ow % iw == 0:
            scale_candidates.add((oh // ih, ow // iw))
            tile_candidates.add((oh // ih, ow // iw))
    for sy, sx in sorted(scale_candidates):
        if (sy, sx) != (1, 1) and sy <= 10 and sx <= 10:
            preds = [scale_cells(g, sy, sx) for g in inputs]
            if preds == outputs:
                rules.append(Rule(f"scale_cells_{sy}x{sx}", lambda g, sy=sy, sx=sx: scale_cells(g, sy, sx), len(pairs)))
            cmap = infer_color_map(preds, outputs)
            if cmap is not None:
                rules.append(Rule(f"scale_cells_{sy}x{sx}+color_map", lambda g, sy=sy, sx=sx, cmap=cmap: apply_color_map(scale_cells(g, sy, sx), cmap), len(pairs)))
    for ty, tx in sorted(tile_candidates):
        if (ty, tx) != (1, 1) and ty <= 10 and tx <= 10:
            preds = [tile_grid(g, ty, tx) for g in inputs]
            if preds == outputs:
                rules.append(Rule(f"tile_{ty}x{tx}", lambda g, ty=ty, tx=tx: tile_grid(g, ty, tx), len(pairs)))
            cmap = infer_color_map(preds, outputs)
            if cmap is not None:
                rules.append(Rule(f"tile_{ty}x{tx}+color_map", lambda g, ty=ty, tx=tx, cmap=cmap: apply_color_map(tile_grid(g, ty, tx), cmap), len(pairs)))

    out_shape = infer_constant_shape(pairs)
    if out_shape:
        h, w = out_shape
        common = most_common_output_color(pairs)
        if all(p["output"] == const_grid(h, w, common) for p in pairs):
            rules.append(Rule(f"constant_{h}x{w}_{common}", lambda _g, h=h, w=w, common=common: const_grid(h, w, common), len(pairs)))
        if all(p["output"] == zeros(h, w) for p in pairs):
            rules.append(Rule(f"zeros_{h}x{w}", lambda _g, h=h, w=w: zeros(h, w), len(pairs)))

    # Dedupe by observed train outputs and rule name order.
    dedup: list[Rule] = []
    seen = set()
    for rule in rules:
        key = tuple(json.dumps(rule.apply(g), separators=(",", ":")) for g in inputs)
        if key not in seen:
            seen.add(key)
            dedup.append(rule)
    return dedup


def fallback_candidates(task: dict, test_input: Grid) -> list[tuple[str, Grid]]:
    pairs = task.get("train", [])
    out_shape = infer_constant_shape(pairs)
    candidates: list[tuple[str, Grid]] = [("identity_fallback", clone(test_input)), ("zero_like_fallback", zeros(*shape(test_input)))]
    if out_shape:
        h, w = out_shape
        candidates.append(("constant_output_common_fallback", const_grid(h, w, most_common_output_color(pairs))))
        candidates.append(("zero_output_shape_fallback", zeros(h, w)))
        candidates.append(("input_padded_to_output_shape_fallback", pad_to_shape(test_input, h, w, bg_color(test_input))))
    candidates.append(("crop_nonzero_fallback", crop_nonzero(test_input)))
    return candidates


def choose_two(task: dict, test_input: Grid) -> tuple[list[dict], list[str]]:
    rules = learn_rules(task)
    candidates: list[tuple[str, Grid]] = []
    for rule in rules:
        try:
            candidates.append((rule.name, rule.apply(test_input)))
        except Exception:
            continue
    candidates.extend(fallback_candidates(task, test_input))

    attempts: list[Grid] = []
    names: list[str] = []
    seen = set()
    for name, grid in candidates:
        h, w = shape(grid)
        if h <= 0 or w <= 0 or h > 30 or w > 30:
            continue
        key = json.dumps(grid, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        attempts.append(grid)
        names.append(name)
        if len(attempts) == 2:
            break
    while len(attempts) < 2:
        attempts.append(zeros(*shape(test_input)))
        names.append("forced_zero_fallback")
    return [{"attempt_1": attempts[0], "attempt_2": attempts[1]}], names[:2]


def solve(challenges: dict) -> tuple[dict, dict]:
    submission: dict = {}
    report: dict = {"tasks": {}, "summary": Counter()}
    for task_id, task in challenges.items():
        task_outputs = []
        task_names = []
        learned = [r.name for r in learn_rules(task)]
        for test_case in task.get("test", []):
            attempt_list, names = choose_two(task, test_case["input"])
            task_outputs.extend(attempt_list)
            task_names.append(names)
            for n in names:
                report["summary"][n] += 1
        submission[task_id] = task_outputs
        report["tasks"][task_id] = {"learned_rules": learned, "selected_attempts": task_names}
    report["summary"] = dict(report["summary"].most_common())
    return submission, report


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate ARC-AGI-2 submission.json from Rubix rule templates.")
    ap.add_argument("--challenges", default=str(DEFAULT_COMP / "arc-agi_test_challenges.json"))
    ap.add_argument("--out", default=str(ROOT / "submission.json"))
    ap.add_argument("--report", default=str(ROOT / "arc_rubix_report.json"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    challenges = json.loads(Path(args.challenges).read_text(encoding="utf-8"))
    submission, report = solve(challenges)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(submission, separators=(",", ":")), encoding="utf-8")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    payload = {
        "ok": True,
        "tasks": len(submission),
        "outputs": sum(len(v) for v in submission.values()),
        "out": args.out,
        "report": args.report,
        "top_rules": list(report["summary"].items())[:12],
    }
    print(json.dumps(payload, indent=2) if args.json else f"Wrote {args.out} ({payload['outputs']} outputs)")


if __name__ == "__main__":
    main()
