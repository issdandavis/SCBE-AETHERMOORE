import json
import subprocess
import sys
from pathlib import Path


def test_doc_verifier_writes_verified_manifest(tmp_path: Path) -> None:
    out = tmp_path / "doc_manifest.json"

    proc = subprocess.run(
        [
            sys.executable,
            "training/doc_verifier.py",
            "--out",
            str(out),
            "--glob",
            "training/kernel_manifest.yaml",
            "--attest",
            "claude,gpt",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert proc.returncode == 0, proc.stdout
    payload = json.loads(out.read_text(encoding="utf-8"))
    docs = payload["documents"]
    kernel_doc = next(doc for doc in docs if doc["filename"] == "training/kernel_manifest.yaml")

    assert payload["document_count"] >= 1
    assert len(kernel_doc["sha256"]) == 64
    assert kernel_doc["verification"]["status"] == "verified"
    assert kernel_doc["verification"]["attesters"] == ["claude", "gpt"]


def test_doc_verifier_json_flag_prints_manifest(tmp_path: Path) -> None:
    out = tmp_path / "doc_manifest.json"

    proc = subprocess.run(
        [
            sys.executable,
            "training/doc_verifier.py",
            "--json",
            "--out",
            str(out),
            "--glob",
            "training/kernel_manifest.yaml",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["documents"]
    assert out.exists()
