from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_npm_geoseal_bin_is_declared() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["bin"]["geoseal"] in {"bin/geoseal.cjs", "./bin/geoseal.cjs"}
    assert package["bin"]["scbe-geoseal"] in {"bin/geoseal.cjs", "./bin/geoseal.cjs"}
    assert (ROOT / "bin" / "geoseal.cjs").exists()


def test_npm_geoseal_bin_help() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "GeoSeal Shell" in proc.stdout
    assert "API shell" in proc.stdout
    assert "Python passthrough" in proc.stdout
    assert "nexus-dispatch" in proc.stdout
    assert "agent-io-contract" in proc.stdout
    assert "tokenizer-code-lanes" in proc.stdout


def test_npm_geoseal_bin_version_matches_package() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == package["version"]


def test_npm_geoseal_bin_python_passthrough_portal_box() -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_PYTHON"] = sys.executable
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "portal-box",
            "--content",
            "def add(a, b):\n    return a + b\n",
            "--language",
            "python",
            "--source-name",
            "sample.python",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["version"] == "geoseal-polly-portal-box-v1"
    assert payload["shell_contract"]["route_packet"]["command_key"] == "add"


def test_npm_geoseal_bin_python_passthrough_shell_command() -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_PYTHON"] = sys.executable
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "shell",
            "--command",
            'portal-box --content "def add(a, b): return a + b" --language python --source-name sample.python --json',
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["version"] == "geoseal-polly-portal-box-v1"
    assert payload["shell_contract"]["route_packet"]["command_key"] == "add"
