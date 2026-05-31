"""Tests for the BFCL tool-call adapter (offline / export-only lane).

These tests run without Ollama or any API key. They verify:
- All 54 tools are exported as OpenAI function-calling schemas (BFCL-adjacent format)
- AST validation passes 100%
- Multi-param and no-param tools are exported correctly
- Irrelevance test cases produce ground_truth_tool = None
- Receipt chaining produces distinct hashes

Model eval (the Groq/Cerebras lane) is NOT tested here — it requires live
credentials and is exercised by running the script directly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.benchmark.bfcl_tool_call_adapter import (
    TEST_CASES,
    _extract_params,
    _make_receipt,
    _same_namespace,
    tools_to_bfcl_schemas,
    validate_all_schemas,
    validate_bfcl_schema,
)

TOOLS_JSON = ROOT / "packages" / "agent-bus" / "tools.json"


# ── Schema export ──────────────────────────────────────────────────────────────

def test_export_count():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    assert len(schemas) == 54, f"expected 54 tools, got {len(schemas)}"


def test_ast_validation_all_pass():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    result = validate_all_schemas(schemas)
    assert result["failed"] == 0, f"AST failures: {result['failures']}"
    assert result["pass_rate"] == 1.0


def test_schema_shape_single_param():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    arxiv = next(s for s in schemas if s["name"] == "research-arxiv")
    assert arxiv["parameters"]["type"] == "object"
    assert "task" in arxiv["parameters"]["properties"]
    assert arxiv["parameters"]["required"] == ["task"]


def test_schema_shape_multi_param():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    agentbus = next(s for s in schemas if s["name"] == "scbe-agentbus")
    props = agentbus["parameters"]["properties"]
    assert "task" in props
    assert "taskType" in props
    assert "seriesId" in props
    assert "privacy" in props
    required = agentbus["parameters"]["required"]
    assert set(required) == {"task", "taskType", "seriesId", "privacy"}


def test_schema_shape_no_param():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    antivirus = next(s for s in schemas if s["name"] == "scbe-antivirus")
    assert antivirus["parameters"]["properties"] == {}
    assert antivirus["parameters"]["required"] == []


def test_reporoot_excluded_from_required():
    """repoRoot is a bus-substituted variable, never caller-supplied."""
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    for schema in schemas:
        assert "repoRoot" not in schema["parameters"]["required"], (
            f"{schema['name']} has repoRoot in required"
        )


def test_all_schemas_have_description():
    schemas = tools_to_bfcl_schemas(TOOLS_JSON)
    missing = [s["name"] for s in schemas if not s.get("description")]
    assert not missing, f"tools with empty description: {missing}"


# ── Param extraction ───────────────────────────────────────────────────────────

def test_extract_params_single():
    assert _extract_params(["-m", "module", "{task}"]) == ["task"]


def test_extract_params_multi():
    params = _extract_params(["--task", "{task}", "--type", "{taskType}", "--id", "{seriesId}"])
    assert params == ["task", "taskType", "seriesId"]


def test_extract_params_empty():
    assert _extract_params(["--self-check"]) == []


def test_extract_params_deduplicated():
    # {task} appears twice but should only appear once in output
    params = _extract_params(["{task}", "--also", "{task}"])
    assert params == ["task"]


# ── AST validator ──────────────────────────────────────────────────────────────

def test_validate_good_schema():
    schema = {
        "name": "my-tool",
        "description": "Does something",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "a query"}},
            "required": ["query"],
        },
    }
    result = validate_bfcl_schema(schema)
    assert result.ok
    assert result.errors == []


def test_validate_missing_name():
    schema = {
        "description": "d",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }
    result = validate_bfcl_schema(schema)
    assert not result.ok
    assert any("name" in e for e in result.errors)


def test_validate_wrong_parameters_type():
    schema = {
        "name": "t",
        "description": "d",
        "parameters": {"type": "array", "properties": {}, "required": []},
    }
    result = validate_bfcl_schema(schema)
    assert not result.ok


def test_validate_required_not_in_properties():
    schema = {
        "name": "t",
        "description": "d",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": ["missing_param"],
        },
    }
    result = validate_bfcl_schema(schema)
    assert not result.ok
    assert any("missing_param" in e for e in result.errors)


# ── Test cases ─────────────────────────────────────────────────────────────────

def test_test_cases_have_required_fields():
    for case in TEST_CASES:
        assert "id" in case
        assert "question" in case
        assert "ground_truth_tool" in case
        assert "ground_truth_args" in case
        assert "category" in case


def test_irrelevance_cases_have_none_tool():
    irrelevance = [c for c in TEST_CASES if c["category"] == "irrelevance"]
    assert len(irrelevance) >= 2, "need at least 2 irrelevance cases"
    for case in irrelevance:
        assert case["ground_truth_tool"] is None, (
            f"{case['id']} is tagged irrelevance but has a non-None ground_truth_tool"
        )


def test_no_duplicate_case_ids():
    ids = [c["id"] for c in TEST_CASES]
    assert len(ids) == len(set(ids)), "duplicate test case IDs"


def test_question_does_not_restate_tool_name():
    """A case whose question literally contains its expected tool name is tautological."""
    tools = {c["ground_truth_tool"] for c in TEST_CASES if c["ground_truth_tool"]}
    for case in TEST_CASES:
        expected = case["ground_truth_tool"]
        if expected is None:
            continue
        assert expected not in case["question"], (
            f"{case['id']} question contains the tool name '{expected}' verbatim — "
            "this is a tautological test case"
        )


# ── Receipt chaining ───────────────────────────────────────────────────────────

def test_receipt_is_deterministic():
    ts = "2026-01-01T00:00:00Z"
    prev = "0" * 64
    r1 = _make_receipt("tc_01", "q", "geoseal-compile", "geoseal-compile",
                        {"task": "t"}, True, prev, ts)
    r2 = _make_receipt("tc_01", "q", "geoseal-compile", "geoseal-compile",
                        {"task": "t"}, True, prev, ts)
    assert r1["receipt_hash"] == r2["receipt_hash"]


def test_receipt_hash_changes_on_different_tool():
    ts = "2026-01-01T00:00:00Z"
    prev = "0" * 64
    r1 = _make_receipt("tc_01", "q", "tool-a", "tool-a", {}, True, prev, ts)
    r2 = _make_receipt("tc_01", "q", "tool-b", "tool-b", {}, True, prev, ts)
    assert r1["receipt_hash"] != r2["receipt_hash"]


def test_receipt_chain_links():
    ts = "2026-01-01T00:00:00Z"
    prev = "0" * 64
    r1 = _make_receipt("tc_01", "q1", "a", "a", {}, True, prev, ts)
    r2 = _make_receipt("tc_02", "q2", "b", "b", {}, True, r1["receipt_hash"], ts)
    assert r2["prev_hash"] == r1["receipt_hash"]
    assert r2["receipt_hash"] != r1["receipt_hash"]


def test_receipt_hash_is_sha256_length():
    ts = "2026-01-01T00:00:00Z"
    r = _make_receipt("tc_01", "q", "a", "a", {}, True, "0" * 64, ts)
    assert len(r["receipt_hash"]) == 64


def test_receipt_near_miss_field_present():
    ts = "2026-01-01T00:00:00Z"
    r = _make_receipt("tc_01", "q", "geoseal-compile", "geoseal-seal", {}, False,
                      "0" * 64, ts, near_miss=True)
    assert r["near_miss"] is True


def test_receipt_near_miss_default_false():
    ts = "2026-01-01T00:00:00Z"
    r = _make_receipt("tc_01", "q", "geoseal-compile", "geoseal-compile", {}, True,
                      "0" * 64, ts)
    assert r["near_miss"] is False


# ── Near-miss namespace detection ─────────────────────────────────────────────

def test_same_namespace_true():
    assert _same_namespace("geoseal-compile", "geoseal-seal") is True


def test_same_namespace_false():
    assert _same_namespace("geoseal-compile", "scbe-compass") is False


def test_same_namespace_research():
    assert _same_namespace("research-arxiv", "research-uspto") is True


def test_same_namespace_single_segment():
    # Tools with no hyphen — each is its own namespace
    assert _same_namespace("mytools", "mytools") is True
    assert _same_namespace("toolA", "toolB") is False
