from python.helm.system_coding_contract import (
    ESCALATE,
    VERIFIED_FIX,
    FixAttempt,
    evaluate_fix_candidates,
    score_decisions,
)

REFERENCE_ADD = "def add(a, b):\n    return a + b\n"
VISIBLE_ADD_TESTS = ["assert add(2, 2) == 4"]


def test_system_coding_contract_trusts_equivalent_refactor():
    decision = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[FixAttempt("commuted_add", "def add(a, b):\n    return b + a\n")],
        tests=VISIBLE_ADD_TESTS,
    )

    assert decision["status"] == VERIFIED_FIX
    assert decision["selected"] == "commuted_add"
    assert decision["code_fixed"] is True
    assert decision["false_success_count"] == 0


def test_system_coding_contract_rejects_visible_pass_wrong_patch():
    decision = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[FixAttempt("multiply_overfit", "def add(a, b):\n    return a * b\n")],
        tests=VISIBLE_ADD_TESTS,
    )

    assert decision["status"] == ESCALATE
    assert decision["selected"] is None
    assert decision["code_fixed"] is False
    assert decision["attempts"][0]["verdict"] == "reject"
    assert "DIVERGES" in decision["attempts"][0]["reason"]


def test_system_coding_contract_falls_through_to_later_verified_candidate():
    decision = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[
            FixAttempt("multiply_overfit", "def add(a, b):\n    return a * b\n"),
            FixAttempt("commuted_add", "def add(a, b):\n    return b + a\n"),
        ],
        tests=VISIBLE_ADD_TESTS,
    )

    assert decision["status"] == VERIFIED_FIX
    assert decision["selected"] == "commuted_add"
    assert [a["verdict"] for a in decision["attempts"]] == ["reject", "trust"]


def test_system_coding_contract_escalates_when_fuzz_oracle_is_insufficient():
    decision = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[FixAttempt("same_code", REFERENCE_ADD)],
        tests=["assert True"],
    )

    assert decision["status"] == ESCALATE
    assert decision["attempts"][0]["verdict"] == "abstain"
    assert "cannot synthesize" in decision["attempts"][0]["reason"]


def test_system_coding_contract_scores_verified_and_escalated_as_closed_not_fake_success():
    fixed = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[FixAttempt("commuted_add", "def add(a, b):\n    return b + a\n")],
        tests=VISIBLE_ADD_TESTS,
    )
    escalated = evaluate_fix_candidates(
        reference=REFERENCE_ADD,
        candidates=[FixAttempt("multiply_overfit", "def add(a, b):\n    return a * b\n")],
        tests=VISIBLE_ADD_TESTS,
    )

    score = score_decisions([fixed, escalated])

    assert score["attempted"] == 2
    assert score["verified_fix"] == 1
    assert score["escalated"] == 1
    assert score["rejected_candidates"] == 1
    assert score["false_success_count"] == 0
    assert score["code_fix_success_rate"] == 0.5
    assert score["operational_closure_rate"] == 1.0
    assert score["contract_passed"] is True
