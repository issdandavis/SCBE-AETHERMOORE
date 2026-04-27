from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "operator_agent_bus_eval.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("operator_agent_bus_eval_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(tags: list[str], assistant: dict) -> dict:
    return {
        "messages": [
            {"role": "user", "content": "prompt"},
            {"role": "assistant", "content": json.dumps(assistant)},
        ],
        "metadata": {
            "tags": tags,
            "source_path": "source.json",
            "dedupe_key": "abc",
        },
    }


def test_score_eval_record_requires_cross_talk_fields() -> None:
    module = _load_module()
    row = _row(
        ["cross_talk", "agent_bus"],
        {
            "intent": "claim_worker",
            "next_action": "Launch worker.",
            "risk": "low",
            "status": "in_progress",
            "ledger": {"channel": "cross_talk"},
            "proof": ["notebook.ipynb"],
            "layer14": {"stability": 1.0},
        },
    )

    score = module.score_eval_record(row)

    assert score["ok"] is True
    assert score["score"] == 1.0
    assert score["checks"]["has_ledger"] is True


def test_score_eval_record_blocks_shell_command_payload() -> None:
    module = _load_module()
    row = _row(["workflow_eval"], {"status": True, "source_type": "workflow_artifact", "shell_command": "rm -rf ."})

    score = module.score_eval_record(row)

    assert score["ok"] is False
    assert score["checks"]["no_execution_command"] is False


def test_score_endpoint_result_requires_artifacts(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_path_exists", lambda value: bool(value))
    result = {
        "task": {"task_id": "coding", "prompt": "raw prompt"},
        "returncode": 0,
        "duration_ms": 10,
        "payload": {
            "schema_version": "scbe_agentbus_user_run_v1",
            "selected_provider": "offline",
            "privacy": "local_only",
            "budget_cents": 0,
            "dispatch": {"enabled": True, "event_id": "evt"},
            "operation_shape": {
                "root_value": 12026,
                "signature_hex": "abc",
                "floating_point_policy": "forbidden for consensus signatures",
            },
            "artifacts": {
                "latest_round": "round.json",
                "watcher": "watcher.json",
                "summary": "summary.json",
            },
        },
    }

    score = module.score_endpoint_result(result)

    assert score["ok"] is True
    assert score["score"] == 1.0


def test_build_report_can_run_dataset_only(tmp_path: Path) -> None:
    module = _load_module()
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(
        json.dumps(
            _row(
                ["route_gate", "agent_bus"],
                {
                    "decision": "allow",
                    "commitment_status": "ready",
                    "proof_status": "PASS",
                    "route_confidence": 1.0,
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report = module.build_report(
        output_dir=tmp_path / "out",
        eval_path=eval_path,
        run_id="dataset-only",
        run_live_endpoint=False,
    )

    assert report["decision"] == "PASS"
    assert report["dataset_score"] == 1.0
    assert (tmp_path / "out" / "dataset-only" / "report.json").exists()
