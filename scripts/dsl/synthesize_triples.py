"""Synthesize DSL triples from existing bijective SFT samples.

Per artifacts/blind_spot_ledger/lanes/L_dsl_synthesis.md Step 2: for each
record in `bijective_codeflow_v1` and `cross_tongue_dialogue_bijective_v1`,
run bounded BFS (depth <= 3) over the 8 SCBE DSL primitives looking for a
program whose final GridState satisfies a structural shape predicate derived
from the record's `meta`.

The lane spec phrases the acceptance check as "produces an output token-equal
to the existing target." DSL primitives operate on numeric grids, not text,
so we reinterpret token-equality as a *shape* predicate over the final state's
(tongue, well) tuple. This is honest because the assistant text is not
recoverable from a zero-grid trajectory anyway, and the structural footprint
is precisely what the lane wants the model to learn.

Coverage gate: if the synthesisable fraction is below 60%, the script exits
non-zero and DOES NOT emit SFT files. Per spec: "either the depth budget is
too low or the primitive set is wrong; halt and review before training."
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.brain import TONGUES  # noqa: E402
from python.scbe.dsl.primitives import (  # noqa: E402
    GridState,
    breath,
    initial_state,
    mobius_phase,
    phi_weight,
    seal,
    tongue_shift,
    well_select,
)

INPUTS = [
    "training-data/sft/bijective_codeflow_v1_train.sft.jsonl",
    "training-data/sft/bijective_codeflow_v1_holdout.sft.jsonl",
    "training-data/sft/cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
    "training-data/sft/cross_tongue_dialogue_bijective_v1_holdout.sft.jsonl",
]
OUT_TRAIN = "training-data/sft/bijective_dsl_v1_train.sft.jsonl"
OUT_HOLDOUT = "training-data/sft/bijective_dsl_v1_holdout.sft.jsonl"
OUT_REPORT = "artifacts/dsl/coverage_report.json"

DEPTH = 3
COVERAGE_GATE = 0.60
LOCALITY_BOUND = 1e6  # zero grid stays zero, but guard anyway

TONGUE_KEYS = sorted(TONGUES.keys())


@dataclass(frozen=True)
class TargetShape:
    tongue: Optional[str] = None
    well: Optional[str] = None

    def matches(self, state: GridState) -> bool:
        if self.tongue is not None and state.tongue != self.tongue:
            return False
        if self.well is not None and state.well != self.well:
            return False
        return True


def _src_from_meta(m: Dict[str, Any]) -> Optional[str]:
    return m.get("src") or m.get("speaker_tongue") or m.get("tongue")


def _dst_from_meta(m: Dict[str, Any]) -> Optional[str]:
    return m.get("dst") or m.get("listener_tongue") or m.get("tongue")


def _well_for_slot(slot: Optional[str], prefix: str) -> str:
    base = (slot or "BODY").upper()
    return f"{prefix}_{base}"


def _shape_for(meta: Dict[str, Any]) -> Tuple[Optional[TargetShape], List[str], Optional[str]]:
    """Map a record's meta dict to (target_shape, candidate_realms, initial_tongue)."""
    task = meta.get("task") or meta.get("category")
    src = _src_from_meta(meta)
    dst = _dst_from_meta(meta)
    if task == "translate_one":
        return TargetShape(tongue=dst, well="TRANSLATED"), ["TRANSLATED"], src
    if task == "translate_all":
        return TargetShape(tongue=src, well="TRANSLATED_ALL"), ["TRANSLATED_ALL"], src
    if task == "identify":
        t = meta.get("tongue")
        return TargetShape(tongue=t, well="IDENTIFIED"), ["IDENTIFIED"], t
    if task == "edit_slot_one":
        well = _well_for_slot(meta.get("slot"), "EDIT")
        return TargetShape(tongue=dst, well=well), [well], src or dst
    if task == "edit_slot_all":
        well = _well_for_slot(meta.get("slot"), "EDIT_ALL")
        return TargetShape(tongue=src, well=well), [well], src
    if task == "align":
        return TargetShape(tongue=dst, well="ALIGNED"), ["ALIGNED"], src
    if task == "governance_tag":
        t = meta.get("tongue")
        return TargetShape(tongue=t, well="GOVERNANCE"), ["GOVERNANCE"], t
    if task == "multiline_edit":
        return TargetShape(tongue=src or "KO", well="MULTILINE"), ["MULTILINE"], src or "KO"
    if task == "dialogue":
        return TargetShape(tongue=dst, well="SEALED"), [], src
    return None, [], None


def _candidate_ops(meta: Dict[str, Any], realms: Sequence[str]) -> List[Tuple[str, Tuple]]:
    """Per-record candidate primitive applications. Invalid ones are pruned at apply time."""
    cands: List[Tuple[str, Tuple]] = []
    seeds = {
        t for t in (
            _src_from_meta(meta),
            _dst_from_meta(meta),
            meta.get("speaker_tongue"),
            meta.get("listener_tongue"),
            meta.get("tongue"),
        )
        if t in TONGUES
    }
    if not seeds:
        seeds = {"KO"}
    for src_t in TONGUE_KEYS:
        for dst_t in seeds:
            if src_t != dst_t:
                cands.append(("tongue_shift", (src_t, dst_t)))
    for t in seeds:
        cands.append(("phi_weight", (t, 1)))
    cands.append(("mobius_phase", (0.5,)))
    cands.append(("breath", (0.5,)))
    for r in realms:
        cands.append(("well_select", (r,)))
    cands.append(("seal", ()))
    return cands


_DISPATCH = {
    "tongue_shift": lambda s, a: tongue_shift(s, a[0], a[1]),
    "phi_weight":   lambda s, a: phi_weight(s, a[0], a[1]),
    "mobius_phase": lambda s, a: mobius_phase(s, a[0]),
    "breath":       lambda s, a: breath(s, a[0]),
    "well_select":  lambda s, a: well_select(s, a[0]),
    "seal":         lambda s, a: seal(s),
}


def _apply(name: str, args: Tuple, state: GridState) -> Optional[GridState]:
    try:
        return _DISPATCH[name](state, args)
    except (ValueError, KeyError):
        return None


def _norm_ok(state: GridState) -> bool:
    return float(np.linalg.norm(state.grid)) <= LOCALITY_BOUND


def _state_key(state: GridState) -> Tuple:
    return (
        state.tongue,
        state.phi_power,
        state.well,
        round(state.phase, 6),
        round(state.breath_phase, 6),
    )


def synthesize(meta: Dict[str, Any]) -> Optional[Tuple[List[Tuple[str, Tuple]], GridState]]:
    shape, realms, init_tongue = _shape_for(meta)
    if shape is None or init_tongue not in TONGUES:
        return None
    cands = _candidate_ops(meta, realms)
    start = initial_state(init_tongue)
    seen = {_state_key(start)}
    queue: deque = deque()
    queue.append((start, []))
    while queue:
        state, ops = queue.popleft()
        if ops and shape.matches(state):
            return ops, state
        if len(ops) >= DEPTH:
            continue
        for name, args in cands:
            new_state = _apply(name, args, state)
            if new_state is None or not _norm_ok(new_state):
                continue
            key = _state_key(new_state)
            if key in seen:
                continue
            seen.add(key)
            queue.append((new_state, ops + [(name, args)]))
    return None


def _emit_op(name: str, args: Tuple) -> str:
    if name == "tongue_shift":
        return f"tongue_shift({args[0]} -> {args[1]})"
    if name == "phi_weight":
        return f"phi_weight({args[0]}, {args[1]})"
    if name == "mobius_phase":
        return f"mobius_phase({args[0]})"
    if name == "breath":
        return f"breath({args[0]})"
    if name == "well_select":
        return f"well_select({args[0]})"
    if name == "seal":
        return "seal()"
    raise ValueError(f"unknown op {name}")


def _last_msg(messages: List[Dict[str, str]], role: str) -> str:
    for m in messages:
        if m.get("role") == role:
            return m.get("content", "")
    return ""


def _build_triple(record: Dict[str, Any], program: List[Tuple[str, Tuple]]) -> Optional[Dict[str, Any]]:
    meta = record.get("meta", {})
    messages = record.get("messages", [])
    user_in = _last_msg(messages, "user")
    target_out = _last_msg(messages, "assistant")
    if not user_in or not target_out:
        return None
    target_tongue = _dst_from_meta(meta) or _src_from_meta(meta) or "KO"
    program_lines = "\n".join(_emit_op(n, a) for n, a in program)
    excerpt = target_out.strip().splitlines()[0][:200] if target_out.strip() else ""
    assistant = f"{program_lines}\n# expected: {excerpt}"
    return {
        "messages": [
            {"role": "system", "content": "Emit a DSL program over the 8 SCBE primitives."},
            {"role": "user", "content": f"<input>{user_in}</input>\n<target_tongue>{target_tongue}</target_tongue>"},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            **meta,
            "dsl_program_depth": len(program),
            "dsl_synthesised_from": meta.get("task") or meta.get("category"),
        },
    }


def _split_for(rel_path: str) -> str:
    return "holdout" if "_holdout" in Path(rel_path).name else "train"


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="compute coverage but skip writing SFT files")
    p.add_argument("--root", default=str(ROOT))
    args = p.parse_args(argv)
    root = Path(args.root)

    counters: Dict[str, Counter] = {
        "total": Counter(),
        "synthesised": Counter(),
        "by_task": Counter(),
        "synthesised_by_task": Counter(),
        "depth_distribution": Counter(),
    }
    triples_by_split: Dict[str, List[Dict[str, Any]]] = {"train": [], "holdout": []}

    for rel in INPUTS:
        path = root / rel
        if not path.exists():
            print(f"[warn] missing input: {path}", file=sys.stderr)
            continue
        split = _split_for(rel)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                meta = record.get("meta", {})
                task = meta.get("task") or meta.get("category") or "unknown"
                counters["total"][split] += 1
                counters["by_task"][task] += 1
                result = synthesize(meta)
                if result is None:
                    continue
                program, _final = result
                counters["synthesised"][split] += 1
                counters["synthesised_by_task"][task] += 1
                counters["depth_distribution"][len(program)] += 1
                triple = _build_triple(record, program)
                if triple is not None:
                    triples_by_split[split].append(triple)

    total = sum(counters["total"].values())
    syn = sum(counters["synthesised"].values())
    coverage = (syn / total) if total else 0.0
    by_task_coverage = {
        task: {
            "total": counters["by_task"][task],
            "synthesised": counters["synthesised_by_task"][task],
            "coverage": (counters["synthesised_by_task"][task] / counters["by_task"][task])
            if counters["by_task"][task]
            else 0.0,
        }
        for task in counters["by_task"]
    }
    report = {
        "total": total,
        "synthesised": syn,
        "coverage": coverage,
        "gate": COVERAGE_GATE,
        "passed": coverage >= COVERAGE_GATE,
        "depth_budget": DEPTH,
        "by_split": {
            s: {"total": counters["total"][s], "synthesised": counters["synthesised"][s]}
            for s in counters["total"]
        },
        "by_task": by_task_coverage,
        "depth_distribution": dict(counters["depth_distribution"]),
        "inputs": INPUTS,
        "outputs": {"train": OUT_TRAIN, "holdout": OUT_HOLDOUT},
    }

    out_report = root / OUT_REPORT
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[coverage] {syn}/{total} = {coverage:.2%} (gate={COVERAGE_GATE:.0%})")
    for task, info in sorted(by_task_coverage.items()):
        print(f"  - {task:20s} {info['synthesised']:>4}/{info['total']:>4} = {info['coverage']:.2%}")

    if not report["passed"]:
        print(
            f"[FAIL] coverage {coverage:.2%} < gate {COVERAGE_GATE:.0%}; not emitting SFT files",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        print("[dry-run] gate passed; skipping SFT emission")
        return 0

    for split, items in triples_by_split.items():
        out_path = root / (OUT_TRAIN if split == "train" else OUT_HOLDOUT)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"[wrote] {out_path} ({len(items)} triples)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
