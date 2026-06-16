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
    assert "tongue-run" in proc.stdout


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
    assert any(command["name"] == "harness-benchmark" for command in payload["commands"])


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


def test_npm_geoseal_bin_doctor_uses_lightweight_python_module_probe() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "doctor", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    src_probe = next(item for item in payload["python_modules"] if item["module"] == "src.geoseal_cli")
    assert src_probe["ok"] is True
    assert str(ROOT / "src" / "geoseal_cli.py") in src_probe["origin"]


def test_npm_geoseal_bin_service_status_is_not_python_passthrough(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_PYTHON"] = str(tmp_path / "missing-python.exe")
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "service-status",
            "--service-output-dir",
            str(tmp_path / "state"),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_service_status_v1"
    assert payload["status"] == "not_started"
    assert "geoseal_cli" not in proc.stderr


def test_npm_geoseal_bin_product_lanes_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "lanes", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_product_lanes_v1"
    lane_ids = {lane["id"] for lane in payload["lanes"]}
    assert {"agents", "providers", "chemistry", "tokenizer", "arrays-spreadsheets"} <= lane_ids


def test_npm_geoseal_bin_stage_renders_terminal_box() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "stage",
            "--width",
            "72",
            "--diagram",
            "flow",
            "input -> route -> receipt",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "GeoSeal Terminal Stage" in proc.stdout
    assert "┌" in proc.stdout
    assert "[input" in proc.stdout
    assert "receipt" in proc.stdout


def test_npm_geoseal_bin_stage_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "stage",
            "--json",
            "--title",
            "Courier",
            "input -> route -> receipt",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_terminal_stage_v1"
    assert payload["title"] == "Courier"
    assert payload["route_hint"] == "input → route → receipt"


def test_npm_geoseal_bin_rooms_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "rooms",
            "--room",
            "frontend",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_stage_rooms_v1"
    assert payload["selected"]["id"] == "frontend"
    assert "component" in " ".join(payload["selected"]["examples"])


def test_npm_geoseal_bin_rooms_termux_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "rooms",
            "--room",
            "termux",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["selected"]["id"] == "termux"
    assert "phone-friendly" in payload["selected"]["purpose"]


def test_npm_geoseal_bin_stage_named_example_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "stage",
            "--room",
            "frontend",
            "--example",
            "slideshow",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_terminal_stage_v1"
    assert payload["room"] == "frontend"
    assert payload["example"] == "slideshow"
    assert "slides data" in payload["content"]
    assert len(payload["frames"]) >= 3


def test_npm_geoseal_bin_stage_frame_github_json() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "stage-frame",
            "--room",
            "github",
            "--example",
            "pr-flow",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_stage_frame_v1"
    assert payload["room"] == "github"
    assert payload["example"] == "pr-flow"
    assert len(payload["frames"]) >= 4
    assert "command-check" in payload["safety"]["preflight"]


def test_npm_geoseal_bin_stage_frame_renders_terminal_boxes() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "stage-frame",
            "--room",
            "github",
            "--example",
            "pr-flow",
            "--width",
            "76",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "GitHub Room Stage Frames" in proc.stdout
    assert "frame 01" in proc.stdout
    assert "\u250c" in proc.stdout


def test_npm_geoseal_bin_command_check_allows_read_only() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "command-check",
            "--json",
            "Get-ChildItem docs",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_command_preflight_v1"
    assert payload["decision"] == "allow"


def test_npm_geoseal_bin_command_check_refuses_home_delete() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "command-check",
            "--json",
            "Remove-Item -Recurse C:\\Users\\issda",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "block"
    assert payload["safety"] == "refused"


def test_npm_geoseal_bin_command_check_requires_confirm_for_writes() -> None:
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "command-check",
            "--json",
            "Set-Content output.txt hello",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 3
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "confirm"
    assert payload["safety"] == "write"


def test_npm_geoseal_bin_provider_registry_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "providers", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_provider_registry_v1"
    providers = {provider["id"]: provider for provider in payload["providers"]}
    assert providers["local-service"]["tier"] == "free"
    assert providers["openai"]["tier"] == "paid"
    assert payload["policy"]["default_route"] == "free_local_first"


def test_npm_geoseal_bin_ask_alias_requires_local_service_when_not_running(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_SERVICE_DIR"] = str(tmp_path / "state")
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "ask", "explain", "tokenizer", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_alias_v1"
    assert payload["routes_to"] == "chat"
    assert payload["error"] == "local_service_required"


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


def test_npm_geoseal_bin_python_passthrough_tongue_run() -> None:
    env = dict(os.environ)
    env["SCBE_GEOSEAL_PYTHON"] = sys.executable
    program = "ko:set r0, 4\nko:set r1, 6\nca:add r2, r0, r1\nko:print r2\nko:halt"
    proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "tongue-run",
            "--content",
            program,
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
    assert payload["schema_version"] == "geoseal_tongue_run_v1"
    assert payload["run"]["output"] == [10]


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
