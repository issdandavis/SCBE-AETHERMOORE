from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_URL = "https://buy.stripe.com/aFafZiggOdyn9gQ11Ydby0l"


def read_doc(name: str) -> str:
    path = ROOT / "docs" / name
    assert path.exists(), f"missing public page: {path}"
    return path.read_text(encoding="utf-8")


def test_homepage_focuses_first_buyer_path_on_workflow_snapshot() -> None:
    homepage = read_doc("index.html")

    assert "Start $99 Workflow Snapshot" in homepage
    assert "ai-workflow-snapshot.html#receipt" in homepage
    assert "payments.html" in homepage
    assert "briefing-room.html" not in homepage


def test_workflow_snapshot_checkout_is_consistent_and_live_wired() -> None:
    workflow = read_doc("workflow-snapshot.html")
    intake = read_doc("ai-workflow-snapshot.html")
    config = json.loads((ROOT / "docs" / "app-config.json").read_text(encoding="utf-8"))

    assert CHECKOUT_URL in workflow
    assert CHECKOUT_URL in intake
    assert 'data-funnel-event="cta_click_buy"' in workflow
    assert 'data-funnel-event="cta_click_buy"' in intake
    assert config["endpoints"]["workflow_snapshot_checkout"] == CHECKOUT_URL
    assert config["endpoints"]["workflow_snapshot_page"].endswith("/workflow-snapshot.html")


def test_ai_workflow_snapshot_has_no_stale_39_dollar_copy() -> None:
    intake = read_doc("ai-workflow-snapshot.html")
    workflow = read_doc("workflow-snapshot.html")

    assert "$39" not in intake
    assert "cheaper $39" not in workflow
    assert "$99 AI Workflow Snapshot" in intake
    assert "price_usd: 99" in intake


def test_money_path_pages_load_funnel_telemetry() -> None:
    homepage = read_doc("index.html")
    workflow = read_doc("workflow-snapshot.html")
    intake = read_doc("ai-workflow-snapshot.html")
    category = read_doc("ai-agent-governance-toolkit.html")

    assert 'src="static/polly-funnel.js"' in homepage
    assert 'src="static/polly-funnel.js"' in workflow
    assert 'src="static/polly-funnel.js"' in intake
    assert 'src="static/polly-funnel.js"' in category
    assert 'data-funnel-event="snapshot_intake_ok"' in intake


def test_ai_agent_governance_category_page_is_search_targeted() -> None:
    category = read_doc("ai-agent-governance-toolkit.html")
    homepage = read_doc("index.html")
    products = read_doc("products.html")
    sitemap = read_doc("sitemap.xml")
    cli = read_doc("cli.html")

    assert "<title>AI Agent Governance Toolkit and Workflow Audit | AetherMoore</title>" in category
    assert "AI agent governance starter path" in category
    assert "AI agent workflow audit" in category
    assert "Cursor, Copilot, Claude Code, Codex" in category
    assert "Zapier, Make, n8n, Lindy" in category
    assert "$99 Workflow Snapshot" in category
    assert 'data-funnel-event="cta_click_buy"' in category
    assert "ai-agent-governance-toolkit.html" in homepage
    assert "ai-agent-governance-toolkit.html" in products
    assert "https://aethermoore.com/SCBE-AETHERMOORE/ai-agent-governance-toolkit.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/ai-workflow-snapshot.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/cli.html" in sitemap
    assert '<link rel="canonical" href="https://aethermoore.com/SCBE-AETHERMOORE/cli.html" />' in cli
