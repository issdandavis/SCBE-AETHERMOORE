from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark.harness_live_smoke import _extract_message_text, build_chat_payload, build_smoke_report

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_live_smoke_dry_run_reports_plan_without_network() -> None:
    report = build_smoke_report(["ollama:a", "deepseek:b"], execute=False)

    assert report["schema_version"] == "scbe_harness_live_smoke_v1"
    assert report["mode"] == "dry_run"
    assert report["summary"]["planned"] == 2
    assert report["results"][0]["tool_adapter"] == "raw_json_only"
    assert "chat_url" in report["results"][0]


def test_live_smoke_payload_requires_compact_json() -> None:
    payload = build_chat_payload("ollama", "a")

    assert payload["temperature"] == 0
    assert payload["messages"][0]["role"] == "system"
    assert "Reply only" in payload["messages"][0]["content"]
    assert "harness-smoke" in payload["messages"][1]["content"]


def test_live_smoke_extracts_reasoning_content_when_content_is_null() -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "reasoning_content": "thinking text",
                    "reasoning": "fallback text",
                }
            }
        ]
    }

    assert _extract_message_text(body) == "thinking text"


def test_live_smoke_script_json_output() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/harness_live_smoke.py",
            "--models",
            "ollama:a,deepseek:b",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["mode"] == "dry_run"
    assert report["summary"]["planned"] == 2
