"""Tests for aether_ide.editor."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.editor import GovernedEditor


def test_editor_default_mode():
    ed = GovernedEditor()
    assert ed.mode == "ENGINEERING"
    assert ed.zone == "HOT"


def test_editor_available_tools():
    ed = GovernedEditor()
    tools = ed.available_tools()
    assert isinstance(tools, tuple)
    assert len(tools) > 0


def test_editor_switch_mode():
    ed = GovernedEditor(mode="ENGINEERING", zone="HOT")
    ed.switch_mode("NAVIGATION")
    assert ed.mode == "NAVIGATION"
    assert ed.zone == "HOT"  # Always demotes on switch


def test_editor_tongue_mapping():
    ed = GovernedEditor(mode="ENGINEERING")
    assert ed.tongue == "CA"  # ENGINEERING -> CA

    ed.switch_mode("COMMS")
    assert ed.tongue == "KO"  # COMMS -> KO


def test_editor_demote():
    ed = GovernedEditor(mode="ENGINEERING", zone="HOT")
    ed.demote()  # Already HOT, should be no-op
    assert ed.zone == "HOT"


def test_editor_tool_check():
    ed = GovernedEditor(mode="ENGINEERING", zone="HOT")
    tools = ed.available_tools()
    if tools:
        assert ed.is_tool_allowed(tools[0]) is True
    assert ed.is_tool_allowed("NONEXISTENT_TOOL_XYZ") is False
