"""Probe: does the eval_runner-class language-idiom-drift recur on a NEW case?

Catalog Open Question 2 (artifacts/bijective_tongue/failure_mode_catalog.md):
"Is the eval_runner case the canonical pattern, or are there other cases waiting
to manifest at higher tongue volume?"

This probe answers it. Adds a NEW case `to_string` whose body uses Python's `str()`
built-in (which has different names across tongues: Rust to_string/format!, JS
String/toString, Mathematica ToString, Haskell show). BACK_PREFIX is INTENTIONALLY
MINIMAL — signature only, no body — replicating the original eval_runner failure
condition.

If the catalog hypothesis (eval_runner was a unique case) holds: 5/5 across tongues.
If language-idiom drift is general: <5/5 with surface drift visible in failures.

Output: artifacts/bijective_tongue/probe_print_pattern_<ts>.json
Cost: $0 (CPU). Runtime: ~5-10 min on Qwen-0.5B CPU.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE_PATH = REPO / "scripts" / "eval" / "run_bijective_constrained_decoding_local.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("bijective_gate", GATE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


PROBE_CASE_ID = "to_string"
PROBE_PROMPT = (
    "Write a Python function to_string(x: object) -> str that returns the standard "
    "string representation of x by calling Python's built-in str()."
)
PROBE_ENTRYPOINT = "to_string"
PROBE_ASSERTIONS = (
    "assert to_string(42) == '42'",
    "assert to_string('hi') == 'hi'",
    "assert to_string(True) == 'True'",
    "assert to_string(None) == 'None'",
)
PROBE_SEED = "def to_string(x: object) -> str:\n    return str(x)\n"
PROBE_BACK_PREFIX_MINIMAL = "def to_string(x: object) -> str:\n"  # signature only, no body


def main() -> int:
    gate = _load_gate()
    case = gate.PromptCase(
        case_id=PROBE_CASE_ID,
        prompt=PROBE_PROMPT,
        entrypoint=PROBE_ENTRYPOINT,
        assertions=PROBE_ASSERTIONS,
    )
    gate.SEEDS[PROBE_CASE_ID] = PROBE_SEED
    gate.BACK_PREFIX[PROBE_CASE_ID] = PROBE_BACK_PREFIX_MINIMAL

    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    print(f"loading base: {gate.BASE_MODEL}")
    print(f"  device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    tokenizer = AutoTokenizer.from_pretrained(gate.BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    use_cuda = torch.cuda.is_available()
    model = AutoModelForCausalLM.from_pretrained(
        gate.BASE_MODEL,
        torch_dtype=torch.float16 if use_cuda else torch.float32,
        device_map="auto" if use_cuda else None,
        low_cpu_mem_usage=True,
    )
    if not use_cuda:
        model = model.to("cpu")
    model.eval()

    fwd_generate, back_generate = gate.make_generators(model, tokenizer)

    print(f"\nProbe case: {PROBE_CASE_ID} (minimal BACK_PREFIX, signature only)")
    print(f"  prefix = {PROBE_BACK_PREFIX_MINIMAL!r}")
    print()

    results = []
    n_pass = 0
    for tongue in gate.GATE_TONGUES:
        print(f"--- {tongue} ---")
        try:
            r = gate.round_trip_case(case, tongue, fwd_generate, back_generate)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            results.append({"tongue": tongue, "tests_passed": False, "error": f"{type(e).__name__}: {e}"})
            continue
        n_pass += int(r.tests_passed)
        head = (r.round_tripped_python or "")[:200]
        print(f"  tests_passed: {r.tests_passed}  syntax_ok: {r.syntax_ok}  exec_ok: {r.exec_ok}")
        print(f"  round_tripped: {head!r}")
        if not r.tests_passed and r.error:
            print(f"  error: {r.error}")
        results.append({
            "tongue": tongue,
            "tests_passed": r.tests_passed,
            "syntax_ok": r.syntax_ok,
            "exec_ok": r.exec_ok,
            "round_tripped_head": head,
            "intermediate_head": (r.intermediate_code or "")[:200],
            "error": r.error,
            "back_used_prefix": r.back_used_prefix,
            "forward_seconds": r.forward_seconds,
            "back_seconds": r.back_seconds,
        })

    n = len(gate.GATE_TONGUES)
    print()
    print("=" * 70)
    print(f"Probe result: {n_pass}/{n} pass")
    if n_pass == n:
        verdict = "CATALOG_HYPOTHESIS_HOLDS"
        long = ("All tongues passed with minimal prefix. eval_runner was a specific "
                "case, not a general drift pattern. Per-case BACK_PREFIX tightening "
                "remains the right approach.")
    elif n_pass >= 3:
        verdict = "PARTIAL_DRIFT"
        long = (f"{n - n_pass}/{n} tongues drifted. Drift is real but not universal. "
                "Catalog should treat language-idiom-drift as a per-tongue pattern.")
    else:
        verdict = "DRIFT_IS_GENERAL"
        long = (f"{n - n_pass}/{n} tongues drifted. Catalog hypothesis was wrong; "
                "drift is general. Need a structural fix (e.g., body-assertion-with-"
                "retry) rather than per-case prefix patches.")

    print(f"VERDICT: {verdict}")
    print(long)
    print("=" * 70)

    out_dir = REPO / "artifacts" / "bijective_tongue"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    out_path = out_dir / f"probe_print_pattern_{ts}.json"
    out_path.write_text(json.dumps({
        "schema": "scbe_bijective_probe_v1",
        "probe_case": PROBE_CASE_ID,
        "minimal_back_prefix": PROBE_BACK_PREFIX_MINIMAL,
        "tongues": list(gate.GATE_TONGUES),
        "n_pass": n_pass,
        "n_total": n,
        "verdict": verdict,
        "verdict_long": long,
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"\nReceipt: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
