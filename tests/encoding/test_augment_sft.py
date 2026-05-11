"""Tests for scripts/encoding/augment_sft_with_dense_bundle.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "encoding" / "augment_sft_with_dense_bundle.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_augment_sft_with_dense_bundle", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aug():
    return _load_module()


# ---------------------------------------------------------------------------
# Pure record augmentation
# ---------------------------------------------------------------------------


def test_augments_user_turn(aug) -> None:
    record = {
        "id": "rec-1",
        "messages": [
            {"role": "system", "content": "you are an agent"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    }
    out = aug.augment_record(record)
    bundle = out["dense_bundle"]
    assert bundle["target"] == "user"
    assert bundle["default_view"] == "hex"
    assert bundle["byte_length"] == 5  # len(b"hello")
    assert bundle["views"]["hex"] == "68656c6c6f"
    assert bundle["intent_profile"]["pos"] == 1.0  # all low ASCII
    assert bundle["route_lane"] == "binary_analysis"


def test_does_not_mutate_input(aug) -> None:
    record = {"messages": [{"role": "user", "content": "x"}]}
    snapshot = json.dumps(record, sort_keys=True)
    aug.augment_record(record)
    assert json.dumps(record, sort_keys=True) == snapshot


def test_skips_when_target_missing(aug) -> None:
    record = {"messages": [{"role": "system", "content": "x"}]}
    out = aug.augment_record(record, target="user")
    assert "dense_bundle" not in out


def test_skips_empty_target_content(aug) -> None:
    record = {"messages": [{"role": "user", "content": ""}]}
    out = aug.augment_record(record, target="user")
    assert "dense_bundle" not in out


def test_target_can_be_assistant(aug) -> None:
    record = {
        "messages": [
            {"role": "user", "content": "ask"},
            {"role": "assistant", "content": "answer"},
        ]
    }
    out = aug.augment_record(record, target="assistant")
    assert out["dense_bundle"]["byte_length"] == 6  # len("answer")


def test_default_view_changes_route_lane(aug) -> None:
    record = {"messages": [{"role": "user", "content": "x"}]}
    out_hex = aug.augment_record(record, default_view="hex")
    out_ternary = aug.augment_record(record, default_view="ternary")
    assert out_hex["dense_bundle"]["route_lane"] == "binary_analysis"
    assert out_ternary["dense_bundle"]["route_lane"] == "governance_intent"


def test_handles_multipart_content(aug) -> None:
    record = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]}
        ]
    }
    out = aug.augment_record(record)
    assert out["dense_bundle"]["byte_length"] == 11  # "hello world"


# ---------------------------------------------------------------------------
# CLI / file round-trip
# ---------------------------------------------------------------------------


def test_cli_round_trip(tmp_path, aug) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    rows = [
        {"messages": [{"role": "user", "content": "abc"}]},
        {"messages": [{"role": "user", "content": "def"}]},
        {"messages": [{"role": "system", "content": "no user turn"}]},  # passes through unchanged
    ]
    inp.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    rc = aug.main([str(inp), str(out)])
    assert rc == 0

    written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(written) == 3
    assert "dense_bundle" in written[0]
    assert "dense_bundle" in written[1]
    assert "dense_bundle" not in written[2]


def test_cli_missing_input_exits_2(aug, tmp_path) -> None:
    out = tmp_path / "out.jsonl"
    rc = aug.main([str(tmp_path / "nope.jsonl"), str(out)])
    assert rc == 2


def test_cli_skips_blank_lines(tmp_path, aug) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    inp.write_text(
        "\n".join(
            [
                json.dumps({"messages": [{"role": "user", "content": "a"}]}),
                "",
                "   ",
                json.dumps({"messages": [{"role": "user", "content": "b"}]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rc = aug.main([str(inp), str(out)])
    assert rc == 0
    written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(written) == 2
