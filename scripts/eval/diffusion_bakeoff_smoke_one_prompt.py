"""Single-prompt smoke for the bake-off — times AR vs Schrödinger on CPU.

Use this BEFORE the full 12-prompt run to confirm the chosen model
loads and decodes within a sensible budget on this machine.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config" / "eval" / "coding_diffusion_bakeoff_v1.json"

MODEL_ID = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MAX_NEW_TOKENS = 192


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    prompt = contract["prompts"][0]  # code_eval_inventory_unique_python (simple_implementation)
    print(f"prompt: {prompt['id']}  shape: {prompt['shape']}")
    print(f"required: {prompt['required']}")
    print(f"forbidden: {prompt['forbidden']}")

    from scripts.eval.diffusion_codegen_bakeoff import (
        gate_score,
        make_ar_generator,
        make_schrodinger_generator_local,
    )

    print(f"\n[ar] loading {MODEL_ID}…")
    t0 = time.time()
    ar_gen = make_ar_generator(MODEL_ID, MAX_NEW_TOKENS)
    ar_resp = ar_gen(prompt)
    ar_elapsed = time.time() - t0
    print(f"[ar] {ar_elapsed:.1f}s ({len(ar_resp)} chars)")
    print(f"---ar response---\n{ar_resp}\n---")
    ar_v = gate_score(prompt, ar_resp)
    print(f"[ar] ok={ar_v.ok}  missing={ar_v.missing_required}  triggered={ar_v.triggered_forbidden}")

    print(f"\n[schrodinger] loading {MODEL_ID}…")
    t0 = time.time()
    sw_gen = make_schrodinger_generator_local(MODEL_ID, MAX_NEW_TOKENS)
    sw_resp = sw_gen(prompt)
    sw_elapsed = time.time() - t0
    print(f"[schrodinger] {sw_elapsed:.1f}s ({len(sw_resp)} chars)")
    print(f"---schrodinger response---\n{sw_resp}\n---")
    sw_v = gate_score(prompt, sw_resp)
    print(f"[schrodinger] ok={sw_v.ok}  missing={sw_v.missing_required}  triggered={sw_v.triggered_forbidden}")

    print(f"\n[budget] full run (12 prompts x 2 generators) ~= {12 * (ar_elapsed + sw_elapsed):.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
