import asyncio

import pytest

try:
    from cryptography.fernet import Fernet  # noqa: F401
except BaseException:
    pytest.skip(
        "cryptography package not functional (cffi backend missing)",
        allow_module_level=True,
    )

from hydra.tenreary import MCPTenreary, MCPTenrearyRunner


def test_tenreary_rule_analysis_local_only():
    tenreary = MCPTenreary.from_dict(
        {
            "tenreary_type": "mcp.tenreary.v1",
            "name": "unit-tenreary",
            "dual_browser": {"enabled": False},
            "steps": [
                {
                    "id": "set_a",
                    "type": "context.set",
                    "params": {
                        "key": "message",
                        "value": "stripe checkout conversion n8n zapier",
                    },
                },
                {
                    "id": "analyze",
                    "type": "analysis.content",
                    "params": {"backend": "rule", "source_key": "message"},
                },
            ],
        }
    )

    runner = MCPTenrearyRunner(allow_network=False)
    result = asyncio.run(runner.run(tenreary))

    assert result["ok"] is True
    assert result["steps_total"] == 2
    assert result["steps_failed"] == 0
    analyze = [r for r in result["results"] if r["id"] == "analyze"][0]
    assert analyze["status"] == "ok"
    keywords = analyze["data"]["analysis"]["top_keywords"]
    assert "stripe" in keywords or "checkout" in keywords


def test_tenreary_nested_step_context_resolution():
    tenreary = MCPTenreary.from_dict(
        {
            "tenreary_type": "mcp.tenreary.v1",
            "name": "nested-step-context",
            "dual_browser": {"enabled": False},
            "steps": [
                {
                    "id": "set_alpha",
                    "type": "context.set",
                    "params": {"key": "alpha", "value": "money"},
                },
                {
                    "id": "set_beta",
                    "type": "context.set",
                    "params": {"key": "beta", "value": "{{step.set_alpha.data.value}}"},
                },
            ],
        }
    )

    runner = MCPTenrearyRunner(allow_network=False)
    result = asyncio.run(runner.run(tenreary))

    assert result["ok"] is True
    set_beta = [r for r in result["results"] if r["id"] == "set_beta"][0]
    assert set_beta["status"] == "ok"
    assert set_beta["data"]["value"] == "money"


def test_tenreary_notion_append_skips_without_network():
    tenreary = MCPTenreary.from_dict(
        {
            "tenreary_type": "mcp.tenreary.v1",
            "name": "notion-append-offline",
            "dual_browser": {"enabled": False},
            "steps": [
                {
                    "id": "set_payload",
                    "type": "context.set",
                    "params": {
                        "key": "run_summary",
                        "value": {"cash_signal": 88, "elite_ready": True},
                    },
                },
                {
                    "id": "notion_log",
                    "type": "notion.append",
                    "params": {
                        "page_id": "2a8e8d49c25b4bdaa8c5739db28e2ec1",
                        "source_key": "run_summary",
                        "heading": "Tenreary Revenue Run",
                    },
                },
            ],
        }
    )

    runner = MCPTenrearyRunner(allow_network=False)
    result = asyncio.run(runner.run(tenreary))

    assert result["ok"] is True
    notion_log = [r for r in result["results"] if r["id"] == "notion_log"][0]
    assert notion_log["status"] == "ok"
    assert notion_log["data"]["status"] == "skipped"
    assert notion_log["data"]["reason"] == "network_disabled"
