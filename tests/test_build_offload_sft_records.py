from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "build_offload_sft_records.py"
)
SPEC = importlib.util.spec_from_file_location("build_offload_sft_records", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_build_sft_records_filters_empty_and_dedupes(tmp_path: Path) -> None:
    run_root = tmp_path / "runs"
    run_a = run_root / "20260321T000000Z"
    run_b = run_root / "20260321T000100Z"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)

    row_keep = {
        "instruction": "Classify file A",
        "output": "This file is a lore planning note that should be archived for writing context.",
        "input": {
            "relative_path": "notes/file-a.txt",
            "assigned_lane": "gemini-sorter",
            "assigned_provider": "google",
            "assigned_model": "gemini-2.5-flash",
            "selected_lane": "gemini-sorter",
            "size": 123,
        },
        "metadata": {
            "source_sha256": "abc123",
            "timestamp_utc": "2026-03-21T20:00:00Z",
        },
    }
    row_duplicate = dict(row_keep)
    row_skip = {
        "instruction": "Classify file B",
        "output": "",
        "input": {"relative_path": "notes/file-b.txt", "size": 55},
        "metadata": {"source_sha256": "def456"},
    }

    (run_a / "training_rows.jsonl").write_text(
        json.dumps(row_keep) + "\n" + json.dumps(row_skip) + "\n",
        encoding="utf-8",
    )
    (run_b / "training_rows.jsonl").write_text(
        json.dumps(row_duplicate) + "\n", encoding="utf-8"
    )

    output_path = tmp_path / "sft_multi_agent_offload.jsonl"
    summary = MODULE.build_sft_records(
        run_root=run_root, output_path=output_path, min_output_chars=5
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["instruction"] == "Classify file A"
    assert record["response"].startswith("This file is a lore planning note")
    assert record["metadata"]["run_id"] == "20260321T000000Z"
    assert summary["raw_rows"] == 3
    assert summary["kept_rows"] == 1
    assert summary["duplicates_removed"] == 1
    assert summary["skipped_short_or_empty"] == 1
