from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.crypto.sacred_tongue_payload_bijection import (
    canonical_json_bytes,
    prove_dict,
    prove_bytes_all_tongues,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_json_stable() -> None:
    a = canonical_json_bytes({"z": 1, "a": 2})
    b = canonical_json_bytes({"a": 2, "z": 1})
    assert a == b


def test_prove_dict_all_tongues_ok() -> None:
    out = prove_dict({"lane": "test", "tongues": 6})
    assert out["schema_version"] == "scbe_sacred_tongue_payload_bijection_v1"
    assert out["ok"] is True
    assert set(out["tongues"]) == {"ko", "av", "ru", "ca", "um", "dr"}
    for row in out["tongues"].values():
        assert row["ok"] is True


def test_prove_bytes_empty_roundtrip() -> None:
    out = prove_bytes_all_tongues(b"")
    assert out["all_ok"] is True
    for row in out["tongues"].values():
        assert row["token_count"] == 0


def test_cli_self_check() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/sacred_tongue_build_bijection.py",
            "--self-check",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["ok"] is True
