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
    assert "materials" in proc.stdout
    assert "math" in proc.stdout
    assert "units" in proc.stdout


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


def test_npm_geoseal_bin_code_languages_ir_and_injection_plan(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.py"
    source_file.write_text(
        "import math\n\n"
        "class Wheel:\n"
        "    pass\n\n"
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )

    languages_proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "code-languages", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert languages_proc.returncode == 0, languages_proc.stderr
    languages_payload = json.loads(languages_proc.stdout)
    assert languages_payload["schema_version"] == "geoseal_code_languages_v1"
    assert languages_payload["bijection_scope"]["transport"].startswith("byte_hex_binary")
    assert any(row["language"] == "python" and row["tongue"] == "KO" for row in languages_payload["languages"])

    ir_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "code-ir",
            "--source-file",
            str(source_file),
            "--language",
            "python",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert ir_proc.returncode == 0, ir_proc.stderr
    ir_payload = json.loads(ir_proc.stdout)
    assert ir_payload["schema_version"] == "geoseal_code_ir_v1"
    assert ir_payload["language"] == "python"
    assert ir_payload["symbols"]["functions"] == ["add"]
    assert ir_payload["symbols"]["classes"] == ["Wheel"]
    assert ir_payload["transport_lanes_available"] == ["byte", "hex", "binary", "tongue"]

    plan_proc = subprocess.run(
        [
            "node",
            str(ROOT / "bin" / "geoseal.cjs"),
            "injection-plan",
            "--source-file",
            str(source_file),
            "--interval",
            "lines:3",
            "--tongues",
            "KO,AV",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert plan_proc.returncode == 0, plan_proc.stderr
    plan_payload = json.loads(plan_proc.stdout)
    assert plan_payload["schema_version"] == "geoseal_code_injection_plan_v1"
    assert plan_payload["checkpoint_policy"] == "deterministic_hash_sync_markers_only_no_prompt_or_code_injection"
    assert plan_payload["checkpoint_count"] >= 2
    assert plan_payload["checkpoints"][0]["marker"].startswith("SCBE_SYNC_KO_0000_")
    assert plan_payload["checkpoints"][1]["marker"].startswith("SCBE_SYNC_AV_0001_")


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


def test_npm_geoseal_bin_easy_aliases() -> None:
    tools_proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "tools", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert tools_proc.returncode == 0, tools_proc.stderr
    tools_payload = json.loads(tools_proc.stdout)
    assert tools_payload["schema_version"] == "geoseal_toolbox_v1"
    assert any(tool["command"] == "materials" for tool in tools_payload["quick_start"])

    math_proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "math", "sqrt(2)^2 + phi", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert math_proc.returncode == 0, math_proc.stderr
    math_payload = json.loads(math_proc.stdout)
    assert math_payload["schema_version"] == "geoseal_calc_v1"
    assert math_payload["ok"] is True

    units_proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "units", "kg*m/s^2", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert units_proc.returncode == 0, units_proc.stderr
    units_payload = json.loads(units_proc.stdout)
    assert units_payload["canonical"] == "M L T^-2"


def test_npm_geoseal_bin_materials_missing_query_json() -> None:
    proc = subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), "materials", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_material_search_v1"
    assert payload["error"] == "missing_material_query"


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
    assert any(tool["command"] == "materials" for tool in payload["network_tools"])
    assert any(tool["command"] == "math" for tool in payload["quick_start"])
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
    assert any(command["command"] == "materials" for command in payload["commands"])
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


def _run_geoseal(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(ROOT / "bin" / "geoseal.cjs"), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_npm_geoseal_code_ir_python_imports_no_newlines() -> None:
    target = ROOT / "scripts" / "research" / "mahss_demo.py"
    assert target.exists(), f"fixture missing: {target}"
    proc = _run_geoseal(
        "code-ir", "--source-file", str(target), "--language", "python", "--json"
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    imports = payload["symbols"]["imports"]
    assert isinstance(imports, list) and len(imports) >= 1
    for imp in imports:
        assert "\n" not in imp, f"newline bleed in import: {imp!r}"
        assert "\r" not in imp, f"CR bleed in import: {imp!r}"
        assert "import" not in imp, f"unparsed token in import: {imp!r}"


def test_npm_geoseal_code_verify_happy_path() -> None:
    target = ROOT / "scripts" / "research" / "mahss_demo.py"
    proc = _run_geoseal(
        "code-verify", "--source-file", str(target), "--language", "python", "--json"
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "geoseal_code_verify_v1"
    assert payload["ok"] is True
    assert payload["language"] == "python"
    assert isinstance(payload["actual_source_sha256"], str)
    assert len(payload["actual_source_sha256"]) == 64
    assert payload["sha_check"]["provided"] is False
    assert payload["sha_check"]["ok"] is True
    assert payload["ir_check"]["provided"] is False
    assert payload["probe"]["requested"] is False
    assert payload["verdict"]["ok"] is True


def test_npm_geoseal_code_verify_sha_mismatch_fails() -> None:
    target = ROOT / "scripts" / "research" / "mahss_demo.py"
    bogus = "0" * 64
    proc = _run_geoseal(
        "code-verify",
        "--source-file",
        str(target),
        "--language",
        "python",
        "--expected-source-sha",
        bogus,
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["sha_check"]["provided"] is True
    assert payload["sha_check"]["ok"] is False
    assert payload["sha_check"]["expected_source_sha256"] == bogus
    assert payload["sha_check"]["actual_source_sha256"] != bogus
    assert payload["verdict"]["ok"] is False
    assert payload["verdict"]["checks"]["sha_check_ok"] is False


def test_npm_geoseal_code_translate_emits_deterministic_contract() -> None:
    target = ROOT / "scripts" / "research" / "mahss_demo.py"
    proc1 = _run_geoseal(
        "code-translate",
        "--source-file",
        str(target),
        "--language",
        "python",
        "--target-language",
        "typescript",
        "--json",
    )
    assert proc1.returncode == 0, proc1.stderr
    payload1 = json.loads(proc1.stdout)
    assert payload1["schema_version"] == "geoseal_code_translate_contract_v1"
    assert payload1["ok"] is True
    assert payload1["source"]["language"] == "python"
    assert payload1["target"]["language"] == "typescript"
    contract_id = payload1["contract_id"]
    assert isinstance(contract_id, str) and len(contract_id) == 24
    must = payload1["contract"]["must_preserve"]
    assert isinstance(must["functions"], list)
    assert isinstance(must["classes"], list)
    forced = payload1["contract"]["forced_prefix"]
    assert "required-preserved-identifiers" in forced
    assert payload1["policy"] == "contract_only_no_llm_invocation_no_code_execution"

    proc2 = _run_geoseal(
        "code-translate",
        "--source-file",
        str(target),
        "--language",
        "python",
        "--target-language",
        "typescript",
        "--json",
    )
    assert proc2.returncode == 0, proc2.stderr
    payload2 = json.loads(proc2.stdout)
    assert payload2["contract_id"] == contract_id, "contract_id must be deterministic"


def test_npm_geoseal_help_advertises_code_verify_and_translate() -> None:
    proc = _run_geoseal("--help")
    assert proc.returncode == 0, proc.stderr
    assert "code-verify" in proc.stdout
    assert "code-translate" in proc.stdout
