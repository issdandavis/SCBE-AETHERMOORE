from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "training" / "build_agentic_coding_workbench.py"


def test_agentic_coding_workbench_builder_outputs_routeable_records(tmp_path: Path) -> None:
    output = tmp_path / "agentic_workbench_scbe.jsonl"
    manifest = tmp_path / "manifest.json"
    site_data = tmp_path / "site.json"
    site_index = tmp_path / "index.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(ROOT),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--site-data",
            str(site_data),
            "--site-index",
            str(site_index),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = json.loads(site_data.read_text(encoding="utf-8"))
    index_payload = json.loads(site_index.read_text(encoding="utf-8"))

    assert len(rows) == 5
    assert payload["schema_version"] == "scbe_agentic_coding_workbench_v1"
    assert payload["record_count"] == 5
    assert {"KO", "AV", "RU", "CA", "UM", "DR"}.issubset(payload["route_counts"])

    first = rows[0]
    assert first["category"] == "agentic-coding-workbench"
    assert first["messages"][0]["role"] == "system"
    assert "STISA/Sacred Tongues" in first["messages"][0]["content"]
    assert "<governance>" in first["messages"][2]["content"]
    assert first["metadata"]["research_grounding"]
    assert first["metadata"]["retrieval_count"] >= 1
    assert first["metadata"]["verification"]
    assert index_payload["tasks"]["agentic_coding_workbench"]["file"] == "agentic-coding-workbench.json"
