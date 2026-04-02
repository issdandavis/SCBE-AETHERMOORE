from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "ingest_small_business_helper_exports.py"
SPEC = importlib.util.spec_from_file_location("ingest_small_business_helper_exports", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ingest_exports_from_thread_bundle_keeps_primary_and_compare_rows(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    bundle_path = export_dir / "helper-thread.json"
    duplicate_path = export_dir / "duplicate-thread.json"

    bundle = {
        "session": {"id": "sess-123", "startedAt": "2026-03-31T08:00:00Z"},
        "exportedAt": "2026-03-31T08:10:00Z",
        "title": "Small Business Helper",
        "assistantName": "Polly Helper",
        "primaryModel": "issdandavis/scbe-pivot-qwen-0.5b",
        "compareModels": ["openai/gpt-oss-120b"],
        "source": "small_business_helper_mobile",
        "systemPrompt": "You are Polly Helper.",
        "messages": [
            {"role": "assistant", "content": "Initial helper note.", "initial": True},
            {"role": "user", "content": "Draft a customer reply for a delayed order."},
            {
                "role": "assistant",
                "content": "Primary response.",
                "model": "issdandavis/scbe-pivot-qwen-0.5b",
                "lane": "primary",
                "label": "Polly Helper",
                "createdAt": "2026-03-31T08:00:10Z",
            },
            {
                "role": "assistant",
                "content": "Compare response.",
                "model": "openai/gpt-oss-120b",
                "lane": "compare",
                "label": "gpt-oss-120b",
                "createdAt": "2026-03-31T08:00:11Z",
            },
            {
                "role": "assistant",
                "content": "token: sk-this-should-be-scrubbed",
                "model": "broken/model",
                "lane": "error",
                "label": "broken",
                "createdAt": "2026-03-31T08:00:12Z",
            },
        ],
    }
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    duplicate_path.write_text(json.dumps(bundle), encoding="utf-8")

    output_path = tmp_path / "small_business_helper_mobile.jsonl"
    summary_path = tmp_path / "small_business_helper_mobile.summary.json"
    summary = MODULE.ingest_exports([bundle_path, duplicate_path], output_path, summary_path)

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["messages"][1]["content"] == "Draft a customer reply for a delayed order."
    assert rows[0]["metadata"]["lane"] == "primary"
    assert rows[1]["metadata"]["lane"] == "compare"
    assert rows[1]["metadata"]["model"] == "openai/gpt-oss-120b"
    assert summary["counts"]["duplicates_removed"] == 2
    assert summary["counts"]["kept_rows"] == 2


def test_ingest_exports_skips_invalid_bundle_without_messages(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"title": "broken"}), encoding="utf-8")

    output_path = tmp_path / "small_business_helper_mobile.jsonl"
    summary_path = tmp_path / "small_business_helper_mobile.summary.json"
    summary = MODULE.ingest_exports([bad_path], output_path, summary_path)

    assert output_path.read_text(encoding="utf-8") == ""
    assert summary["counts"]["bundle_files"] == 1
    assert summary["counts"]["kept_rows"] == 0
