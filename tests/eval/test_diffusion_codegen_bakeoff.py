"""Tests for scripts/eval/diffusion_codegen_bakeoff.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval import diffusion_codegen_bakeoff as bakeoff

# ---------------------------------------------------------------------------
# Scorer parity with v6h `_gate_score`
# ---------------------------------------------------------------------------


def test_gate_score_passes_when_all_required_present_and_no_forbidden() -> None:
    prompt = {
        "id": "p1",
        "shape": "simple_implementation",
        "required": ["def foo", "return"],
        "forbidden": ["TODO"],
    }
    response = "def foo(x):\n    return x"
    v = bakeoff.gate_score(prompt, response)
    assert v.ok is True
    assert v.missing_required == []
    assert v.triggered_forbidden == []
    assert v.id == "p1"
    assert v.shape == "simple_implementation"


def test_gate_score_lowercases_required_per_v6h() -> None:
    prompt = {"id": "p", "required": ["UMBROTH"], "forbidden": []}
    response = "the umbroth tongue is haskell"
    assert bakeoff.gate_score(prompt, response).ok is True


def test_gate_score_word_boundary_for_alphanumeric_forbidden() -> None:
    # `atom` is forbidden — but `atomicity` should not trigger it.
    prompt = {"id": "p", "required": [], "forbidden": ["atom"]}
    assert bakeoff.gate_score(prompt, "atomicity is fine").ok is True
    assert bakeoff.gate_score(prompt, "an atom of carbon").ok is False


def test_gate_score_substring_for_non_alphanumeric_forbidden() -> None:
    # Tokens with punctuation fall back to plain substring (v6h behavior).
    prompt = {"id": "p", "required": [], "forbidden": ["def count_vowels("]}
    assert bakeoff.gate_score(prompt, "def count_vowels(s):").ok is False
    assert bakeoff.gate_score(prompt, "count_vowels does this").ok is True


def test_gate_score_reports_missing_required() -> None:
    prompt = {"id": "p", "required": ["alpha", "beta", "gamma"], "forbidden": []}
    v = bakeoff.gate_score(prompt, "alpha and gamma only")
    assert v.ok is False
    assert v.missing_required == ["beta"]


# ---------------------------------------------------------------------------
# Contract / shape coverage
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config" / "eval" / "coding_diffusion_bakeoff_v1.json"


def test_contract_loads_and_has_12_prompts() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    assert contract["contract_id"] == "coding_diffusion_bakeoff_v1"
    assert contract["source_contract"] == "coding_verification_unseen_eval_v2"
    assert len(contract["prompts"]) == 12


def test_every_prompt_has_known_shape() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    known = set(contract["shape_taxonomy"].keys())
    for p in contract["prompts"]:
        assert p["shape"] in known, f"unknown shape {p['shape']!r} on {p['id']}"


def test_contract_required_and_forbidden_are_lists_of_strings() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    for p in contract["prompts"]:
        assert isinstance(p["required"], list) and all(isinstance(t, str) for t in p["required"])
        assert isinstance(p["forbidden"], list) and all(isinstance(t, str) for t in p["forbidden"])


# ---------------------------------------------------------------------------
# Bake-off + triangulation (dry-run end-to-end)
# ---------------------------------------------------------------------------


def _stub_gen_factory(passing_ids: set[str]):
    """Build a generator that PASSES exactly the prompt ids in `passing_ids`."""

    def _gen(prompt: dict) -> str:
        if prompt.get("id") in passing_ids:
            # Concat all required tokens; avoid forbidden.
            return " ".join(prompt.get("required") or [])
        return "(stub: nothing useful)"

    return _gen


def test_run_bakeoff_dry_run_produces_consistent_pass_counts() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    ar_pass = {"code_eval_inventory_unique_python", "code_eval_avali_javascript_lens"}
    diff_pass = ar_pass | {
        "code_eval_multi_lens_consistency",
        "code_eval_lane_boundary_no_chem",
    }
    gens = [
        ("ar", "stub::ar", _stub_gen_factory(ar_pass)),
        ("diffusion", "stub::diff", _stub_gen_factory(diff_pass)),
    ]
    report, raws = bakeoff.run_bakeoff(contract, gens)
    by_label = {g["label"]: g for g in report["generators"]}
    assert by_label["ar"]["n_pass"] == 2
    assert by_label["diffusion"]["n_pass"] == 4
    # 12 prompts × 2 generators = 24 raw responses
    assert len(raws) == 24


def test_triangulation_includes_shape_delta_when_both_labels_present() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    ar_pass: set[str] = set()
    diff_pass = {"code_eval_multi_lens_consistency"}  # only a multi_lens prompt
    gens = [
        ("ar", "stub::ar", _stub_gen_factory(ar_pass)),
        ("diffusion", "stub::diff", _stub_gen_factory(diff_pass)),
    ]
    report, _ = bakeoff.run_bakeoff(contract, gens)
    delta = report["triangulation"]["shape_delta"]
    assert "multi_lens_parallel" in delta
    assert delta["multi_lens_parallel"]["delta"] == 1
    # Shapes where neither passes show 0 delta
    for shape, row in delta.items():
        if shape != "multi_lens_parallel":
            assert row["delta"] == 0


def test_triangulation_classifies_split_vs_all_pass_vs_all_fail() -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    ar_pass = {"code_eval_inventory_unique_python"}  # ar wins this one
    diff_pass = {"code_eval_inventory_unique_python", "code_eval_clamp_value_rust"}
    gens = [
        ("ar", "stub::ar", _stub_gen_factory(ar_pass)),
        ("diffusion", "stub::diff", _stub_gen_factory(diff_pass)),
    ]
    report, _ = bakeoff.run_bakeoff(contract, gens)
    by_id = {row["id"]: row for row in report["triangulation"]["by_prompt"]}
    assert by_id["code_eval_inventory_unique_python"]["verdict_class"] == "all_pass"
    assert by_id["code_eval_clamp_value_rust"]["verdict_class"] == "split"
    # An untouched prompt is "all_fail"
    untouched = "code_eval_runethic_option_chain"
    assert by_id[untouched]["verdict_class"] == "all_fail"


def test_dry_run_main_writes_artifact(tmp_path: Path) -> None:
    out_dir = tmp_path / "artifacts"
    rc = bakeoff.main(
        [
            "--dry-run",
            "--out-dir",
            str(out_dir),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    assert rc == 0
    json_files = list(out_dir.glob("diffusion_bakeoff_*.json"))
    raws_files = list(out_dir.glob("diffusion_bakeoff_*.responses.jsonl"))
    assert json_files, "expected report json"
    assert raws_files, "expected raw responses jsonl"
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scbe_diffusion_bakeoff_report_v1"
    assert payload["n_prompts"] == 12
    labels = {g["label"] for g in payload["generators"]}
    assert labels == {"ar", "diffusion"}


def test_baseline_only_skips_diffusion(tmp_path: Path) -> None:
    out_dir = tmp_path / "artifacts"
    rc = bakeoff.main(
        [
            "--dry-run",
            "--baseline-only",
            "--out-dir",
            str(out_dir),
            "--contract",
            str(CONTRACT_PATH),
        ]
    )
    assert rc == 0
    payload = json.loads(next(out_dir.glob("diffusion_bakeoff_*.json")).read_text(encoding="utf-8"))
    labels = {g["label"] for g in payload["generators"]}
    assert labels == {"ar"}


def test_emit_markdown_report(tmp_path: Path) -> None:
    contract = bakeoff.load_contract(CONTRACT_PATH)
    gens = [
        ("ar", "stub::ar", _stub_gen_factory(set())),
        ("diffusion", "stub::diff", _stub_gen_factory({"code_eval_lane_boundary_no_chem"})),
    ]
    report, _ = bakeoff.run_bakeoff(contract, gens)
    md_path = tmp_path / "report.md"
    bakeoff.emit_markdown_report(report, md_path)
    md = md_path.read_text(encoding="utf-8")
    assert "Code-Diffusion Bake-Off" in md
    assert "Per-shape delta" in md
    assert "negative_constraint" in md
