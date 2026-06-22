from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCBE = REPO_ROOT / "scbe.py"


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


def test_opcode_table_cli_emits_contracts() -> None:
    result = run_scbe("opcode", "table", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_semantic_opcode_table_v1"
    tokens = {row["token"]: row for row in payload["opcodes"]}
    assert tokens["VERIFY"]["opcode_hex"] == "0x82"
    assert tokens["HALT"]["failure_behavior"] == "halt"


def test_opcode_assemble_disasm_and_run_cli_round_trip() -> None:
    program = "LOAD A 7; LOAD B 7; COMPARE A B; VERIFY; HALT"
    assembled = run_scbe("opcode", "assemble", program, "--json")

    assert assembled.returncode == 0, assembled.stderr
    asm_payload = json.loads(assembled.stdout)
    assert asm_payload["schema"] == "scbe_semantic_opcode_assemble_v1"

    disassembled = run_scbe("opcode", "disasm", asm_payload["program_hex"], "--json")
    assert disassembled.returncode == 0, disassembled.stderr
    dis_payload = json.loads(disassembled.stdout)
    assert dis_payload["program"] == ["LOAD A 7", "LOAD B 7", "COMPARE A B", "VERIFY", "HALT"]

    run_result = run_scbe("opcode", "run", asm_payload["program_hex"], "--from-hex", "--json")
    assert run_result.returncode == 0, run_result.stderr
    receipt = json.loads(run_result.stdout)
    assert receipt["schema"] == "scbe_semantic_opcode_vm_receipt_v1"
    assert receipt["verified"] is True
    assert receipt["cost"]["total_evaluations"] == 5
