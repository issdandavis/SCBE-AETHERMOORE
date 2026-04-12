from __future__ import annotations

from pathlib import Path

from scripts.system.openclaw_hf_handler_bootstrap import (
    BootstrapPlan,
    _extract_tool_names,
    _extract_tool_payload,
    build_bootstrap_report,
)


def test_extract_tool_names_finds_browser_and_scbe_tools() -> None:
    payload = {
        "response": {
            "tools": [
                {"name": "browser", "description": "bundled browser"},
                {
                    "name": "scbe_model_plan",
                    "label": "SCBE Model Plan",
                    "parameters": {},
                },
                {
                    "name": "scbe_octoarms_dispatch",
                    "label": "dispatch",
                    "parameters": {},
                },
            ]
        }
    }

    assert _extract_tool_names(payload) == [
        "browser",
        "scbe_model_plan",
        "scbe_octoarms_dispatch",
    ]


def test_extract_tool_payload_decodes_text_json() -> None:
    payload = {
        "response": {
            "content": [
                {
                    "type": "text",
                    "text": '{"profile_id":"hf-agentic-handler","base_model":"HuggingFaceTB/SmolLM2-1.7B-Instruct","ready":true}',
                }
            ]
        }
    }

    decoded = _extract_tool_payload(payload)
    assert decoded["profile_id"] == "hf-agentic-handler"
    assert decoded["ready"] is True


def test_build_bootstrap_report_tracks_missing_tools_and_handler_state() -> None:
    plan = BootstrapPlan(
        repo_root="C:/repo",
        probe_script="C:/repo/scripts/system/openclaw_gateway_probe.mjs",
        node_bin="node",
        profile="hf-agentic-handler",
        provider="hf",
        lane="hydra-swarm",
        formation="hexagonal-ring",
        workflow_template="training-center-loop",
        task="Bootstrap",
        dry_run=True,
        timeout_ms=120000,
        output_path=str(Path("C:/repo/artifacts/openclaw-plugin/bootstrap.json")),
    )
    health = {"response": {"ok": True}}
    catalog = {"response": {"tools": [{"name": "scbe_model_plan", "label": "Model"}]}}
    model = {
        "response": {
            "content": [
                {
                    "type": "text",
                    "text": '{"profile_id":"hf-agentic-handler","base_model":"HuggingFaceTB/SmolLM2-1.7B-Instruct","backend":"unsloth-qlora","ready":true,"total_train_rows":122579,"total_eval_rows":2048,"missing_files":[]}',
                }
            ]
        }
    }

    report = build_bootstrap_report(plan, health, catalog, model)

    assert report["health"]["ok"] is True
    assert report["catalog"]["missing_tools"] == ["browser", "scbe_octoarms_dispatch"]
    assert report["hf_handler"]["profile_id"] == "hf-agentic-handler"
    assert report["hf_handler"]["ready"] is True
    assert report["ready"] is False
