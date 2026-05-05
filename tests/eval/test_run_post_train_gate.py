"""Unit tests for the post-train gate runner.

Tests cover happy-path PASS, must_pass FAIL, minimum_pass_rate FAIL,
contract validation, candidate validation, and the exit-code mapping.
No model loads, no network, just the JSON-in/JSON-out contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval.run_post_train_gate import (
    build_payload,
    evaluate,
    gate_passed,
    load_candidates,
    load_contract,
    main,
)


def _write_contract(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_stage_eval_contract_v1",
                "contract_id": "unit_post_train_gate",
                "thresholds": {
                    "minimum_pass_rate": 0.5,
                    "must_pass": ["p_must"],
                },
                "prompts": [
                    {
                        "id": "p_must",
                        "prompt": "must-pass prompt",
                        "required": ["alpha"],
                        "forbidden": ["betatrigger"],
                    },
                    {
                        "id": "p_nice",
                        "prompt": "nice-to-have prompt",
                        "required": ["gamma"],
                        "forbidden": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_candidates(path: Path, candidates: list[dict]) -> Path:
    path.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return path


def test_gate_passes_when_all_thresholds_met(tmp_path: Path) -> None:
    contract_path = _write_contract(tmp_path / "contract.json")
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "happy",
                "metadata": {"step": 180},
                "responses": {"p_must": "alpha is present", "p_nice": "gamma here too"},
            }
        ],
    )

    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")

    assert gate_passed(report)
    assert report["candidate_count"] == 1
    assert report["candidate_results"][0]["pass_rate"] == 1.0
    assert report["candidate_results"][0]["must_pass_all_ok"] is True


def test_gate_fails_when_must_pass_prompt_misses_required(tmp_path: Path) -> None:
    contract_path = _write_contract(tmp_path / "contract.json")
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "must_pass_misses",
                "metadata": {},
                "responses": {"p_must": "no required token here", "p_nice": "gamma included"},
            }
        ],
    )

    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")

    assert not gate_passed(report)
    assert report["candidate_results"][0]["must_pass_all_ok"] is False


def test_gate_fails_when_forbidden_token_triggers_in_must_pass(tmp_path: Path) -> None:
    contract_path = _write_contract(tmp_path / "contract.json")
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "boundary_breach",
                "metadata": {},
                "responses": {
                    "p_must": "alpha is present but betatrigger leaked",
                    "p_nice": "gamma included",
                },
            }
        ],
    )

    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")

    assert not gate_passed(report)


def test_forbidden_token_uses_word_boundary_not_substring(tmp_path: Path) -> None:
    """Word-boundary semantics: forbidden 'PASS' must NOT trigger on 'compass' or 'PASSAGE'.

    Mirrors dispatcher inline gate behavior so offline re-scoring produces
    the same verdict as the on-runner gate.
    """
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_id": "word_boundary_check",
                "thresholds": {"minimum_pass_rate": 1.0, "must_pass": []},
                "prompts": [
                    {
                        "id": "p1",
                        "prompt": "p",
                        "required": ["needed"],
                        "forbidden": ["PASS", "promote"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "stems_should_not_trigger",
                "metadata": {},
                "responses": {
                    "p1": "needed token is here. The compass shows north and the passage is open. Promotion is also fine.",
                },
            }
        ],
    )

    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")
    assert gate_passed(report), report["candidate_results"]


def test_forbidden_token_does_trigger_on_exact_word(tmp_path: Path) -> None:
    """Counterpart: same token DOES trigger on exact word boundary."""
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_id": "word_boundary_positive",
                "thresholds": {"minimum_pass_rate": 1.0, "must_pass": []},
                "prompts": [
                    {
                        "id": "p1",
                        "prompt": "p",
                        "required": ["needed"],
                        "forbidden": ["PASS"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "exact_word_should_trigger",
                "metadata": {},
                "responses": {"p1": "needed token here. Verdict: PASS."},
            }
        ],
    )
    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")
    assert not gate_passed(report)


def test_gate_fails_when_pass_rate_below_minimum(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_id": "rate_only",
                "thresholds": {"minimum_pass_rate": 1.0, "must_pass": []},
                "prompts": [
                    {"id": "a", "prompt": "a", "required": ["needed"], "forbidden": []},
                    {"id": "b", "prompt": "b", "required": ["needed"], "forbidden": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "half_only",
                "metadata": {},
                "responses": {"a": "needed in a", "b": "missing token"},
            }
        ],
    )

    report = evaluate(contract_path, candidates_path, tmp_path / "report.json")

    assert not gate_passed(report)
    assert report["candidate_results"][0]["pass_rate"] == 0.5


def test_load_contract_rejects_empty_prompts(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps({"prompts": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="prompts"):
        load_contract(contract_path)


def test_load_candidates_rejects_empty_candidates(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(json.dumps({"candidates": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="candidates"):
        load_candidates(candidates_path)


def test_build_payload_threads_seed_when_provided() -> None:
    contract = {"prompts": [{"id": "x", "prompt": "x", "required": [], "forbidden": []}]}
    candidates = [{"candidate_id": "c", "responses": {"x": "ok"}, "metadata": {}}]
    payload_with = build_payload(contract, candidates, "deterministic-seed")
    payload_without = build_payload(contract, candidates, None)
    assert payload_with["seed"] == "deterministic-seed"
    assert "seed" not in payload_without


def test_main_returns_zero_on_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    contract_path = _write_contract(tmp_path / "contract.json")
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "main_happy",
                "metadata": {},
                "responses": {"p_must": "alpha", "p_nice": "gamma"},
            }
        ],
    )
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_post_train_gate",
            "--contract",
            str(contract_path),
            "--candidates",
            str(candidates_path),
            "--out",
            str(report_path),
        ],
    )
    assert main() == 0
    out = capsys.readouterr().out
    assert "passed=1/1" in out
    assert "PASS main_happy" in out


def test_main_returns_nonzero_on_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    contract_path = _write_contract(tmp_path / "contract.json")
    candidates_path = _write_candidates(
        tmp_path / "candidates.json",
        [
            {
                "candidate_id": "main_fail",
                "metadata": {},
                "responses": {"p_must": "the required token is missing entirely", "p_nice": "gamma"},
            }
        ],
    )
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_post_train_gate",
            "--contract",
            str(contract_path),
            "--candidates",
            str(candidates_path),
            "--out",
            str(report_path),
        ],
    )
    assert main() == 1
    out = capsys.readouterr().out
    assert "FAIL main_fail" in out
