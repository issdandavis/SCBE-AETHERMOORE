from __future__ import annotations

from scripts.benchmark.local_writing_benchmark import score_output, select_models


def test_score_output_passes_constrained_product_note() -> None:
    task = {
        "task_id": "free_local_product_note",
        "title": "Free/local product framing",
        "min_words": 10,
        "max_words": 80,
        "required_terms": ["free/local", "no API", "receipt"],
        "required_headings": ["Problem", "System", "Next Step"],
        "forbidden_terms": ["magic"],
    }
    output = """## Problem
People need simple tools.

## System
Use free/local AI, no API by default, and write a receipt for every run.

## Next Step
Run the local path first."""
    result = score_output(task, output, 0.1)
    assert result.passed
    assert result.score == 100.0


def test_score_output_catches_forbidden_and_missing_terms() -> None:
    task = {
        "task_id": "bad",
        "title": "Bad",
        "min_words": 1,
        "max_words": 20,
        "required_terms": ["receipt"],
        "forbidden_terms": ["magic"],
    }
    result = score_output(task, "This is magic.", 0.1)
    assert not result.passed
    assert result.checks["required_terms"]["receipt"] is False
    assert result.checks["forbidden_terms_absent"]["magic"] is False


def test_score_output_validates_ledger_json_array() -> None:
    task = {
        "task_id": "ledger",
        "title": "Ledger",
        "min_words": 1,
        "max_words": 80,
        "required_line_prefixes": ["Corrected:", "Ledger:"],
        "required_json_array_fields": ["old", "new", "reason"],
    }
    output = """Corrected: We need the AI to preserve meaning.

Ledger:
[
  {"old": "teh", "new": "the", "reason": "spelling correction"}
]"""
    result = score_output(task, output, 0.1)
    assert result.passed
    assert result.checks["json_array_fields"]["pass"] is True


def test_select_models_filters_cloud_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.benchmark.local_writing_benchmark.list_downloaded_ollama_models",
        lambda: {"local:1b", "remote:cloud"},
    )
    assert select_models(["local:1b", "remote:cloud", "missing:1b"]) == ["local:1b"]
