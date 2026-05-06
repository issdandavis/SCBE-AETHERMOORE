"""Production-shim gate rendering tests for dispatch_coding_agent_hf_job.py.

Verifies that when a profile opts into ``evaluation.production_shim_gate``,
the rendered HF Jobs training script:

1. parses as valid Python (no f-string brace-escape regressions),
2. wires PRODUCTION_SHIM_GATE / GATE_SUPPRESS_FORBIDDEN / GATE_BEST_OF_N
   from EVAL_CFG so per-job overrides via env or profile work,
3. inlines the canonical scaffold helpers
   (``_canonical_prefix``, ``_canonical_bad_words_ids``, etc.) so the
   container runs self-contained,
4. preserves backward compatibility: profiles without the new flags
   render exactly as before, with PRODUCTION_SHIM_GATE defaulting to
   False so the legacy ``constrained_gate_scaffold`` path is unchanged.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.system import dispatch_coding_agent_hf_job as dispatcher

REPO_ROOT = Path(__file__).resolve().parents[1]


def _baseline_profile() -> dict:
    return json.loads(
        (REPO_ROOT / "config" / "model_training" / "scbe-coding-primary-7b-qlora-v6c-DRAFT.json").read_text(
            encoding="utf-8"
        )
    )


def test_rendered_script_is_valid_python_with_new_flags():
    profile = _baseline_profile()
    profile.setdefault("evaluation", {})
    profile["evaluation"]["production_shim_gate"] = True
    profile["evaluation"]["gate_suppress_forbidden"] = True
    profile["evaluation"]["gate_best_of_n"] = True
    script = dispatcher.render_uv_training_script(profile)
    ast.parse(script)


def test_rendered_script_is_valid_python_without_new_flags():
    """Backward compatibility: profiles that do NOT set the new flags must
    render unchanged in semantics — flags default to False."""

    profile = _baseline_profile()
    profile.setdefault("evaluation", {}).pop("production_shim_gate", None)
    script = dispatcher.render_uv_training_script(profile)
    ast.parse(script)
    assert 'PRODUCTION_SHIM_GATE = bool(EVAL_CFG.get("production_shim_gate", False))' in script


def test_canonical_helpers_are_inlined_when_flag_set():
    profile = _baseline_profile()
    profile.setdefault("evaluation", {})["production_shim_gate"] = True
    script = dispatcher.render_uv_training_script(profile)
    for symbol in (
        "_PREFIX_SCAFFOLDS_CANONICAL",
        "_canonical_select_scaffold",
        "_canonical_filter_required",
        "_canonical_prefix",
        "_canonical_bad_words_ids",
        "_canonical_gate_one",
        "_canonical_gate_response",
    ):
        assert symbol in script, f"{symbol} missing from rendered template"


def test_report_payload_includes_new_flags():
    profile = _baseline_profile()
    profile.setdefault("evaluation", {})["production_shim_gate"] = True
    script = dispatcher.render_uv_training_script(profile)
    # Report dict literally writes these keys for downstream consumers.
    for key in (
        '"production_shim_gate": bool(PRODUCTION_SHIM_GATE)',
        '"gate_suppress_forbidden": bool(GATE_SUPPRESS_FORBIDDEN)',
        '"gate_best_of_n": bool(GATE_BEST_OF_N)',
    ):
        assert key in script, f"report missing key: {key!r}"


def test_legacy_scaffold_path_remains_intact():
    """The legacy CONSTRAINED_GATE_SCAFFOLD path (deterministic-receipt mode
    that v6c/v6e/v6e-bumped used) must still be present so existing profiles
    keep working bit-for-bit."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert "_scaffolded_gate_response" in script
    assert "SCBE_GATE_WRAPPER=deterministic receipt emitted" in script


def test_production_shim_branch_is_first_in_loop():
    """When PRODUCTION_SHIM_GATE is true, the new path must take precedence
    over the legacy CONSTRAINED_GATE_SCAFFOLD path; verify the source order."""

    profile = _baseline_profile()
    profile.setdefault("evaluation", {})["production_shim_gate"] = True
    script = dispatcher.render_uv_training_script(profile)
    pos_new = script.find("if PRODUCTION_SHIM_GATE:")
    pos_legacy = script.find("if CONSTRAINED_GATE_SCAFFOLD:")
    assert 0 <= pos_new < pos_legacy, (pos_new, pos_legacy)
