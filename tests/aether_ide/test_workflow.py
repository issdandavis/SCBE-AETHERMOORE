"""Tests for aether_ide.workflow."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.workflow import WorkflowTrigger


def test_workflow_health_check_unreachable():
    wf = WorkflowTrigger(bridge_url="http://127.0.0.1:59999")
    assert wf.health_check() is False


def test_workflow_governance_scan_unreachable():
    wf = WorkflowTrigger(bridge_url="http://127.0.0.1:59999")
    result = wf.governance_scan("test content")
    assert result.get("error") == "bridge_unreachable"


def test_workflow_submit_task_unreachable():
    wf = WorkflowTrigger(bridge_url="http://127.0.0.1:59999")
    result = wf.submit_task("test", {"data": "value"})
    assert result.get("error") == "bridge_unreachable"
