"""Tests for the frozen-action math source audit."""

from __future__ import annotations

from fractions import Fraction
import json

from scripts.research.audit_frozen_action_math_sources import (
    _audit_row,
    _safe_value,
    _source_rows,
    _summarize,
)


def test_safe_value_is_bounded_arithmetic() -> None:
    assert _safe_value("(3+4)/2") == Fraction(7, 2)
    assert _safe_value("560//10") == 56


def test_audit_row_requires_value_consistency_and_compiler_acceptance() -> None:
    def compile_action(text: str) -> dict[str, str]:
        if "//" in text:
            raise ValueError("floor division is not supported")
        return {"receipt_sha256": "a" * 64}

    good = _audit_row(
        {
            "source": "fixture",
            "source_row_id": "good",
            "source_index": 0,
            "prompt": "What is three plus four?",
            "source_expression": "3+4",
            "expected": "7",
        },
        compile_action=compile_action,
    )
    unsupported = _audit_row(
        {
            "source": "fixture",
            "source_row_id": "unsupported",
            "source_index": 1,
            "prompt": "Divide evenly.",
            "source_expression": "560//10",
            "expected": "56",
        },
        compile_action=compile_action,
    )
    inconsistent = _audit_row(
        {
            "source": "fixture",
            "source_row_id": "inconsistent",
            "source_index": 2,
            "prompt": "A mismatched source row.",
            "source_expression": "4-2+3",
            "expected": "1",
        },
        compile_action=compile_action,
    )

    assert good["accepted"] is True
    assert unsupported["accepted"] is False
    assert unsupported["value_consistent"] is True
    assert unsupported["compiler_error"]["type"] == "ValueError"
    assert inconsistent["accepted"] is False
    assert inconsistent["compiler_receipt_sha256"] == "a" * 64
    assert _summarize([good, unsupported, inconsistent]) == {
        "accepted": 1,
        "accepted_ledger_sha256": _summarize([good])["accepted_ledger_sha256"],
        "compiler_rejected": 1,
        "missing_expression": 0,
        "rejected": 2,
        "rejected_row_ids": ["unsupported", "inconsistent"],
        "total": 3,
        "value_inconsistent": 1,
    }


def test_source_rows_extracts_last_gsm8k_annotation(tmp_path) -> None:
    gsm8k = tmp_path / "gsm8k.jsonl"
    gsm8k.write_text(
        json.dumps(
            {
                "question": "Two steps.",
                "answer": "First <<1+1=2>>. Then <<2*3=6>>.\n#### 6",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    svamp = tmp_path / "svamp.json"
    svamp.write_text(
        json.dumps(
            [
                {
                    "ID": "s1",
                    "Body": "There were four.",
                    "Question": "Two left; how many remain?",
                    "Equation": "4-2",
                    "Answer": 2,
                }
            ]
        ),
        encoding="utf-8",
    )

    rows = list(_source_rows(gsm8k, svamp))
    assert rows[0]["source_expression"] == "2*3"
    assert rows[0]["expected"] == "6"
    assert rows[1]["prompt"] == "There were four. Two left; how many remain?"
