from __future__ import annotations

import subprocess
import sys


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_encode_decode_cmd_roundtrip() -> None:
    encoded = _run_cli("encode-cmd", "--tongue", "KO", "hello")
    assert encoded.returncode == 0, encoded.stderr
    decoded = _run_cli("decode-cmd", "--tongue", "KO", encoded.stdout.strip())
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == "hello"


def test_xlate_cmd_preserves_payload() -> None:
    encoded = _run_cli("encode-cmd", "--tongue", "KO", "abc")
    assert encoded.returncode == 0, encoded.stderr
    translated = _run_cli("xlate-cmd", "--src", "KO", "--dst", "AV", encoded.stdout.strip())
    assert translated.returncode == 0, translated.stderr
    decoded = _run_cli("decode-cmd", "--tongue", "AV", translated.stdout.strip())
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == "abc"


def test_atomic_shows_row_metadata() -> None:
    result = _run_cli("atomic", "add")
    assert result.returncode == 0, result.stderr
    assert '"name": "add"' in result.stdout
    assert '"trit":' in result.stdout
    assert '"feat":' in result.stdout
