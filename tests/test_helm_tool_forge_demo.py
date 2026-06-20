"""Tool Forge demo proves the make-test-repair-keep loop."""

from pathlib import Path

from python.helm.tool_forge_demo import render_tool_forge_demo, run_tool_forge_demo


def test_tool_forge_demo_repairs_and_keeps_verified_tool(tmp_path: Path):
    result = run_tool_forge_demo(tmp_path)
    text = render_tool_forge_demo(result)

    assert result["approved"] == 7
    assert result["denied"] == 0
    assert result["failed"] == 0
    assert result["first_attempt_passed"] is False
    assert result["second_attempt_passed"] is True
    assert Path(result["kept_path"]).exists()
    assert Path(result["receipt_path"]).exists()
    assert "Helm Tool Forge demo" in text
