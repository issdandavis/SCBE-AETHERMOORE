import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCBE = REPO_ROOT / "scbe.py"
GEOSEAL = REPO_ROOT / "bin" / "geoseal.cjs"


def run_scbe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCBE), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )


def run_geoseal(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(GEOSEAL), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )


def ensure_aethermon_adapter_target() -> None:
    result = run_geoseal("aethermon-adapter", "build", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["schema"] == "aethermon_agent_adapter_v0_manifest"


def test_bits_alias_emits_machine_readable_packet() -> None:
    result = run_scbe("bits", "SCBE", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_bit_spine_packet_v1"
    assert payload["binary"] == "01010011010000110100001001000101"
    assert payload["hex"] == "53434245"
    assert payload["views"]["binary"] == payload["binary"]


def test_spine_decode_hex_round_trips_text() -> None:
    result = run_scbe("spine", "decode", "--from", "hex", "53434245", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_bit_spine_decode_v1"
    assert payload["text"] == "SCBE"


def test_spine_decode_trits_round_trips_text() -> None:
    encoded = run_scbe("trits", "A")
    assert encoded.returncode == 0, encoded.stderr

    decoded = run_scbe("spine", "decode", "--from", "trits", encoded.stdout.strip(), "--json")

    assert decoded.returncode == 0, decoded.stderr
    payload = json.loads(decoded.stdout)
    assert payload["text"] == "A"
    assert payload["hex"] == "41"


def test_binary_increment_alias_uses_turing_machine() -> None:
    result = run_scbe("inc", "1111", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_binary_turing_increment_v1"
    assert payload["output"] == "10000"
    assert payload["alphabet"] == ["0", "1", "B"]


def test_spine_run_brainfuck_class_program() -> None:
    result = run_scbe("spine", "run", ",.", "--input", "A", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_spine_program_run_v1"
    assert payload["output_text"] == "A"
    assert payload["output_hex"] == "41"


def test_spine_relationship_vm_emits_verified_receipt() -> None:
    result = run_scbe(
        "spine",
        "rel",
        "read 0 A; transform add A 1; write A 1; verify mem[1] eq 0x42",
        "--memory-hex",
        "41",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_relationship_vm_receipt_v1"
    assert payload["verified"] is True
    assert payload["registers"]["A"] == 0x42
    assert payload["memory_nonzero"]["1"] == 0x42


def test_templates_include_user_agent_and_geoseal_commands() -> None:
    result = run_scbe("templates", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_spine_templates_v1"
    assert 'scbe bits "hello"' in payload["commands"]["users"]
    assert "geoseal spine templates --json" in payload["commands"]["sub_agents"]


def test_map_unifies_bit_tongue_atomic_chemistry_and_workflow_lanes() -> None:
    result = run_scbe("map", "release payload after compare", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_unified_substrate_packet_v1"
    assert payload["bit_spine"]["hex"] == "72656c65617365207061796c6f616420616674657220636f6d70617265"
    assert set(payload["sacred_tongues"]["projection"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert payload["atomic_tokenization"]["states"][0]["element"]["symbol"] == "Fe"
    assert "tau_hat" in payload["atomic_tokenization"]["fusion"]
    assert payload["chemistry_tokenization"]["command_stack"]["validation"]["deterministic_projection"] is True
    assert payload["workflow_units"]["units"][0]["chemistry_lane"]["bond_capacity"] >= 1
    system_ids = {system["id"] for system in payload["local_code_systems"]["systems"]}
    assert {"bit_spine", "atomic_tokenization", "chemical_fusion", "chemistry_command_stack"} <= system_ids


def test_systems_inventory_lists_local_code_systems() -> None:
    result = run_scbe("systems", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_local_code_systems_v1"
    system_ids = {system["id"] for system in payload["systems"]}
    assert {"sacred_tongues", "ast_cube", "rust_ast_cube_hot_loop"} <= system_ids
    assert payload["active_unified_command"] == 'scbe map "<text>" --json'


def test_map_json_is_strict_json_for_node_agents() -> None:
    if shutil.which("node") is None:
        return

    result = run_scbe("map", "release payload after compare", "--json")
    assert result.returncode == 0, result.stderr

    parser = subprocess.run(
        ["node", "-e", "JSON.parse(require('fs').readFileSync(0, 'utf8')); console.log('ok')"],
        input=result.stdout,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert parser.returncode == 0, parser.stderr
    assert parser.stdout.strip() == "ok"


def test_geoseal_spine_commands_passthrough_to_scbe() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("bits", "SCBE", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_bit_spine_packet_v1"
    assert payload["hex"] == "53434245"


def test_geoseal_map_passthrough_to_unified_substrate() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("map", "release payload after compare", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_unified_substrate_packet_v1"
    assert payload["chemistry_tokenization"]["command_stack"]["schema_version"] == "scbe-chemistry-command-stack-v1"


def test_geoseal_systems_passthrough_to_inventory() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("systems", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_local_code_systems_v1"
    assert any(system["id"] == "atomic_tokenization" for system in payload["systems"])


def test_geoseal_help_lists_system_map_and_aethermon_adapter_lanes() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("help")

    assert result.returncode == 0, result.stderr
    assert "geoseal system-map --check" in result.stdout
    assert "geoseal aethermon-adapter preflight --json" in result.stdout
    assert "geoseal powershell check --command" in result.stdout


def test_geoseal_system_map_runs_procedural_map_json() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("system-map", "--dry-run", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["world_digest"]
    assert payload["summary"]["regions"] >= 1


def test_geoseal_aethermon_adapter_preflight_uses_local_profile() -> None:
    if shutil.which("node") is None:
        return

    ensure_aethermon_adapter_target()
    result = run_geoseal("aethermon-adapter", "preflight", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["profile_id"] == "aethermon-agent-adapter-v0-local"


def test_geoseal_aethermon_adapter_abstain_runs_eval_gate() -> None:
    if shutil.which("node") is None:
        return

    ensure_aethermon_adapter_target()
    result = run_geoseal("aethermon-adapter", "abstain", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["rates"]["abstain"] == 1.0
    assert payload["promotion_gate"]["ok"] is False


def test_geoseal_powershell_profiles_are_bounded() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("powershell", "profiles", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "geoseal_powershell_profiles_v1"
    assert payload["ok"] is True
    profile_ids = {profile["id"] for profile in payload["profiles"]}
    assert {"pwd", "version", "repo_files"} <= profile_ids
    assert all("command" not in profile for profile in payload["profiles"])
    assert "get-location" in payload["ad_hoc_profile"]["allowed_commands"]


def test_geoseal_powershell_check_blocks_destructive_command() -> None:
    if shutil.which("node") is None:
        return

    result = run_geoseal("powershell", "check", "--command", r"Remove-Item C:\Temp -Recurse", "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["decision"] == "block"


def test_geoseal_powershell_run_executes_harmless_command() -> None:
    if shutil.which("node") is None or shutil.which("powershell") is None:
        return

    result = run_geoseal("powershell", "run", "--command", "Write-Output GEOSEAL_PS_OK", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "geoseal_powershell_run_v1"
    assert payload["ok"] is True
    assert payload["risk_tier"] == "bounded-host-read"
    assert payload["command_digest"]
    assert "GEOSEAL_PS_OK" in payload["stdout_tail"]


def test_geoseal_powershell_run_can_write_and_list_receipts() -> None:
    if shutil.which("node") is None or shutil.which("powershell") is None:
        return

    receipt_dir = "artifacts/pytest_tmp/geoseal_powershell_receipts"
    result = run_geoseal(
        "powershell",
        "run",
        "--command",
        "Write-Output GEOSEAL_PS_RECEIPT",
        "--write-receipt",
        "--receipt-dir",
        receipt_dir,
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    receipt_path = REPO_ROOT / payload["receipt_path"]
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "geoseal_powershell_run_v1"
    assert "GEOSEAL_PS_RECEIPT" in receipt["stdout_tail"]

    listed = run_geoseal("powershell", "receipts", "--receipt-dir", receipt_dir, "--json")
    assert listed.returncode == 0, listed.stderr
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["schema_version"] == "geoseal_powershell_receipts_v1"
    assert any(item["file"] == payload["receipt_path"] for item in listed_payload["receipts"])


def test_geoseal_colab_watch_reads_local_checkpoint(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        return

    result_path = tmp_path / "results_20260702_050228.json"
    result_path.write_text(
        json.dumps(
            {
                "meta": {"stamp": "20260702_050228"},
                "A": {
                    "Qwen2.5-Coder-0.5B": {"py": {}, "jl": {}, "rs": {}, "hs": {}},
                    "Qwen2.5-Coder-1.5B": {"py": {}, "jl": {}, "rs": {}, "hs": {}},
                },
                "B": {},
                "C": {},
            }
        ),
        encoding="utf-8",
    )
    receipt_dir = "artifacts/pytest_tmp/geoseal_colab_watch"

    result = run_geoseal(
        "colab-watch",
        "--file",
        str(result_path),
        "--write-receipt",
        "--receipt-dir",
        receipt_dir,
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_colab_hf_watch_v1"
    assert payload["state"]["status"] == "complete"
    assert payload["state"]["a_cells"] == 8
    assert (REPO_ROOT / payload["receipt_path"]).exists()
