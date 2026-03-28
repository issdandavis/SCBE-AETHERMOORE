from __future__ import annotations

import pytest

try:
    import websockets  # noqa: F401
except ImportError:
    pytest.skip("websockets not installed", allow_module_level=True)

from scripts.verify_aetherbrowser_extension_service import (
    build_service_report,
    classify_cdp_targets,
)


def test_classify_cdp_targets_extracts_extension_workers_and_pages():
    targets = [
        {
            "id": "page-1",
            "type": "page",
            "title": "AetherBrowser Health",
            "url": "http://127.0.0.1:8002/health",
        },
        {
            "id": "worker-1",
            "type": "service_worker",
            "title": "Service Worker chrome-extension://abc123/service_worker.js",
            "url": "chrome-extension://abc123/service_worker.js",
        },
        {
            "id": "worker-2",
            "type": "service_worker",
            "title": "Other worker",
            "url": "https://example.com/worker.js",
        },
    ]

    summary = classify_cdp_targets(targets)

    assert summary["page_count"] == 1
    assert summary["service_worker_count"] == 2
    assert summary["extension_worker_count"] == 1
    assert summary["extension_ids"] == ["abc123"]
    assert summary["pages"][0]["title"] == "AetherBrowser Health"


def test_build_service_report_tracks_provider_state_and_extension_flag():
    health = {
        "status": "ok",
        "version": "0.1.0",
        "agents": {"KO": {}, "AV": {}},
        "executor": {
            "local": {"available": True},
            "flash": {"available": False},
            "sonnet": {"available": True},
        },
    }
    cdp = {
        "page_count": 1,
        "service_worker_count": 1,
        "extension_worker_count": 1,
        "extension_ids": ["abc123"],
        "pages": [],
        "extension_workers": [],
    }

    report = build_service_report(
        health, cdp, {"research_flow": {"execution_provider": "local"}}
    )

    assert report["status"] == "ok"
    assert report["ready_providers"] == ["local", "sonnet"]
    assert report["blocked_providers"] == ["flash"]
    assert report["agent_count"] == 2
    assert report["extension_loaded"] is True
    assert report["backend_smoke"]["research_flow"]["execution_provider"] == "local"
