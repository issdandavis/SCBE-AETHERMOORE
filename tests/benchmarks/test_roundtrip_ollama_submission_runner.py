from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "benchmarks" / "scbe_bijective_round_trip" / "run_ollama_submission.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("roundtrip_ollama_submission_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_slots_from_prompt_extracts_slots_line_and_slot_equals() -> None:
    runner = _load_runner()
    prompt = """
    Slots: sig, init, loop_body
    Multi-slot edit:
      - slot=init: initialize accumulator
      - slot=ret: return total
    """
    assert runner._slots_from_prompt(prompt) == ["sig", "init", "loop_body", "ret"]


def test_contract_repair_adds_missing_tongue_and_slot_markers() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Edit request: slot=init and slot=loop_body.",
        "meta": {"task": "multiline_edit", "algorithm": "sum_list"},
    }
    repaired = runner.contract_repair(row, "body")
    assert "## algorithm: sum_list" in repaired
    for tongue in runner.TONGUE_ORDER:
        assert f"### TONGUE:{tongue}" in repaired
    assert "#slot:init" in repaired
    assert "#slot:loop_body" in repaired


def test_expanded_slots_infers_multiline_loop_contract_from_public_prompt() -> None:
    runner = _load_runner()
    row = {
        "prompt": """
        Original:
        def sum_list(xs):
            total = 0
            for x in xs:
                total += x
            return total
        Multi-slot edit:
          - slot=init: initialize accumulator to 1
          - slot=loop_body: convert sum into product
        """,
        "meta": {"task": "multiline_edit", "slots": ["init", "loop_body"]},
    }
    assert runner.expanded_slots(row) == ["sig", "init", "loop_open", "loop_body", "ret"]


def test_metadata_preface_uses_public_algorithm_and_slots() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Slots: sig, body.",
        "meta": {"task": "translate_all", "algorithm": "is_even", "src": "UM"},
    }
    preface = runner.metadata_preface(row)
    assert "## algorithm: is_even" in preface
    assert "## task: translate_all" in preface
    assert "## tongue: UM (Umbroth)" in preface
    assert "## slots: sig, body" in preface


def test_build_prompt_includes_public_algorithm_lookup_card() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Translate this.",
        "meta": {"task": "translate_one", "algorithm": "linear_search", "src": "UM", "dst": "KO"},
    }
    prompt = runner.build_prompt(row, include_algorithm_card=True)
    assert "Algorithm lookup card:" in prompt
    assert "canonical label: linear_search" in prompt
    assert "return -1 on miss" in prompt


def test_build_prompt_omits_algorithm_card_by_default() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Translate this.",
        "meta": {"task": "translate_one", "algorithm": "linear_search", "src": "UM", "dst": "KO"},
    }
    prompt = runner.build_prompt(row)
    assert "Algorithm lookup card:" not in prompt


def test_structural_scaffold_wraps_translate_all_in_all_six_tongues() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Emit all six tongues. Slots: sig, body.",
        "meta": {"task": "translate_all"},
    }
    scaffold = runner.structural_scaffold(row, "return x")
    for tongue in runner.TONGUE_ORDER:
        assert f"### TONGUE:{tongue}" in scaffold
    assert "#slot:sig" in scaffold
    assert "#slot:body" in scaffold


def test_write_failure_lessons_omits_hidden_reference_text(tmp_path) -> None:
    runner = _load_runner()

    class FakeScorer:
        @staticmethod
        def _ref_signature(reference, task):
            assert "hidden answer" in reference
            return {"codeblock_count": 1, "slot_count": 0, "tongue_count": 0, "task": task}

    rows = [
        {
            "id": "r1",
            "prompt": "Slots: sig",
            "reference": "hidden answer ```py\nx=1\n```",
            "meta": {"task": "translate_one", "algorithm": "demo", "tongue": "KO"},
        }
    ]
    report = {"per_row": [{"id": "r1", "row_score": 0.5, "token_recall": 0.5, "structural_preservation": 1.0}]}
    diagnostics = [{"id": "r1", "raw_prediction_preview": "raw", "prediction_preview": "pred"}]
    out = tmp_path / "lessons.jsonl"

    count = runner.write_failure_lessons(rows, report, diagnostics, FakeScorer(), out)

    assert count == 1
    text = out.read_text(encoding="utf-8")
    assert "hidden answer" not in text
    assert "codeblock_count" in text
    assert "raw" in text


def test_lookup_verify_rejects_missing_translate_all_sections() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Emit all six tongues. Slots: sig, body.",
        "meta": {"task": "translate_all", "algorithm": "demo", "slots": ["sig", "body"]},
    }
    result = runner.lookup_verify(row, "demo\n### TONGUE:KO\n```py\n#slot:sig\n```")
    assert not result["ok"]
    assert any("missing tongue sections" in issue for issue in result["issues"])
    assert any("slot `body`" in issue for issue in result["issues"])


def test_lookup_verify_accepts_complete_translate_one_target_fence() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Translate to tongue UM (Haskell), preserving slot alignment.",
        "meta": {"task": "translate_one", "algorithm": "demo", "src": "KO", "dst": "UM"},
    }
    result = runner.lookup_verify(row, "demo\n```hs\nx = x\n```")
    assert result["ok"]


def test_lookup_verify_identify_requires_exact_algorithm() -> None:
    runner = _load_runner()
    row = {
        "prompt": "Identify this.",
        "meta": {"task": "identify", "algorithm": "is_even", "tongue": "UM"},
    }
    result = runner.lookup_verify(row, "Algorithm: parity\nTongue: UM\nslots: sig, body")
    assert not result["ok"]
    assert any("is_even" in issue for issue in result["issues"])
