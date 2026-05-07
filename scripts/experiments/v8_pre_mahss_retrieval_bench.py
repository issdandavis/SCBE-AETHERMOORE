"""v8-pre Phase 1 bench: does role-pinned HRR retrieve v6g failure markers?

Runs the 10 raw-failing prompts from the v6g gate through two conditions:

  Condition A (pinned roles): role vectors are deterministic random vectors
    keyed by semantic role name (TONGUE, LANG, SLOT, ...). For each prompt,
    we build a memory with the prompt's required (role, filler) bindings
    plus all distractors registered. Query each role -> rank against the
    role's filler dictionary -> top-1 retrieval.

  Condition B (hash-control): same memory layout, but role vectors are
    drawn from a content-free namespace (a different SHA-256 prefix). This
    is the control the MAHSS spec already flagged: hash-derived random
    role vectors carry no mechanism affinity. Retrieval still works
    mechanically because the bind/unbind operation is symmetric in role
    vector identity, so we expect Condition B to ALSO succeed -- making
    the falsifiable claim sharper: if A and B give equivalent retrieval
    accuracy, the spec's open-issue diagnosis was about routing, not
    retrieval. Phase 1 then confirms HRR retrieval is the easy part;
    Phase 2 has to prove the markers, once retrieved, actually move the
    raw pass rate.

Falsifiable predictions before running:
- Condition A top-1 >= 80%
- Condition B top-1 >= 80% (HRR retrieval is content-agnostic to role names)
- Per-role accuracy is uniform across {TONGUE, LANG, SLOT, METRIC, KEYWORD,
  IDENT, EXPR, LITERAL}; if any role craters, that's the substrate weakness.

Output: artifacts/mahss_v8_pre/phase1_retrieval_bench.json with full receipt
plus per-prompt breakdown and a Wilson 95% CI on overall pass rate."""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from python.scbe.mahss import circular_convolution, circular_correlation, l2_normalize, role_vector
from python.scbe.mahss_role_pinned_memory import (  # noqa: E402
    V6G_DISTRACTORS,
    V6G_RAW_FAILURE_CORPUS,
    RolePinnedMemory,
    build_per_prompt_memory,
)


DIM = 4096


def wilson_ci(n_pass: int, n_total: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% confidence interval for a binomial proportion."""

    if n_total == 0:
        return (0.0, 1.0)
    p = n_pass / n_total
    denom = 1.0 + (z * z) / n_total
    centre = (p + (z * z) / (2.0 * n_total)) / denom
    halfwidth = (z * math.sqrt((p * (1.0 - p) / n_total) + (z * z) / (4.0 * n_total * n_total))) / denom
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


# ----------------------------------------------------------------------
# Hash-control: memory whose role vectors come from a different namespace
# ----------------------------------------------------------------------

class HashControlMemory(RolePinnedMemory):
    """Same memory, but role vectors drawn from a deliberately different
    namespace. Used to verify that retrieval depends on the namespace
    consistency between bind and query, not on the namespace's name."""

    def role_vector_for(self, role: str) -> np.ndarray:
        if role not in self._role_vecs:
            self._role_vecs[role] = role_vector(f"hash-control-role::{role}", self.dim)
        return self._role_vecs[role]

    def register_filler(self, role: str, filler: str) -> np.ndarray:
        bucket = self._filler_vecs.setdefault(role, {})
        if filler not in bucket:
            bucket[filler] = role_vector(f"hash-control-filler::{role}::{filler}", self.dim)
        return bucket[filler]


def build_hash_control_memory(
    pairs,
    *,
    dim: int = DIM,
    distractors: dict | None = None,
) -> HashControlMemory:
    mem = HashControlMemory(dim=dim)
    if distractors:
        for role, options in distractors.items():
            mem.register_distractors(role, options)
    for role, filler in pairs:
        mem.bind(role, filler)
    return mem


# ----------------------------------------------------------------------
# Bench
# ----------------------------------------------------------------------


def evaluate_condition(
    label: str,
    builder,
    *,
    dim: int = DIM,
) -> dict:
    """Run one condition over the v6g failure corpus.

    Two scoring regimes are reported:

    - top-1: standard retrieval -- did the unbound peak match the expected
      filler? Fair when each role has ONE binding per memory.

    - set-retrieval: when a role has N bindings in this memory, take the
      top-N retrieved fillers and check whether the expected filler is
      in that set. This is the fair regime when prompts legitimately bind
      multiple fillers under one role (e.g., multi_lens_consistency
      needs three TONGUE bindings).

    Both numbers are reported so the substrate can be judged honestly."""

    by_prompt = []
    by_role: dict[str, dict[str, int]] = {}
    overall_top1 = 0
    overall_setretrieval = 0
    overall_total = 0

    for prompt_id, pairs in V6G_RAW_FAILURE_CORPUS:
        mem = builder(pairs, dim=dim, distractors=V6G_DISTRACTORS)
        # Count bindings per role for set-retrieval scoring
        role_load: dict[str, int] = {}
        for r, _ in pairs:
            role_load[r] = role_load.get(r, 0) + 1

        prompt_results = []
        prompt_top1 = 0
        prompt_setretrieval = 0
        for role, expected in pairs:
            n_bindings = role_load[role]
            ranks = mem.query(role, top_k=max(5, n_bindings + 2))
            top1_correct = bool(ranks) and ranks[0][0] == expected
            top_n_set = {name for name, _ in ranks[:n_bindings]}
            set_correct = expected in top_n_set
            prompt_results.append(
                {
                    "role": role,
                    "expected": expected,
                    "retrieved_top1": ranks[0][0] if ranks else "",
                    "score_top1": round(ranks[0][1], 6) if ranks else 0.0,
                    "n_bindings_under_role": n_bindings,
                    "top1_correct": top1_correct,
                    "setretrieval_correct": set_correct,
                    "ranks": [(name, round(s, 6)) for name, s in ranks[:5]],
                }
            )
            overall_total += 1
            if top1_correct:
                overall_top1 += 1
                prompt_top1 += 1
            if set_correct:
                overall_setretrieval += 1
                prompt_setretrieval += 1
            by_role.setdefault(role, {"top1": 0, "setretrieval": 0, "total": 0})
            by_role[role]["total"] += 1
            by_role[role]["top1"] += int(top1_correct)
            by_role[role]["setretrieval"] += int(set_correct)
        by_prompt.append(
            {
                "prompt_id": prompt_id,
                "n_pairs": len(pairs),
                "n_top1_correct": prompt_top1,
                "n_setretrieval_correct": prompt_setretrieval,
                "all_top1_correct": prompt_top1 == len(pairs),
                "all_setretrieval_correct": prompt_setretrieval == len(pairs),
                "memory_load": mem.num_bindings,
                "crosstalk_floor": round(mem.crosstalk_floor(), 6),
                "results": prompt_results,
            }
        )

    top1_ci = wilson_ci(overall_top1, overall_total)
    set_ci = wilson_ci(overall_setretrieval, overall_total)
    return {
        "condition": label,
        "dim": dim,
        "n_pairs_total": overall_total,
        "top1": {
            "n_correct": overall_top1,
            "accuracy": overall_top1 / overall_total if overall_total else 0.0,
            "wilson_95_ci": [round(top1_ci[0], 6), round(top1_ci[1], 6)],
        },
        "setretrieval": {
            "n_correct": overall_setretrieval,
            "accuracy": overall_setretrieval / overall_total if overall_total else 0.0,
            "wilson_95_ci": [round(set_ci[0], 6), round(set_ci[1], 6)],
        },
        "by_role": {
            role: {
                "total": data["total"],
                "top1": data["top1"],
                "top1_accuracy": data["top1"] / data["total"] if data["total"] else 0.0,
                "setretrieval": data["setretrieval"],
                "setretrieval_accuracy": data["setretrieval"] / data["total"] if data["total"] else 0.0,
            }
            for role, data in sorted(by_role.items())
        },
        "by_prompt": by_prompt,
    }


def random_baseline_accuracy() -> dict:
    """Expected top-1 accuracy under uniform random retrieval per role.

    For each (role, expected) pair in the corpus, random top-1 = 1 / |dictionary|.
    Average across the corpus to compare with measured top-1."""

    pair_random = []
    for _prompt_id, pairs in V6G_RAW_FAILURE_CORPUS:
        for role, _ in pairs:
            n_candidates = len(V6G_DISTRACTORS[role])
            pair_random.append(1.0 / n_candidates)
    return {
        "expected_random_top1": sum(pair_random) / len(pair_random),
        "n_pairs": len(pair_random),
    }


# ----------------------------------------------------------------------
# Cross-condition consistency check
# ----------------------------------------------------------------------


def role_vector_namespace_independence_probe() -> dict:
    """Verify the spec's claim that role-vector namespace doesn't affect
    HRR retrieval mechanics: bind+unbind in namespace X recovers filler;
    bind in X but unbind in namespace Y returns garbage.

    This pins what Phase 1 is and is not testing."""

    mem = RolePinnedMemory(dim=DIM)
    mem.bind("TONGUE", "umbroth")
    role_x = mem.role_vector_for("TONGUE")
    role_y = role_vector("hash-control-role::TONGUE", DIM)
    bound = mem.memory
    correct_unbind = circular_correlation(role_x, bound)
    cross_unbind = circular_correlation(role_y, bound)
    expected = role_vector(f"filler::TONGUE::umbroth", DIM)
    correct_cos = float(np.dot(l2_normalize(correct_unbind), l2_normalize(expected)))
    cross_cos = float(np.dot(l2_normalize(cross_unbind), l2_normalize(expected)))
    return {
        "correct_namespace_cos": round(correct_cos, 6),
        "cross_namespace_cos": round(cross_cos, 6),
        "snr_ratio": round(correct_cos / max(abs(cross_cos), 1e-9), 3),
    }


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------


def main() -> int:
    pinned = evaluate_condition("pinned_roles", build_per_prompt_memory, dim=DIM)
    hash_control = evaluate_condition("hash_control", build_hash_control_memory, dim=DIM)
    namespace_probe = role_vector_namespace_independence_probe()
    random_baseline = random_baseline_accuracy()

    pinned_top1 = pinned["top1"]["accuracy"]
    pinned_set = pinned["setretrieval"]["accuracy"]
    random_top1 = random_baseline["expected_random_top1"]

    receipt = {
        "schema": "scbe_mahss_v8_pre_phase1_retrieval_bench_v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dim": DIM,
        "corpus": "v6g_raw_failure_corpus",
        "n_prompts": len(V6G_RAW_FAILURE_CORPUS),
        "phase1_threshold_setretrieval": 0.80,
        "phase1_pass_top1": pinned_top1 >= 0.80,
        "phase1_pass_setretrieval": pinned_set >= 0.80,
        "conditions": {
            "pinned_roles": pinned,
            "hash_control": hash_control,
        },
        "namespace_independence_probe": namespace_probe,
        "random_baseline": random_baseline,
        "headline": {
            "pinned_top1": round(pinned_top1, 4),
            "pinned_setretrieval": round(pinned_set, 4),
            "hash_control_top1": round(hash_control["top1"]["accuracy"], 4),
            "hash_control_setretrieval": round(hash_control["setretrieval"]["accuracy"], 4),
            "random_top1": round(random_top1, 4),
            "lift_over_random_top1": round(pinned_top1 - random_top1, 4),
            "lift_over_random_setretrieval": round(pinned_set - random_top1, 4),
        },
    }

    out_dir = _REPO_ROOT / "artifacts" / "mahss_v8_pre"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase1_retrieval_bench.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print(f"== v8-pre Phase 1 retrieval bench (dim={DIM}) ==")
    print(f"prompts: {len(V6G_RAW_FAILURE_CORPUS)} | total (role,filler) pairs: {pinned['n_pairs_total']}")
    print()
    print(f"pinned_roles    top-1:        {pinned_top1:.4f}  CI95: {pinned['top1']['wilson_95_ci']}")
    print(f"pinned_roles    setretrieval: {pinned_set:.4f}  CI95: {pinned['setretrieval']['wilson_95_ci']}")
    print(f"hash_control    top-1:        {hash_control['top1']['accuracy']:.4f}")
    print(f"hash_control    setretrieval: {hash_control['setretrieval']['accuracy']:.4f}")
    print(f"random baseline top-1:        {random_top1:.4f}")
    print(f"namespace probe SNR:          {namespace_probe['snr_ratio']}x")
    print()
    print("by-role accuracy (pinned, setretrieval-aware):")
    for role, data in pinned["by_role"].items():
        print(
            f"  {role:<8}  top1 {data['top1']}/{data['total']} ({data['top1_accuracy']:.0%})"
            f"   set {data['setretrieval']}/{data['total']} ({data['setretrieval_accuracy']:.0%})"
        )
    print()
    gate_top1 = "PASS" if receipt["phase1_pass_top1"] else "FAIL"
    gate_set = "PASS" if receipt["phase1_pass_setretrieval"] else "FAIL"
    print(f"PHASE 1 GATE (top-1 >= 0.80):        {gate_top1}")
    print(f"PHASE 1 GATE (setretrieval >= 0.80): {gate_set}")
    print(f"receipt: {out_path}")
    return 0 if receipt["phase1_pass_setretrieval"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
