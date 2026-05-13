from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "security" / "traditional_security_layers.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_traditional_security_layers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eicar_signature_denies_without_execution(tmp_path: Path) -> None:
    layer = _load_module()
    layer.EICAR_ASCII = b"SCBE-LOCAL-EICAR-CONTROL-TEST"
    artifact = tmp_path / "eicar.txt"
    artifact.write_bytes(layer.EICAR_ASCII)

    report = layer.evaluate_artifact(artifact)
    controls = {hit.control for hit in report.controls}

    assert report.decision == "DENY"
    assert "eicar_test_signature" in controls


def test_magic_extension_mismatch_quarantines(tmp_path: Path) -> None:
    layer = _load_module()
    artifact = tmp_path / "invoice.pdf"
    artifact.write_bytes(b"MZ" + b"\x00" * 64)

    report = layer.evaluate_artifact(artifact)
    controls = {hit.control for hit in report.controls}

    assert report.decision in {"QUARANTINE", "DENY"}
    assert "magic_extension_mismatch" in controls


def test_policy_blocklist_denies_by_hash(tmp_path: Path) -> None:
    layer = _load_module()
    artifact = tmp_path / "tool.bin"
    artifact.write_bytes(b"known bad")
    digest = layer.sha256_file(artifact)
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"blocked_sha256": [digest]}), encoding="utf-8")

    report = layer.evaluate_artifact(artifact, policy_path=policy)

    assert report.decision == "DENY"
    assert any(hit.control == "hash_reputation_block" for hit in report.controls)


def test_artifact_triage_includes_traditional_controls(tmp_path: Path) -> None:
    triage_path = REPO_ROOT / "scripts" / "security" / "artifact_triage.py"
    spec = importlib.util.spec_from_file_location("_artifact_triage_traditional", triage_path)
    assert spec is not None and spec.loader is not None
    triage = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = triage
    spec.loader.exec_module(triage)

    artifact = tmp_path / "readme.txt"
    artifact.write_text("plain notes", encoding="utf-8")
    payload = triage.report_to_dict(triage.triage_artifact(artifact))

    assert payload["traditional_controls"]["schema"] == "scbe_traditional_security_layers_v1"


def test_cli_writes_traditional_security_receipt(tmp_path: Path) -> None:
    artifact = tmp_path / "dropper.exe"
    artifact.write_bytes(b"MZ" + b"\x00" * 32)
    out_dir = tmp_path / "out"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(artifact), "--output-dir", str(out_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode in {1, 2}
    assert "[traditional-security]" in result.stdout
    assert len(list(out_dir.glob("*.json"))) == 1
