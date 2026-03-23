from __future__ import annotations

import json
from pathlib import Path

from scripts.eval_legacy_hf_model import (
    EvalRecord,
    build_prompt,
    evaluate_records,
    load_eval_records,
    score_response,
    summarize_results,
    write_report,
)


def test_load_eval_records_reads_jsonl(tmp_path: Path) -> None:
    eval_path = tmp_path / "legacy.jsonl"
    eval_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "eval-001",
                        "category": "sacred-tongues",
                        "instruction": "List the sacred tongues",
                        "expected": "KO, AV, RU",
                        "response_should_contain": ["KO", "AV", "RU"],
                        "difficulty": "easy",
                    }
                ),
                json.dumps(
                    {
                        "id": "eval-002",
                        "category": "pipeline",
                        "instruction": "Describe the pipeline",
                        "expected": "embed -> classify",
                        "response_should_contain": ["embed", "classify"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    records = load_eval_records(eval_path)

    assert [record.id for record in records] == ["eval-001", "eval-002"]
    assert records[0].response_should_contain == ["KO", "AV", "RU"]
    assert records[1].category == "pipeline"


def test_score_response_is_case_insensitive_and_tracks_missing_terms() -> None:
    record = EvalRecord(
        id="eval-001",
        category="sacred-tongues",
        instruction="List the sacred tongues",
        expected="Kor'aelin and Draumric",
        response_should_contain=["Kor'aelin", "Draumric", "GABA"],
    )

    result = score_response(record, "kor'aelin maps to dopamine. DRAUMRIC handles structure.")

    assert result.matched_terms == ["Kor'aelin", "Draumric"]
    assert result.missing_terms == ["GABA"]
    assert result.term_match_ratio == 2 / 3
    assert result.passed is False


def test_evaluate_records_and_write_report(tmp_path: Path) -> None:
    records = [
        EvalRecord(
            id="eval-001",
            category="sacred-tongues",
            instruction="List the sacred tongues",
            expected="KO, AV, RU",
            response_should_contain=["KO", "AV"],
            difficulty="easy",
        ),
        EvalRecord(
            id="eval-002",
            category="pipeline",
            instruction="Describe the pipeline",
            expected="embed -> classify",
            response_should_contain=["embed", "classify"],
            difficulty="medium",
        ),
    ]

    answers = {
        "eval-001": "KO and AV are core tongues.",
        "eval-002": "It starts with embed_to_21d only.",
    }
    results = evaluate_records(records, lambda record: answers[record.id])
    summary = summarize_results(results)
    paths = write_report(tmp_path, "issdandavis/scbe-pivot-qwen-0.5b", summary, results)

    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["partial_hits"] == 2
    assert summary["matched_terms"] == 3
    assert summary["required_terms"] == 4
    assert summary["global_term_coverage"] == 0.75
    assert summary["categories"]["sacred-tongues"]["pass_rate"] == 1.0
    assert summary["categories"]["pipeline"]["pass_rate"] == 0.0
    assert summary["categories"]["pipeline"]["global_term_coverage"] == 0.5
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Pass Rate" in markdown
    assert "global_term_coverage" in markdown.lower()
    assert "Coverage" in markdown
    assert "eval-002" in markdown
    assert "Answer:" in build_prompt(records[0])
