"""HTTP contract tests for the non-UI AetherBrowser control plane."""

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

import src.aetherbrowser.serve as serve_module

client = TestClient(serve_module.app)


def setup_function() -> None:
    serve_module.pending_browser_actions.clear()
    serve_module.pending_controller_events.clear()
    serve_module.shared_headless_context.update(
        {
            "page_context": None,
            "page_analysis": None,
            "topology": None,
            "updated_at": None,
        }
    )


def test_headless_capabilities_expose_http_surface() -> None:
    response = client.get("/headless/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "headless-http" in data["surfaces"]
    assert data["routes"]["page_context"]["path"] == "/headless/page-context"
    assert data["controller"]["model"] == "webpage_as_game_state"


def test_headless_page_context_updates_shared_context() -> None:
    response = client.post(
        "/headless/page-context",
        json={
            "url": "https://example.com/demo",
            "title": "Example Demo",
            "text": "AetherBrowser agents share browser context.",
            "headings": ["Demo"],
            "links": [{"text": "Docs", "href": "https://example.com/docs"}],
            "forms": [],
            "buttons": [],
            "tabs": [],
            "page_type": "test",
        },
    )

    data = response.json()
    assert data["status"] == "analyzed"
    assert data["context"]["page_context"]["title"] == "Example Demo"
    assert data["context"]["page_analysis"]["risk_tier"] == "low"


def test_headless_command_plans_read_only_and_holds_risky_action() -> None:
    planned = client.post(
        "/headless/command",
        json={"text": "summarize this page for an agent", "execute": False, "source": "contract-test"},
    ).json()
    held = client.post(
        "/headless/command",
        json={"text": "delete the account and submit the form", "source": "contract-test"},
    ).json()

    assert planned["status"] == "planned"
    assert planned["plan"]["next_actions"]
    assert held["status"] == "approval_required"
    assert held["approval"]["zone"] == "RED"


def test_browser_action_queue_and_controller_policy() -> None:
    action = client.post(
        "/headless/browser-action",
        json={"action": "navigate", "url": "https://example.com", "source": "contract-test"},
    ).json()
    queued = client.get("/headless/browser-actions").json()
    state = client.get("/headless/controller-state").json()
    held = client.post(
        "/headless/controller-event",
        json={"event": "primary", "source": "contract-test"},
    ).json()
    move = client.post(
        "/headless/controller-event",
        json={"event": "move_down", "source": "contract-test", "intensity": 0.25},
    ).json()

    assert action["status"] == "queued"
    assert queued["pending"]
    assert state["model"] == "webpage_as_game_state"
    assert held["status"] == "approval_required"
    assert move["status"] == "queued"
