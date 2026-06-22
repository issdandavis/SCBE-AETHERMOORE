from python.helm.agent_solve import agent_solve
from python.helm.domain_router import solve_routed
from python.helm.reference_bank import get as get_reference

PF_MEDIAN_PROMPT = (
    "Write a function median(nums) that returns the median of a list of numbers without mutating the input."
)

PF_MEDIAN_TESTS = [
    "assert median([3, 1, 2]) == 2",
    "assert median([1, 2, 3, 4]) == 2.5",
    "data = [9, 1, 5, 3]\nassert median(data) == 4.0\nassert data == [9, 1, 5, 3]",
]


def bad_model(_prompt: str) -> str:
    return "def median(nums):\n    return 0\n"


def test_domain_router_uses_reference_bank_automatically_after_model_miss():
    assert get_reference("pf_median") is not None

    result = solve_routed(
        PF_MEDIAN_PROMPT,
        PF_MEDIAN_TESTS[:1],
        PF_MEDIAN_TESTS,
        bad_model,
        task_id="pf_median",
    )

    assert result["status"] == "VERIFIED_FIX"
    assert result["via"] == "fallback:reference_bank"
    assert result["false_success_count"] == 0
    assert "def median" in result["code"]


def test_agent_solve_passes_task_id_to_reference_bank_live_loop():
    result = agent_solve(
        PF_MEDIAN_PROMPT,
        ask=bad_model,
        tests=PF_MEDIAN_TESTS,
        task_id="pf_median",
    )

    assert result["status"] == "VERIFIED_FIX"
    assert result["via"] == "fallback:reference_bank"
    assert result["false_success_count"] == 0


def test_unbanked_failed_code_task_escalates_instead_of_fake_success():
    result = agent_solve(
        PF_MEDIAN_PROMPT,
        ask=bad_model,
        tests=PF_MEDIAN_TESTS,
        task_id="not_in_bank",
    )

    assert result["status"] == "ESCALATE"
    assert result["false_success_count"] == 0
