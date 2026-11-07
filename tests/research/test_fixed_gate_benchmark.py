from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "research" / "gated-sidecar-routing-20261107" / "fixed_gate_benchmark.py"
BENCHMARK_PATH = MODULE_PATH.with_name("false_route_benchmark_v1.json")
PIN_PATH = MODULE_PATH.with_name("FALSE_ROUTE_BENCHMARK_PIN.json")


def _load_module():
    spec = importlib.util.spec_from_file_location("fixed_gate_benchmark", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_false_route_contract_passes() -> None:
    module = _load_module()
    receipt = module.evaluate_benchmark(BENCHMARK_PATH)

    assert receipt["status"] == "PASS"
    assert receipt["case_count"] == 54
    assert receipt["ordinary_prompt_count"] == 30
    assert receipt["false_specialist_routes"] == 0
    assert receipt["false_route_rate"] == 0.0
    assert receipt["specialist_route_recall"] == 1.0
    assert receipt["promotion"] == "NOT_AUTHORIZED"
    assert receipt["training_intake"] == "NOT_AUTHORIZED"


def test_frozen_files_match_preimplementation_pin() -> None:
    module = _load_module()
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))

    assert module.sha256_file(BENCHMARK_PATH) == pin["benchmark_sha256"]
    assert module.sha256_file(MODULE_PATH) == pin["evaluator_sha256"]
    assert pin["promotion"] == "NOT_AUTHORIZED"
    assert pin["training_intake"] == "NOT_AUTHORIZED"


def test_lexical_traps_never_request_the_specialist() -> None:
    module = _load_module()
    for prompt in (
        "Write Python code",
        "Debug this function",
        "Compile a source list",
        "A specialist should inspect the adapter weights",
    ):
        decision, reason = module.fixed_gate({"prompt": prompt})
        assert decision == "CORE_PASS"
        assert reason == "CAPABILITY_NOT_REQUESTED"


def test_explicit_but_untrusted_request_abstains() -> None:
    module = _load_module()
    decision, reason = module.fixed_gate(
        {
            "capability_id": "clay.coding.v1",
            "request_explicit": True,
            "provenance_verified": False,
            "source_kind": "source_code",
            "requested_output_schema": "typed_action_candidates.v1",
            "specialist_available": True,
            "capacity_available": True,
        }
    )
    assert decision == "ABSTAIN"
    assert reason == "PROVENANCE_UNVERIFIED"


def test_valid_typed_request_routes_without_reading_prompt_text() -> None:
    module = _load_module()
    envelope = {
        "capability_id": "clay.coding.v1",
        "request_explicit": True,
        "provenance_verified": True,
        "source_kind": "source_code",
        "requested_output_schema": "typed_action_candidates.v1",
        "specialist_available": True,
        "capacity_available": True,
    }
    assert module.fixed_gate(envelope) == ("SPECIALIST", "ELIGIBLE")
