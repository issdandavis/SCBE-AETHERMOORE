"""Local sanity check for Phase 3a-2 bridge memory binding.

Confirms that the schema -> memory pipeline actually binds helper names
to their signatures in a way the bridge can retrieve. Without this
check, a passing dispatch could mean "bridge worked" or "bridge ran on
garbage memory and we got noise" — same lexical result either way.

What this checks:
1. schema_to_memory_and_vocab builds an HRR memory bundle from a schema
   shaped like {helper_name: [signature_summary]}.
2. Querying the memory with the helper-name role vector via circular
   correlation returns a vector that's closer to the bound signature
   filler than to any other filler in the vocab.

Runs locally on CPU; no GPU, no model load.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch

# Reuse the same primitives the dispatcher embeds
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
import importlib.util

DISPATCHER = Path(__file__).resolve().parents[1] / "eval" / "hf_job_v8_pre_phase3a_2_retrieval_pivot.py"
spec = importlib.util.spec_from_file_location("d", DISPATCHER)
mod = importlib.util.module_from_spec(spec)
# Don't call main(); just import the helpers
spec.loader.exec_module(mod)

DIM = 1024


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a / (a.norm() + 1e-9)).dot(b / (b.norm() + 1e-9)).item())


def main() -> int:
    helpers = [
        ("harmonic_wall", "(d_h: float, pd: float) -> float; returns 1/(1 + d_h + 2*pd)"),
        (
            "phi_weight",
            "(tongue: str) -> float; returns {KO:1.00, AV:1.62, RU:2.62, CA:4.24, UM:6.85, DR:11.09}[tongue]",
        ),
        ("poincare_distance", "(u, v) -> float; returns arcosh(...)"),
        ("tongue_encode", "(text: str, tongue_code: str) -> list[int]; ..."),
        ("breath_phase", "(t: float) -> float; sin(2*pi*t/period)"),
        ("realm_transition", "(state: str, score: float) -> str; ..."),
    ]

    # Build a single shared memory bundle with ALL bindings (worst case
    # for retrieval — superposition interference is highest here).
    schema = {name: [filler] for name, filler in helpers}
    memory, vocab = mod.schema_to_memory_and_vocab(schema, DIM, "cpu", torch.float32)
    print(f"memory shape: {tuple(memory.shape)}, vocab shape: {tuple(vocab.shape)}")
    print(f"memory norm:  {memory.norm().item():.4f}")
    print()

    # For each helper, query memory with role-vec(name) via circular correlation.
    # The retrieval should be closer to the correct filler than to any other.
    print(f"{'helper':<22} {'self_cos':<10} {'best_other':<12} {'top_match':<22} {'OK'}")
    print("-" * 80)
    n_correct = 0
    for i, (name, filler) in enumerate(helpers):
        role_vec = mod.deterministic_role_vector(f"role::{name}", DIM)
        u = mod.circular_correlation_torch(role_vec, memory)
        # Cosine vs each filler in vocab (vocab is stacked in helper order)
        cosines = []
        for j, (_, _other_filler) in enumerate(helpers):
            # Note: filler vectors stored in vocab are namespaced by role::filler,
            # so vocab[j] corresponds to the j-th helper's filler under name
            cosines.append(cosine(u, vocab[j]))
        self_idx = i
        self_cos = cosines[self_idx]
        other_cosines = [c for j, c in enumerate(cosines) if j != self_idx]
        best_other = max(other_cosines)
        top_idx = max(range(len(cosines)), key=lambda j: cosines[j])
        ok = top_idx == self_idx
        n_correct += int(ok)
        print(f"{name:<22} {self_cos:<10.4f} {best_other:<12.4f} {helpers[top_idx][0]:<22} {ok}")

    print("-" * 80)
    print(f"correct retrievals: {n_correct}/{len(helpers)}")
    if n_correct == len(helpers):
        print("PASS: memory binding works — bridge can retrieve correct filler for each helper.")
        return 0
    else:
        print(f"FAIL: {len(helpers) - n_correct} helper(s) retrieved wrong filler.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
