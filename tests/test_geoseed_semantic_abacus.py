from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.geoseed.semantic_abacus import (
    build_semantic_abacus_for_text,
    build_semantic_abacus_receipt,
)

ROOT = Path(__file__).resolve().parents[1]


def test_semantic_abacus_receipt_accounts_tokenizer_bytes_and_geoseal_allow() -> None:
    receipt = build_semantic_abacus_receipt(bytes([0xA6]), payload_label="probe")

    assert receipt.schema_version == "geoseed_semantic_abacus_receipt_v1"
    assert receipt.payload_label == "probe"
    assert receipt.payload_sha256 == hashlib.sha256(bytes([0xA6])).hexdigest()
    assert receipt.byte_count == 1
    assert receipt.bit_count == 8
    assert receipt.byte_tokens[0].hex == "a6"
    assert receipt.byte_tokens[0].bits == "10100110"
    assert receipt.composition.prime_one_counts == {
        "p2": 2,
        "p3": 0,
        "p5": 1,
        "p7": 0,
        "p11": 0,
        "p13": 1,
    }
    assert receipt.composition.prime_weighted_total == 22
    assert receipt.abacus_layer["id"] == "geoseed-tokenizer-prime"
    assert receipt.decision == "ALLOW_CLI"
    assert receipt.allowed is True


def test_semantic_abacus_receipt_attaches_geoseal_denial_without_execution() -> None:
    receipt = build_semantic_abacus_for_text(
        "x",
        expected_tool="terminal.command.request",
        origin="user",
        command="powershell Remove-Item .env -Recurse",
        workspace=ROOT,
    )

    assert receipt.decision == "DENY"
    assert receipt.allowed is False
    findings = receipt.geoseal["decision"]["findings"]
    assert any(finding["rule"].startswith("exec-gate:") for finding in findings)


def test_semantic_abacus_cli_emits_json_for_allowed_payload() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseed.semantic_abacus",
            "--hex",
            "a6",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["byte_tokens"][0]["bits"] == "10100110"
    assert payload["composition"]["prime_weighted_total"] == 22
    assert payload["decision"] == "ALLOW_CLI"
    assert payload["allowed"] is True


def test_semantic_abacus_cli_fails_closed_for_dangerous_command_shape() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseed.semantic_abacus",
            "--text",
            "x",
            "--tool",
            "terminal.command.request",
            "--command",
            "powershell Remove-Item .env -Recurse",
            "--workspace",
            str(ROOT),
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 3, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] == "DENY"
    assert payload["allowed"] is False


def test_semantic_abacus_rejects_empty_payload_and_bad_hex_cli() -> None:
    with pytest.raises(ValueError, match="payload must not be empty"):
        build_semantic_abacus_receipt(b"")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseed.semantic_abacus",
            "--hex",
            "abc",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "hex payload must contain whole bytes" in result.stderr
