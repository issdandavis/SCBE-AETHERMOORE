"""Build every implementation and verify one byte-exact golden packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "c549c006d3378380e37db58ddc44b3a167d3a63bad0f99e731d3d092ab838518"


def run(command: list[str], *, cwd: Path, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != expect_success:
        raise RuntimeError(
            f"unexpected exit {result.returncode}: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required tool is not on PATH: {name}")
    return path


def main() -> int:
    started = time.perf_counter()
    fixture = bytes.fromhex((ROOT / "fixtures" / "held_context_v1.hex").read_text(encoding="ascii"))
    digest = hashlib.sha256(fixture).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"golden fixture SHA-256 mismatch: {digest}")

    sys.path.insert(0, str(ROOT / "python"))
    from held_context import decode_packet  # noqa: PLC0415

    if decode_packet(fixture).encode() != fixture:
        raise RuntimeError("Python round trip changed canonical bytes")

    cargo = require_tool("cargo")
    zig = require_tool("zig")
    javac = require_tool("javac")
    java = require_tool("java")
    implementations: dict[str, dict[str, object]] = {
        "python": {"roundtrip": True, "rejects_corruption": True},
    }

    with tempfile.TemporaryDirectory(prefix="hctx-interop-") as temp_name:
        temp = Path(temp_name)
        fixture_path = temp / "fixture.hctx"
        fixture_path.write_bytes(fixture)
        corrupt_path = temp / "corrupt.hctx"
        corrupt = bytearray(fixture)
        corrupt[-1] ^= 1
        corrupt_path.write_bytes(corrupt)

        rust_target = temp / "rust-target"
        run(
            [
                cargo,
                "build",
                "--release",
                "--manifest-path",
                str(ROOT / "rust" / "Cargo.toml"),
                "--target-dir",
                str(rust_target),
            ],
            cwd=ROOT,
        )
        rust_exe = rust_target / "release" / "held-context-rs.exe"
        rust_output = temp / "rust.hctx"
        run([str(rust_exe), "roundtrip", str(fixture_path), str(rust_output)], cwd=ROOT)
        run([str(rust_exe), "validate", str(corrupt_path)], cwd=ROOT, expect_success=False)
        implementations["rust"] = {
            "roundtrip": rust_output.read_bytes() == fixture,
            "rejects_corruption": True,
        }

        c_exe = temp / "held-context-c.exe"
        run(
            [
                zig,
                "cc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(ROOT / "c" / "held_context.c"),
                str(ROOT / "c" / "main.c"),
                "-o",
                str(c_exe),
            ],
            cwd=ROOT,
        )
        c_output = temp / "c.hctx"
        run([str(c_exe), "roundtrip", str(fixture_path), str(c_output)], cwd=ROOT)
        run([str(c_exe), "validate", str(corrupt_path)], cwd=ROOT, expect_success=False)
        implementations["c"] = {
            "roundtrip": c_output.read_bytes() == fixture,
            "rejects_corruption": True,
        }

        java_build = temp / "java-build"
        java_build.mkdir()
        run(
            [
                javac,
                "-Xlint:all",
                "-Werror",
                "-d",
                str(java_build),
                str(ROOT / "java" / "io" / "aethermoor" / "context" / "HeldContextPacket.java"),
                str(ROOT / "java" / "io" / "aethermoor" / "context" / "HeldContextSelfTest.java"),
            ],
            cwd=ROOT,
        )
        java_output = temp / "java.hctx"
        java_command = [java, "-cp", str(java_build), "io.aethermoor.context.HeldContextSelfTest"]
        run([*java_command, "roundtrip", str(fixture_path), str(java_output)], cwd=ROOT)
        run([*java_command, "validate", str(corrupt_path)], cwd=ROOT, expect_success=False)
        implementations["java"] = {
            "roundtrip": java_output.read_bytes() == fixture,
            "rejects_corruption": True,
        }

    if not all(bool(row["roundtrip"]) for row in implementations.values()):
        raise RuntimeError("at least one implementation changed the golden vector")
    report = {
        "schema": "held-context-interop-v1",
        "fixture_bytes": len(fixture),
        "fixture_sha256": digest,
        "implementations": implementations,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "status": "PASS",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
