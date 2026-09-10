from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_URL = "https://buy.stripe.com/aFafZiggOdyn9gQ11Ydby0l"


def read_doc(name: str) -> str:
    path = ROOT / "docs" / name
    assert path.exists(), f"missing public page: {path}"
    return path.read_text(encoding="utf-8")


def test_homepage_presents_verifiable_systems_path() -> None:
    homepage = read_doc("index.html")

    assert "AetherMoore | Verifiable AI Systems" in homepage
    assert "AI systems that can show their work" in homepage
    assert 'href="#work"' in homepage
    assert 'href="agents.html"' in homepage
    assert 'href="cli.html"' in homepage
    assert 'href="training-hub.html"' in homepage
    assert "briefing-room.html" not in homepage


def test_homepage_sells_verification_without_legal_claims() -> None:
    homepage = read_doc("index.html").lower()

    assert "verifiable agent infrastructure" in homepage
    assert "evidence before claims" in homepage
    assert "no certification claim" in homepage
    assert "independent lab" in homepage

    banned_phrases = [
        "lawsuit",
        "case law",
        "air canada",
        "moffatt",
        "regulators demand",
        "legal advice",
        "medical advice",
        "compliance certification",
        "regulated-context",
        "medical coding",
        "cpt",
    ]
    for phrase in banned_phrases:
        assert phrase not in homepage, f"homepage contains legal-adjacent claim phrase: {phrase}"


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
    polly = read_doc("static/polly-sidebar.js")
    polly_agent = read_doc("static/polly-sidebar-agent.js")

    assert "$39" not in intake
    assert "cheaper $39" not in workflow
    assert "$39" not in polly
    assert "$39" not in polly_agent
    assert "$99 AI Workflow Snapshot" in intake
    assert "price_usd: 99" in intake


def test_money_path_pages_load_funnel_telemetry() -> None:
    workflow = read_doc("workflow-snapshot.html")
    intake = read_doc("ai-workflow-snapshot.html")
    category = read_doc("ai-agent-governance-toolkit.html")

    assert 'src="static/polly-funnel.js"' in workflow
    assert 'src="static/polly-funnel.js"' in intake
    assert 'src="static/polly-funnel.js"' in category
    assert 'data-funnel-event="snapshot_intake_ok"' in intake


def test_ai_agent_governance_category_page_is_search_targeted() -> None:
    category = read_doc("ai-agent-governance-toolkit.html")
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
    assert "ai-agent-governance-toolkit.html" in products
    assert "https://aethermoore.com/SCBE-AETHERMOORE/ai-agent-governance-toolkit.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/ai-workflow-snapshot.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/cli.html" in sitemap
    assert '<link rel="canonical" href="https://aethermoore.com/SCBE-AETHERMOORE/cli.html" />' in cli


def test_workflow_machine_proof_page_is_discoverable_and_scoped() -> None:
    machine = read_doc("workflow-machine.html")
    sitemap = read_doc("sitemap.xml")
    llms = read_doc("llms.txt")

    assert "https://aethermoore.com/SCBE-AETHERMOORE/workflow-machine.html" in sitemap
    assert "Workflow machine proof" in llms

    assert "Crank" in machine
    assert "Forge memory" in machine
    assert "python scbe.py prove forge" in machine
    assert "python scbe.py prove black-box" in machine
    assert "re-verifies" in machine
    assert "does not claim legal protection" in machine
