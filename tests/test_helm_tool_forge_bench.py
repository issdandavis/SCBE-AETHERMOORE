"""Tool Forge Bench proves public checks, hidden checks, repair, and receipts."""

from pathlib import Path

from python.helm.tool_forge_bench import render_tool_forge_bench, run_tool_forge_bench


def test_tool_forge_bench_repairs_all_tasks_and_keeps_receipts(tmp_path: Path):
    summary = run_tool_forge_bench(workspace=tmp_path)
    text = render_tool_forge_bench(summary)

    assert summary["tasks"] == 4
    assert summary["passed_after_repair"] == 4
    assert summary["pass_rate"] == 1.0
    assert summary["hidden_catches"] >= 2
    assert "Helm Tool Forge Bench" in text

    for row in summary["results"]:
        assert row["first_attempt_passed"] is False
        assert row["second_attempt_passed"] is True
        assert row["approved"] == 7
        assert row["denied"] == 0
        assert row["failed"] == 0
        assert Path(row["kept_path"]).exists()
        assert Path(row["receipt_path"]).exists()
