from python.helm import reference_bank
from python.helm.domain_router import solve_routed

ADD_PROMPT = "Write a function add(a, b) that returns the sum."
ADD_TESTS = ["assert add(2, 2) == 4", "assert add(-1, 3) == 2", "assert add(5, 7) == 12"]
ADD_REF = "def add(a, b):\n    return a + b\n"


def test_arrow_hint_retry_reasks_with_failure_context():
    prompts = []
    outputs = iter(["def add(a, b):\n    return a * b\n", "def add(a, b):\n    return a + b\n"])

    def ask(prompt):
        prompts.append(prompt)
        return next(outputs)

    result = solve_routed(ADD_PROMPT, ADD_TESTS[:1], ADD_TESTS[1:], ask, max_attempts=2, arrow_hint=True)

    assert result["status"] == "VERIFIED_FIX"
    assert result["via"].startswith("routed:")
    assert result["attempts"] == 2
    assert result["repair_attempts"][0]["passed"] is False
    assert result["repair_attempts"][1]["passed"] is True
    assert len(prompts) == 2
    assert "REPAIR ARROW 1" in prompts[1]
    assert result["false_success_count"] == 0


def test_auto_bank_writes_only_after_hidden_and_fuzz_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(reference_bank, "BANK", str(tmp_path / "reference_bank.jsonl"))

    def ask(_prompt):
        return "def add(a, b):\n    return b + a\n"

    result = solve_routed(
        ADD_PROMPT,
        ADD_TESTS[:1],
        ADD_TESTS[1:],
        ask,
        reference=ADD_REF,
        task_id="auto_add",
        auto_bank=True,
        auto_bank_require_fuzz=True,
    )

    assert result["status"] == "VERIFIED_FIX"
    assert result["auto_bank"]["banked"] is True
    assert result["auto_bank"]["fuzz_verdict"] == "trust"
    assert reference_bank.get("auto_add").startswith("def add")


def test_auto_bank_refuses_hidden_only_when_fuzz_required(tmp_path, monkeypatch):
    monkeypatch.setattr(reference_bank, "BANK", str(tmp_path / "reference_bank.jsonl"))

    def ask(_prompt):
        return "def add(a, b):\n    return a + b\n"

    result = solve_routed(
        ADD_PROMPT,
        ADD_TESTS[:1],
        ADD_TESTS[1:],
        ask,
        task_id="no_ref_add",
        auto_bank=True,
        auto_bank_require_fuzz=True,
    )

    assert result["status"] == "VERIFIED_FIX"
    assert result["auto_bank"]["banked"] is False
    assert result["auto_bank"]["fuzz_verdict"] == "unavailable"
    assert reference_bank.get("no_ref_add") is None
