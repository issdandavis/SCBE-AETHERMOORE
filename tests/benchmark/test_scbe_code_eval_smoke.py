from scripts.benchmark.scbe_code_eval import (
    StubModel,
    evaluate_case,
    load_prompt_cases,
    summarize,
)


def test_scbe_code_eval_smoke():
    cases = load_prompt_cases("tests/fixtures/code_eval_prompts.json")
    model = StubModel()

    records = [evaluate_case(case, model) for case in cases]
    summary = summarize(records)

    assert len(records) >= 4
    assert summary["total"] == len(records)
    assert summary["decision_counts"]["ALLOW"] + summary["decision_counts"]["QUARANTINE"] + summary["decision_counts"]["DENY"] == len(records)
    assert summary["final_pass_rate"] >= summary["baseline_pass_rate"]
    assert any(record.retry_used for record in records)
    assert any(record.final_checks["tests_passed"] for record in records)
