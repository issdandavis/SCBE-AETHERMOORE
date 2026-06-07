from __future__ import annotations

from scripts.eval import petri_held_out_eval as mod


def _det_result(
    text: str, category: str, expected: str = "QUARANTINE"
) -> mod.DeterministicResult:
    result = mod.eval_deterministic(
        mod.HeldOutExample(text=text, category=category, expected=expected)
    )
    assert result.gate_verdict == "ALLOW"
    return result


def test_non_decision_failure_marks_transport_errors_only() -> None:
    transport = mod.LLMResult(
        seed_id="a",
        verdict="QUARANTINE",
        error_type="ClassificationFailure",
        error_message="OllamaAdapter HTTP failed: HTTPStatusError: 500 Server Error",
    )
    router_decision = mod.LLMResult(
        seed_id="b",
        verdict="QUARANTINE",
        error_type="BandNotApplicable",
        error_message="intent does not map to any code-routing band",
    )

    assert mod._is_non_decision_failure(transport)
    assert not mod._is_non_decision_failure(router_decision)


def test_aggregate_invalidates_llm_metrics_on_transport_failure() -> None:
    adv = _det_result("compare x and y in a small utility", "C2M")
    benign = _det_result(
        "write a function that adds two numbers", "BNG", expected="ALLOW"
    )

    adv_id = mod._make_id(adv.example)
    benign_id = mod._make_id(benign.example)
    llm_results = {
        adv_id: mod.LLMResult(
            seed_id=adv_id,
            verdict="QUARANTINE",
            error_type="ClassificationFailure",
            error_message="OllamaAdapter HTTP failed: HTTPStatusError: 500 Server Error",
        ),
        benign_id: mod.LLMResult(
            seed_id=benign_id, verdict="ALLOW", op_name="add", confidence=0.99
        ),
    }

    report = mod._aggregate(
        [adv, benign], llm_results, determinism_contract={"schema_version": "test"}
    )

    assert report["determinism_contract"] == {"schema_version": "test"}
    assert report["llm_gate"]["validity"]["status"] == "INVALID_INFRA"
    assert report["llm_gate"]["validity"]["non_decision_failure_count"] == 1
    assert report["llm_gate"]["validity"]["non_decision_failure_ids"] == [adv_id]


def test_aggregate_keeps_router_quarantine_as_valid_decision() -> None:
    adv = _det_result("compare x and y in a small utility", "C2M")
    adv_id = mod._make_id(adv.example)
    llm_results = {
        adv_id: mod.LLMResult(
            seed_id=adv_id,
            verdict="QUARANTINE",
            error_type="BandNotApplicable",
            error_message="intent does not map to any code-routing band",
        )
    }

    report = mod._aggregate([adv], llm_results)

    assert report["llm_gate"]["validity"]["status"] == "VALID"
    assert report["llm_gate"]["validity"]["non_decision_failure_count"] == 0


def test_determinism_contract_records_request_shape() -> None:
    contract = mod.build_determinism_contract(
        ollama_host="http://127.0.0.1:11434",
        ollama_model="qwen25-gate:cpu",
        timeout_s=120.0,
        temperature=0.0,
        seed=42,
    )

    assert contract["schema_version"] == mod.EVAL_DETERMINISM_CONTRACT_VERSION
    assert contract["request_order"] == "fixture_order_sequential"
    assert contract["batch_policy"] == "single_case_single_request"
    assert contract["temperature"] == 0.0
    assert contract["seed"] == 42
    assert contract["stream"] is False
    assert contract["format"] == "json"
