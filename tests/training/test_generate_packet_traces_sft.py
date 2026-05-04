"""Tests for ``scripts/training/generate_packet_traces_sft.py``.

Replaces the old prose-style agentic SFT generator with executable
packet-graph traces. These tests guard the runtime contract:

  - every ``response`` field is valid JSON (never prose)
  - every ``agentic-merge-verdict`` response is a real MergeReport with
    a valid decision and ``channel:value`` evidence tags
  - every ``agentic-packet-trace`` response is a real GraphRunResult
  - generation is byte-deterministic across runs
  - ``metadata.packet_fingerprint`` matches a freshly recomputed
    fingerprint of the seed packet (proves provenance)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "training" / "generate_packet_traces_sft.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_packet_traces_sft", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


@pytest.fixture(scope="module")
def pairs(generator):
    return generator.generate_pairs()


# ---------------------------------------------------------------------------
# Shape — every pair has the SFT envelope and the response is JSON
# ---------------------------------------------------------------------------


def test_pairs_are_non_empty(pairs):
    assert len(pairs) > 0, "generator must emit at least one pair"


def test_every_pair_has_sft_envelope(pairs):
    required = {"id", "category", "instruction", "response", "metadata"}
    for pair in pairs:
        missing = required - set(pair)
        assert not missing, f"pair {pair.get('id')!r} missing keys: {missing}"


def test_every_response_is_valid_json(pairs):
    for pair in pairs:
        try:
            json.loads(pair["response"])
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"pair {pair['id']!r} response is not JSON: {exc.msg}; "
                f"got first 80 chars: {pair['response'][:80]!r}"
            )


def test_every_pair_id_is_unique(pairs):
    ids = [p["id"] for p in pairs]
    assert len(ids) == len(set(ids)), "pair ids must be unique"


# ---------------------------------------------------------------------------
# Categories — both pair categories must be present
# ---------------------------------------------------------------------------


def test_both_categories_emitted(pairs):
    categories = {p["category"] for p in pairs}
    assert "agentic-merge-verdict" in categories
    assert "agentic-packet-trace" in categories


def test_no_unexpected_categories(pairs):
    expected = {"agentic-merge-verdict", "agentic-packet-trace"}
    actual = {p["category"] for p in pairs}
    extra = actual - expected
    assert not extra, f"unexpected categories: {extra}"


# ---------------------------------------------------------------------------
# MergeReport contract — verdict pairs must look like real MergeReports
# ---------------------------------------------------------------------------


def test_merge_verdicts_have_valid_decision(pairs, generator):
    from src.agent_comms.packet import VALID_DECISIONS

    verdicts = [p for p in pairs if p["category"] == "agentic-merge-verdict"]
    assert len(verdicts) > 0
    for pair in verdicts:
        report = json.loads(pair["response"])
        assert report.get("decision") in VALID_DECISIONS, (
            f"verdict {pair['id']!r} decision {report.get('decision')!r} " f"not in {VALID_DECISIONS}"
        )


def test_merge_verdicts_have_channel_value_tags(pairs):
    verdicts = [p for p in pairs if p["category"] == "agentic-merge-verdict"]
    for pair in verdicts:
        report = json.loads(pair["response"])
        for tag in report.get("evidence", []) + report.get("contact_points", []):
            assert isinstance(tag, str) and ":" in tag, f"tag {tag!r} in verdict {pair['id']!r} must be 'channel:value'"


def test_merge_verdicts_carry_task_id(pairs):
    verdicts = [p for p in pairs if p["category"] == "agentic-merge-verdict"]
    for pair in verdicts:
        report = json.loads(pair["response"])
        assert report.get("task_id") == pair["metadata"]["task_id"], (
            f"verdict {pair['id']!r} task_id mismatch: "
            f"report={report.get('task_id')!r} meta={pair['metadata']['task_id']!r}"
        )


def test_merge_verdicts_have_no_created_at_clock(pairs):
    """``created_at`` is stripped — otherwise every run produces fresh bytes."""

    verdicts = [p for p in pairs if p["category"] == "agentic-merge-verdict"]
    for pair in verdicts:
        report = json.loads(pair["response"])
        assert "created_at" not in report, f"verdict {pair['id']!r} still carries created_at clock"


# ---------------------------------------------------------------------------
# GraphRunResult contract — trace pairs must look like real run results
# ---------------------------------------------------------------------------


def test_traces_have_run_result_fields(pairs):
    traces = [p for p in pairs if p["category"] == "agentic-packet-trace"]
    assert len(traces) > 0
    required = {
        "schema_version",
        "graph_id",
        "task_id",
        "start_node",
        "final_node",
        "final_decision",
        "checkpoints",
        "path",
        "halted_reason",
    }
    for pair in traces:
        result = json.loads(pair["response"])
        missing = required - set(result)
        assert not missing, f"trace {pair['id']!r} missing fields: {missing}"


def test_traces_checkpoints_are_non_empty(pairs):
    traces = [p for p in pairs if p["category"] == "agentic-packet-trace"]
    for pair in traces:
        result = json.loads(pair["response"])
        assert len(result["checkpoints"]) > 0, f"trace {pair['id']!r} has no checkpoints — graph never executed"


def test_traces_use_runner_schema_version(pairs):
    from src.agent_comms.graph_runner import SCHEMA_VERSION

    traces = [p for p in pairs if p["category"] == "agentic-packet-trace"]
    for pair in traces:
        result = json.loads(pair["response"])
        assert result["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Provenance — fingerprint must round-trip from a real seed packet
# ---------------------------------------------------------------------------


def test_verdict_fingerprint_matches_seed(pairs, generator):
    verdicts = [p for p in pairs if p["category"] == "agentic-merge-verdict"]
    for pair in verdicts:
        recomputed = generator.recompute_fingerprint_from_metadata(pair["metadata"])
        assert recomputed is not None, f"verdict {pair['id']!r} task_id is not in the seed corpus"
        assert recomputed == pair["metadata"]["packet_fingerprint"], (
            f"verdict {pair['id']!r} fingerprint drift: "
            f"meta={pair['metadata']['packet_fingerprint']!r} "
            f"recomputed={recomputed!r}"
        )


# ---------------------------------------------------------------------------
# Determinism — two runs must produce byte-identical JSONL
# ---------------------------------------------------------------------------


def test_jsonl_is_byte_deterministic(generator, tmp_path):
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    generator.write_jsonl(generator.generate_pairs(), out_a)
    generator.write_jsonl(generator.generate_pairs(), out_b)
    assert (
        out_a.read_bytes() == out_b.read_bytes()
    ), "two generator runs produced different bytes — non-determinism leak"


# ---------------------------------------------------------------------------
# Anti-prose guard — explicit defense against the slack we are fixing
# ---------------------------------------------------------------------------


def test_no_fabricated_tool_call_prose(pairs):
    """Catch the exact slack-4 patterns the old generator produced.

    The old ``generate_agentic_sft.py`` emitted strings like::

        <tool_call>{"name": "X", "args": {"param": "value"}}</tool_call>
        <tool_result>Success: operation completed.</tool_result>

    None of those tokens may appear in the executable-trace SFT.
    """

    forbidden = (
        "<tool_call>",
        "<tool_result>",
        "<apply_diff>",
        "<verify>",
        "<read_file>",
        "Success: operation completed.",
        '"param": "value"',
    )
    for pair in pairs:
        for token in forbidden:
            assert token not in pair["response"], (
                f"pair {pair['id']!r} response contains forbidden prose token " f"{token!r}"
            )
            assert token not in pair["instruction"], (
                f"pair {pair['id']!r} instruction contains forbidden prose token " f"{token!r}"
            )
