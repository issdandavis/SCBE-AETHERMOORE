from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "benchmark" / "governed_output_latency.js"


def test_governed_output_latency_json_shape() -> None:
    result = subprocess.run(
        ["node", str(SCRIPT), "--json", "--no-remote", "--samples", "25"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert payload["schema"] == "scbe_governed_output_latency_v1"
    assert payload["local_samples"] == 25
    assert payload["remote"]["skipped"] is True
    names = {row["name"] for row in payload["local"]}
    assert "shouldPreBlock_clean" in names
    assert "shouldPreBlock_bad" in names
    assert "buildGovernanceRecord_allow" in names
    assert "openAiResponse_shape" in names
    for row in payload["local"]:
        assert row["count"] == 25
        assert row["p50_ms"] >= 0
        assert row["p95_ms"] >= 0
