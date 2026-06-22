from python.helm.answer_stage import (
    RESTART_CHECKPOINT,
    AnswerAttempt,
    StageTask,
    arrow_hint,
    model_instructions,
    run_jsonl,
    score_attempt,
)


def test_model_instructions_are_domain_aware_and_fixed_format():
    task = StageTask(
        stage_id="diabetes_ratio",
        domain="diabetes",
        prompt="Calculate a carb ratio example from supplied numbers.",
        expected_answer="12",
        required_process_tokens=["60/5"],
        units="grams/unit",
    )

    instructions = model_instructions(task)

    assert "ANSWER:" in instructions
    assert "PROCESS:" in instructions
    assert "SAFETY:" in instructions
    assert "Do not diagnose" in instructions


def test_full_physics_answer_scores_high_and_continues():
    task = StageTask(
        stage_id="physics_speed",
        domain="physics",
        prompt="A cart travels 20 m in 4 s. Find speed.",
        expected_answer="5",
        required_process_tokens=["v=d/t", "20/4"],
        units="m/s",
        context_budget_tokens=2000,
    )
    attempt = AnswerAttempt(
        text="ANSWER: 5\nPROCESS: v=d/t, 20/4=5\nCHECK: 5*4=20\nUNITS: m/s\nCONFIDENCE: high",
        elapsed_seconds=90,
        context_used_tokens=400,
    )

    report = score_attempt(task, attempt)

    assert report["score"] == 1.0
    assert report["arrow"]["kind"] == "finish"
    assert report["checkpoint"]["action"] == "continue"


def test_arrow_points_to_missing_answer_or_process_token():
    task = StageTask(
        stage_id="math_area",
        domain="mathematics",
        prompt="Area of a 3 by 4 rectangle.",
        expected_answer="12",
        required_process_tokens=["3*4"],
        units="square units",
    )
    missing_answer = AnswerAttempt(
        text="PROCESS: 3*4=12\nCHECK: ok\nUNITS: square units\nCONFIDENCE: high",
        elapsed_seconds=10,
        context_used_tokens=100,
    )
    wrong_process = AnswerAttempt(
        text="ANSWER: 12\nPROCESS: multiply sides\nCHECK: ok\nUNITS: square units\nCONFIDENCE: high",
        elapsed_seconds=10,
        context_used_tokens=100,
    )

    assert arrow_hint(task, missing_answer)["arrow"] == "-> ANSWER:"
    assert arrow_hint(task, wrong_process)["arrow"] == "-> 3*4"


def test_low_score_or_high_context_restarts_from_checkpoint():
    task = StageTask(
        stage_id="math_fail",
        domain="mathematics",
        prompt="2+2",
        expected_answer="4",
        checkpoint_id="math_fail_start",
        context_budget_tokens=1000,
    )
    attempt = AnswerAttempt(
        text="ANSWER: 5\nPROCESS: guessed\nCHECK: none\nUNITS: none\nCONFIDENCE: low",
        elapsed_seconds=3,
        context_used_tokens=900,
    )

    report = score_attempt(task, attempt)

    assert report["checkpoint"]["action"] == RESTART_CHECKPOINT
    assert report["checkpoint"]["checkpoint_id"] == "math_fail_start"
    assert any("context_ratio" in r for r in report["checkpoint"]["reasons"])


def test_diabetes_stage_requires_safety_section_for_full_score():
    task = StageTask(
        stage_id="diabetes_calc",
        domain="diabetes",
        prompt="Given verified inputs only, compute 60/5.",
        expected_answer="12",
        required_process_tokens=["60/5"],
        units="grams/unit",
        target_seconds=60,
    )
    attempt = AnswerAttempt(
        text=(
            "ANSWER: 12\n"
            "PROCESS: 60/5=12\n"
            "CHECK: 12*5=60\n"
            "UNITS: grams/unit\n"
            "CONFIDENCE: high\n"
            "SAFETY: calculation only, not medical advice; clinician required for treatment decisions"
        ),
        elapsed_seconds=60,
        context_used_tokens=100,
    )

    report = score_attempt(task, attempt)

    assert report["score"] == 1.0
    assert report["parts"]["safety"] == 1.0


def test_jsonl_runner_outputs_summary_and_restart_counts(tmp_path):
    path = tmp_path / "stages.jsonl"
    path.write_text(
        '{"task":{"stage_id":"math1","domain":"mathematics","prompt":"2+2","expected_answer":"4",'
        '"required_process_tokens":["2+2"],"units":"number"},'
        '"attempt":{"text":"ANSWER: 4\\nPROCESS: 2+2=4\\nCHECK: ok\\nUNITS: number\\nCONFIDENCE: high",'
        '"elapsed_seconds":90,"context_used_tokens":100}}\n'
        '{"task":{"stage_id":"math2","domain":"mathematics","prompt":"2+3","expected_answer":"5",'
        '"checkpoint_id":"math2_start"},'
        '"attempt":{"text":"ANSWER: 8","elapsed_seconds":1,"context_used_tokens":4000}}\n',
        encoding="utf-8",
    )

    report = run_jsonl(str(path))

    assert report["summary"]["attempted"] == 2
    assert report["summary"]["restart_count"] == 1
    assert len(report["sft"]) == 2
