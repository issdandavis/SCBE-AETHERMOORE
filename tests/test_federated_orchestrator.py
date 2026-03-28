import json
import subprocess
import sys
from pathlib import Path


def _write_manifest(path: Path, provider: str, artifact_id: str, role: str, quality: float = 0.8) -> None:
    payload = {
        "provider": provider,
        "artifacts": [
            {
                "id": artifact_id,
                "role": role,
                "metrics": {
                    "quality": quality,
                    "safety": 0.98,
                    "latency_ms_p95": 100,
                    "cost_per_1k_tokens": 0.8,
                },
                "uri": f"{provider}://example/{artifact_id}",
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_orchestrator_generates_fused_manifest(tmp_path: Path) -> None:
    hf = tmp_path / "hf.json"
    gcp = tmp_path / "gcp.json"
    aws = tmp_path / "aws.json"
    out = tmp_path / "fused.json"

    _write_manifest(hf, "hf", "spiralverse/textgen-lora-v1", "textgen")
    _write_manifest(gcp, "gcp", "spiralverse/embedder-v2", "embed")
    _write_manifest(aws, "aws", "spiralverse/runtime-distilled-v3", "runtime")

    result = subprocess.run(
        [
            sys.executable,
            "training/federated_orchestrator.py",
            "--hf-manifest",
            str(hf),
            "--gcp-manifest",
            str(gcp),
            "--aws-manifest",
            str(aws),
            "--output",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert out.exists()

    fused = json.loads(out.read_text(encoding="utf-8"))
    assert set(fused["providers"]) == {"hf", "gcp", "aws"}
    assert fused["units"]["hf"]["role"] == "textgen"
    assert fused["units"]["gcp"]["role"] == "embed"
    assert fused["units"]["aws"]["role"] == "runtime"


def test_orchestrator_fails_when_provider_does_not_pass_gate(tmp_path: Path) -> None:
    hf = tmp_path / "hf.json"
    gcp = tmp_path / "gcp.json"
    aws = tmp_path / "aws.json"
    out = tmp_path / "fused.json"

    _write_manifest(hf, "hf", "spiralverse/textgen-lora-v1", "textgen", quality=0.4)
    _write_manifest(gcp, "gcp", "spiralverse/embedder-v2", "embed")
    _write_manifest(aws, "aws", "spiralverse/runtime-distilled-v3", "runtime")

    result = subprocess.run(
        [
            sys.executable,
            "training/federated_orchestrator.py",
            "--hf-manifest",
            str(hf),
            "--gcp-manifest",
            str(gcp),
            "--aws-manifest",
            str(aws),
            "--output",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "no artifacts passing promotion gates" in result.stderr.lower()
