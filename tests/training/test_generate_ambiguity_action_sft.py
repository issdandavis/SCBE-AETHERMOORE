from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "training" / "generate_ambiguity_action_sft.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_ambiguity_action_sft", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


@pytest.fixture(scope="module")
def pairs(generator):
    return generator.generate_pairs()


def test_pairs_are_non_empty_and_json_only(pairs) -> None:
    assert pairs
    for pair in pairs:
        assert pair["category"] == "ambiguity-to-action-trace"
        payload = json.loads(pair["response"])
        assert payload["schema_version"] == "ambiguity_action_trace_v1"
        assert payload["simulation_only"] is True


def test_every_record_has_repo_grounding_and_actionable_plan(pairs) -> None:
    for pair in pairs:
        payload = json.loads(pair["response"])
        assert payload["repo_grounding"]["paths"]
        assert payload["repo_grounding"]["test_command"]
        assert payload["grounded_actions"]
        assert payload["inferred_purpose"]


def test_clarity_gate_is_explicit_and_not_always_ask(pairs) -> None:
    gates = [json.loads(pair["response"])["clarity_gate"] for pair in pairs]

    assert any(gate["ask_user"] is True for gate in gates)
    assert any(gate["ask_user"] is False for gate in gates)
    for gate in gates:
        assert gate["reason"]
        assert gate["ask_if"]


def test_delegation_uses_small_packet_shadow_not_full_task_body(pairs) -> None:
    for pair in pairs:
        payload = json.loads(pair["response"])
        for delegation in payload["delegation"]:
            shadow = delegation["packet_shadow"]
            assert shadow["schema"] == "agent_handoff_shadow_v1"
            assert shadow["body_commitment"].startswith("sha256:")
            assert "request" not in shadow
            assert delegation["decode_agreement"]["key_lifecycle"] == "derive-use-discard"
            assert delegation["success_gate"]


def test_mini_skills_are_tiny_and_composable(pairs) -> None:
    seen = set()
    for pair in pairs:
        payload = json.loads(pair["response"])
        for skill in payload["mini_skills"]:
            seen.add(skill["skill_id"])
            assert skill["load_cost"] == 1
            assert skill["trigger"]
            assert skill["action"]
            assert skill["improves"]
    assert {
        "repo-first-grounding",
        "context-bloat-triage",
        "small-packet-delegation",
        "residual-temp-skill-propagation",
    }.issubset(seen)


def test_residual_lifecycle_keeps_manifest_not_temp_body(pairs) -> None:
    payloads = [json.loads(pair["response"]) for pair in pairs]
    residual = [payload for payload in payloads if payload["scenario_id"] == "residual_deletion_skill_trace"]
    assert residual, "residual deletion scenario must be present"

    lifecycle = residual[0]["residual_lifecycle"]
    assert lifecycle["schema_version"] == "residual_temp_skill_lifecycle_v1"
    assert lifecycle["temp_artifact"]["status"] == "delete_after_use"
    assert lifecycle["residue_manifest"]["status"] == "retain_if_safe"
    assert lifecycle["residue_manifest"]["retained_fraction_goal"] == 0.03
    assert lifecycle["residue_manifest"]["source_commitment"].startswith("sha256:")
    assert "does not update model weights" in lifecycle["weight_space_note"]


def test_generator_is_byte_deterministic(generator, tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    generator.write_jsonl(generator.generate_pairs(), a)
    generator.write_jsonl(generator.generate_pairs(), b)

    assert a.read_bytes() == b.read_bytes()


def test_script_writes_output(generator, tmp_path: Path) -> None:
    output = tmp_path / "ambiguity.jsonl"
    rc = generator.main(["--output", str(output), "--json"])

    assert rc == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(generator.generate_pairs())
