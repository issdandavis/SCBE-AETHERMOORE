# tests/test_tool_forge.py
import pytest

def test_forge_from_failure_pattern():
    from src.browser.tool_forge import ToolForge
    forge = ToolForge()
    tool = forge.from_failure(
        domain="shopify.com",
        failure_url="/admin/login",
        failure_reason="auth wall detected",
        surrounding_links=["/admin/products", "/admin/orders"],
    )
    assert tool.domain == "shopify.com"
    assert "login" in tool.trigger.lower() or "auth" in tool.trigger.lower()
    assert len(tool.steps) > 0

def test_forge_from_coverage_report():
    from src.browser.tool_forge import ToolForge
    from src.browser.navigation_randomtest import NavCoverageReport
    report = NavCoverageReport(
        failure_points=["/checkout/payment", "/settings/billing"],
        dead_ends=["/404"],
    )
    forge = ToolForge()
    tools = forge.from_report(domain="example.com", report=report)
    assert len(tools) >= 2  # one per failure point

def test_forge_tool_expiry():
    from src.browser.tool_forge import ToolForge
    forge = ToolForge()
    tool = forge.from_failure(domain="test.com", failure_url="/broken", failure_reason="timeout")
    assert tool.ttl_hours == 72  # default expiry

def test_forge_serializable():
    from src.browser.tool_forge import ToolForge
    forge = ToolForge()
    tool = forge.from_failure(domain="test.com", failure_url="/broken", failure_reason="404")
    d = tool.to_dict()
    assert d["domain"] == "test.com"
    assert isinstance(d["steps"], list)
