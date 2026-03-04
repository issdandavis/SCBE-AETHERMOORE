"""Integration-style tests for use_customer_connector_profile runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _write_profile(tmp_path: Path) -> Path:
    profile = {
        "profile_id": "cust-test-1234",
        "customer_id": "test-customer",
        "connectors": [
            {
                "service": "GitHub",
                "domain": "github.com",
                "channels": {"api": True, "cli": True, "browser": True},
                "auth_env_vars": ["GITHUB_TOKEN"],
            }
        ],
    }
    profile_path = tmp_path / "connector_profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    pin = "12345678"
    salt = "abcd1234abcd1234abcd1234abcd1234"
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 200000).hex()
    pin_meta = {
        "algorithm": "pbkdf2_sha256",
        "iterations": 200000,
        "salt": salt,
        "pin_hash": digest,
    }
    (tmp_path / "admin_pin.json").write_text(json.dumps(pin_meta), encoding="utf-8")
    return profile_path


def test_use_customer_profile_channel_cli_runs(tmp_path: Path):
    profile_path = _write_profile(tmp_path)
    script = Path(__file__).resolve().parent.parent / "scripts" / "system" / "use_customer_connector_profile.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--profile",
            str(profile_path),
            "--domain",
            "github.com",
            "--task",
            "sync repo",
            "--channel",
            "cli",
            "--admin-pin",
            "12345678",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["profile_use"]["admin_pin_verified"] is True
    assert payload["profile_use"]["channel"] == "cli"


def test_use_customer_profile_strict_api_blocks_without_env(tmp_path: Path):
    profile_path = _write_profile(tmp_path)
    script = Path(__file__).resolve().parent.parent / "scripts" / "system" / "use_customer_connector_profile.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--profile",
            str(profile_path),
            "--domain",
            "github.com",
            "--task",
            "sync repo",
            "--channel",
            "api",
            "--strict",
            "--admin-pin",
            "12345678",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["error"] in {"connector_env_missing", "connector_not_ready"}

