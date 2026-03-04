"""Tests for customer connector template generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_customer_connector_template_generation(tmp_path: Path):
    access_map = {
        "services": [
            {
                "service": "GitHub",
                "domain": "github.com",
                "tier": "full_access",
                "access_methods": {
                    "api": {"available": True, "env_var": "GITHUB_TOKEN", "base_url": "https://api.github.com"},
                    "browser": {"available": True},
                    "cli": {"available": True},
                },
                "notes": "Test service",
            }
        ]
    }
    access_map_path = tmp_path / "access_map.json"
    access_map_path.write_text(json.dumps(access_map), encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "system" / "customer_connector_template.py"
    out_root = tmp_path / "intake"

    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--customer-id",
            "acme",
            "--connectors",
            "github.com",
            "--access-map",
            str(access_map_path),
            "--out-root",
            str(out_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["customer_id"] == "acme"
    assert payload["connectors_count"] == 1
    assert payload["generated_pin"] is True
    assert "one_time_admin_pin" in payload

    customer_dir = out_root / "acme"
    profile = json.loads((customer_dir / "connector_profile.json").read_text(encoding="utf-8"))
    pin_meta = json.loads((customer_dir / "admin_pin.json").read_text(encoding="utf-8"))
    env_tpl = (customer_dir / ".env.template").read_text(encoding="utf-8")

    assert profile["customer_id"] == "acme"
    assert profile["connectors"][0]["domain"] == "github.com"
    assert pin_meta["algorithm"] == "pbkdf2_sha256"
    assert "GITHUB_TOKEN=" in env_tpl

