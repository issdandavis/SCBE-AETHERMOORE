from __future__ import annotations

import json

from src.geoseal_cli import main


def test_arc_chart_missing_root_is_strict_json_error(capsys, tmp_path):
    code = main(
        [
            "arc-chart",
            "state",
            "--task",
            "missing-task",
            "--arc-root",
            str(tmp_path),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["schema_version"] == "geoseal_arc_chart_error_v1"
    assert payload["ok"] is False
    assert "ARC chart package not found" in payload["error"]


def test_arc_build_missing_root_is_strict_json_error(capsys, tmp_path):
    code = main(["arc-build", "--arc-root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["schema_version"] == "geoseal_arc_chart_error_v1"
    assert payload["ok"] is False
    assert "ARC Prize package not found" in payload["error"]
