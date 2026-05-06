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
    assert "calc" in proc.stdout
    assert "dimensions" in proc.stdout
    assert "web-search" in proc.stdout


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


def test_npm_geoseal_bin_custom_commands_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "custom-commands", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_custom_commands_v1"
    assert payload["count"] >= 1
    assert any(
        command["name"] == "harness-benchmark" for command in payload["commands"]
    )


def test_npm_geoseal_bin_permissions_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "permissions", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_permissions_v1"
    assert payload["gates"]["secrets_to_remote_models"] == "forbid"
    assert payload["max_tier"]


def test_npm_geoseal_bin_run_command_template_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "run-command",
            "harness-benchmark",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_custom_command_v1"
    assert payload["command"]["name"] == "harness-benchmark"
    assert payload["command"]["execution_mode"] == "template_only"
    assert payload["safety"]["executes_shell"] is False


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


def test_npm_geoseal_bin_code_lanes_roundtrip(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_PYTHON"] = sys.executable

    lanes_file = tmp_path / "shl_lanes.json"
    decode_dir = tmp_path / "decoded"

    lanes_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "tokenizer-code-lanes",
            "--command",
            "shl",
            "--tongues",
            "KO,AV",
            "--output",
            str(lanes_file),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert lanes_proc.returncode == 0, lanes_proc.stderr
    lanes_payload = json.loads(lanes_proc.stdout)
    assert lanes_payload["schema_version"] == "geoseal_tokenizer_code_lanes_v1"
    assert lanes_file.exists()

    verify_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "verify-code-lanes",
            "--input-file",
            str(lanes_file),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert verify_proc.returncode == 0, verify_proc.stderr
    verify_payload = json.loads(verify_proc.stdout)
    assert verify_payload["ok"] is True

    decode_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "decode-code-lanes",
            "--input-file",
            str(lanes_file),
            "--output-dir",
            str(decode_dir),
            "--write-binary",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert decode_proc.returncode == 0, decode_proc.stderr
    decode_payload = json.loads(decode_proc.stdout)
    assert decode_payload["decoded_count"] == 2
    for row in decode_payload["written"]:
        assert Path(row["path"]).exists()
        assert Path(row["binary_path"]).exists()


def test_npm_geoseal_bin_local_toolbox_math_and_dimensions() -> None:
    calc_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "calc",
            "--expr",
            "sqrt(2)^2 + phi",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert calc_proc.returncode == 0, calc_proc.stderr
    calc_payload = json.loads(calc_proc.stdout)
    assert calc_payload["schema_version"] == "geoseal_calc_v1"
    assert calc_payload["ok"] is True
    assert abs(calc_payload["value"] - (2 + calc_payload["constants"]["phi"])) < 1e-12

    dims_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "dimensions",
            "--unit",
            "kg*m/s^2",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert dims_proc.returncode == 0, dims_proc.stderr
    dims_payload = json.loads(dims_proc.stdout)
    assert dims_payload["schema_version"] == "geoseal_dimensional_analysis_v1"
    assert dims_payload["vector"] == [1, 1, -2, 0, 0, 0, 0]
    assert dims_payload["canonical"] == "M L T^-2"


def test_npm_geoseal_bin_toolbox_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "toolbox", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_toolbox_v1"
    assert any(tool["command"] == "calc" for tool in payload["local_tools"])
    assert any(tool["command"] == "web-search" for tool in payload["network_tools"])
    assert payload["safety"]["secrets_to_remote_models"] == "forbid"


def test_npm_geoseal_bin_terminal_ui_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "terminal-ui", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_terminal_ui_v1"
    assert payload["ok"] is True
    assert payload["interactive"] is False
    assert any(command["command"] == "calc" for command in payload["commands"])
    assert any(command["command"] == "url-fetch" for command in payload["commands"])
    assert payload["safety"]["shell_execution"] == "not available"


def test_npm_geoseal_bin_agent_bus_ui_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "agent-bus-ui", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_agent_bus_frontend_v1"
    assert payload["ok"] is True
    assert payload["backend_default"] == "http://127.0.0.1:8787"
    assert any(command["command"] == "agent-bus-server" for command in payload["commands"])
    assert any(command["command"] == "agent-bus-send" for command in payload["commands"])
    assert payload["safety"]["default_privacy"] == "local_only"
