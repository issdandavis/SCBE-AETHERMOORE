"""Emit Brick 1 replay boost file from the Brick 0 training slice.

Reads `data/tongue_drill/drill_langues_full.jsonl` and writes
`data/tongue_drill/brick1_boost.jsonl` following the share/factor spec in
docs/BRICK1_CONTINUAL_LEARNING_PLAN.md §3:

  - causal_transform stage, all tongues, sampled 3x
  - route_governance stage, all 3 route maps, sampled 4x
  - KO anchor/witness pairs from cross_braid_code
  - AV filler (rows tagged AV that are not already in a benchmarked stage)

Stage membership follows the same predicates used in
`scripts/benchmark/polly_structural_benchmark.py::build_structural_benchmark_cases`
so the boost is coverage-aligned with what Brick 0's validator actually scores.

Deterministic: seeded from Brick 1 run seed 0xB1.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "data" / "tongue_drill" / "drill_langues_full.jsonl"
OUT = REPO_ROOT / "data" / "tongue_drill" / "brick1_boost.jsonl"
MANIFEST = REPO_ROOT / "data" / "tongue_drill" / "brick1_boost.manifest.json"
SEED = 0xB1

CAUSAL_FACTOR = 3
ROUTE_FACTOR = 4
KO_FACTOR = 1
AV_FACTOR = 1


def stage_of(row: dict) -> str | None:
    m = row.get("map")
    k = row.get("kind")
    txt = row.get("text", "") or ""

    if m == "transport_atomic" and k in {"reaction_predict", "reaction_stability"}:
        return "causal_transform"
    if m == "convergence_action" and k == "packet" and "transport=" in txt:
        return "causal_transform"
    if m == "cartography_state" and k == "route" and "gear=" in txt:
        return "route_governance"
    if m == "cross_braid_code" and k in {"anchor_code", "witness_code"}:
        return "braid_helix"
    if m == "atomic_semantic" and k == "state" and "trust=" in txt:
        return "atom_seed"
    return None


def main() -> int:
    rows = [json.loads(line) for line in SRC.read_text(encoding="utf-8").splitlines() if line.strip()]

    pools: dict[str, list[dict]] = {
        "causal_transform": [],
        "route_governance": [],
        "braid_KO": [],
        "filler_AV": [],
    }

    covered_stages = {"causal_transform", "route_governance", "braid_helix", "atom_seed"}

    for r in rows:
        st = stage_of(r)
        if st == "causal_transform":
            pools["causal_transform"].append(r)
        elif st == "route_governance":
            pools["route_governance"].append(r)
        if st == "braid_helix" and r.get("tongue") == "KO":
            pools["braid_KO"].append(r)
        if r.get("tongue") == "AV" and st not in covered_stages:
            pools["filler_AV"].append(r)

    rng = random.Random(SEED)

    def repeat_shuffle(pool: list[dict], factor: int, tag: str) -> list[dict]:
        out = []
        for pass_i in range(factor):
            shuffled = list(pool)
            rng.shuffle(shuffled)
            for r in shuffled:
                enriched = dict(r)
                enriched["_brick1_tag"] = tag
                enriched["_brick1_pass"] = pass_i
                out.append(enriched)
        return out

    emitted: list[dict] = []
    emitted.extend(repeat_shuffle(pools["causal_transform"], CAUSAL_FACTOR, "causal_transform"))
    emitted.extend(repeat_shuffle(pools["route_governance"], ROUTE_FACTOR, "route_governance"))
    emitted.extend(repeat_shuffle(pools["braid_KO"], KO_FACTOR, "braid_KO"))
    emitted.extend(repeat_shuffle(pools["filler_AV"], AV_FACTOR, "filler_AV"))

    rng.shuffle(emitted)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in emitted:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tag_counts = Counter(r["_brick1_tag"] for r in emitted)
    total = len(emitted)
    shares = {tag: round(count / total, 4) for tag, count in tag_counts.items()}

    manifest = {
        "source": str(SRC.relative_to(REPO_ROOT)),
        "output": str(OUT.relative_to(REPO_ROOT)),
        "seed": SEED,
        "eligible_pool_sizes": {k: len(v) for k, v in pools.items()},
        "oversample_factors": {
            "causal_transform": CAUSAL_FACTOR,
            "route_governance": ROUTE_FACTOR,
            "braid_KO": KO_FACTOR,
            "filler_AV": AV_FACTOR,
        },
        "emitted_counts": dict(tag_counts),
        "emitted_shares": shares,
        "total_rows": total,
        "planned_shares": {
            "causal_transform": 0.20,
            "route_governance": 0.15,
            "braid_KO": 0.10,
            "filler_AV": 0.05,
        },
        "note": (
            "Planned shares from BRICK1_CONTINUAL_LEARNING_PLAN.md sum to 50% and "
            "describe the share of causal/route/KO/AV in the TOTAL training mix (60% "
            "replay + 40% boost). Emitted shares describe the composition of the "
            "boost file itself; the remaining balance comes from the 60% Brick 0 "
            "replay that the trainer interleaves at 1:3."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[brick1_boost] emitted {total} rows -> {OUT}")
    for tag, count in tag_counts.most_common():
        print(f"  {tag:20s} {count:5d}  ({shares[tag]*100:5.2f}%)")
    print(f"manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
