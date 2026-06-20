from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNER = REPO_ROOT / "scripts" / "system" / "scbe_black_box.py"
QUICKSTART = REPO_ROOT / "docs" / "downloads" / "scbe-black-box-quickstart.md"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "black_box_download"
VERSION = "1.0.0"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(args: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _command_block(command: list[str], result: subprocess.CompletedProcess[str]) -> str:
    rendered = " ".join(command)
    return (
        f"### `{rendered}`\n\n"
        f"Exit code: `{result.returncode}`\n\n"
        "stdout:\n\n"
        "```text\n"
        f"{result.stdout.strip()}\n"
        "```\n\n"
        "stderr:\n\n"
        "```text\n"
        f"{result.stderr.strip()}\n"
        "```\n"
    )


def _verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    transcript_parts = [
        "# SCBE Black Box Verification Transcript",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This runs the exact bundled scanner and verifies that buyer-visible reports are written.",
        "",
    ]
    commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="scbe-black-box-verify-") as tmp:
        verify_dir = Path(tmp) / "report"
        command = [
            sys.executable,
            str(bundle_dir / "scbe_black_box.py"),
            "--no-fail-on-high",
            "--out-dir",
            str(verify_dir),
        ]
        result = _run(command, cwd=bundle_dir, timeout=120)
        transcript_parts.append(
            _command_block(["python", "scbe_black_box.py", "--no-fail-on-high", "--out-dir", "<temp>"], result)
        )
        commands.append({"name": "run scanner", "exit_code": result.returncode})
        json_path = verify_dir / "latest_black_box_report.json"
        text_path = verify_dir / "latest_black_box_report.txt"
        schema = ""
        finding_count = 0
        if json_path.exists():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            schema = str(payload.get("schema", ""))
            finding_count = len(payload.get("findings", []))
        output_ok = (
            json_path.exists() and text_path.exists() and schema == "scbe_black_box_report_v1" and finding_count > 0
        )
        commands.append({"name": "report files + schema", "exit_code": 0 if output_ok else 1})
    ok = all(item["exit_code"] == 0 for item in commands)
    _write_text(bundle_dir / "verification_transcript.md", "\n".join(transcript_parts))
    return {"ok": ok, "commands": commands}


def build_black_box_download(out_root: Path = DEFAULT_OUT, verify: bool = True) -> dict[str, Any]:
    bundle_name = f"SCBE-Black-Box-v{VERSION}"
    bundle_dir = out_root / bundle_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SCANNER, bundle_dir / "scbe_black_box.py")
    shutil.copy2(QUICKSTART, bundle_dir / "QUICKSTART.md")

    _write_text(
        bundle_dir / "run-windows.ps1",
        """$ErrorActionPreference = "Stop"
$Out = Join-Path $PSScriptRoot "report"
py -3 (Join-Path $PSScriptRoot "scbe_black_box.py") --no-fail-on-high --out-dir $Out
Write-Host ""
Write-Host "Report written to: $Out"
Write-Host "Open report\\latest_black_box_report.txt"
""",
    )
    _write_text(
        bundle_dir / "run-unix.sh",
        """#!/usr/bin/env sh
set -eu
OUT="$(dirname "$0")/report"
python3 "$(dirname "$0")/scbe_black_box.py" --no-fail-on-high --out-dir "$OUT"
printf '\\nReport written to: %s\\nOpen report/latest_black_box_report.txt\\n' "$OUT"
""",
    )
    _write_text(
        bundle_dir / "README.txt",
        """SCBE Black Box

Run this before long AI, browser automation, model, build, or indexing jobs.
It writes a plain-English report explaining local workstation failure signals.

Windows:
  powershell -ExecutionPolicy Bypass -File .\\run-windows.ps1

macOS/Linux:
  sh ./run-unix.sh

Output:
  report/latest_black_box_report.txt
  report/latest_black_box_report.json

No server is required. No API key is required. No remote upload is performed.
""",
    )

    sample_dir = bundle_dir / "sample-output"
    sample = _run(
        [
            sys.executable,
            str(bundle_dir / "scbe_black_box.py"),
            "--no-fail-on-high",
            "--out-dir",
            str(sample_dir),
        ],
        cwd=bundle_dir,
        timeout=120,
    )
    if sample.returncode != 0:
        raise RuntimeError(f"sample report generation failed:\nSTDOUT:\n{sample.stdout}\nSTDERR:\n{sample.stderr}")

    manifest: dict[str, Any] = {
        "schema": "scbe_black_box_download_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle_name,
        "version": VERSION,
        "product": {
            "name": "SCBE Black Box",
            "one_liner": "A local black-box report for Windows workstation shutdown, crash, and pre-failure signals.",
            "buyer_result": "report/latest_black_box_report.txt",
        },
        "files": {},
        "verification": {"ok": None, "commands": []},
    }
    for path in sorted(bundle_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(bundle_dir).as_posix()
            manifest["files"][rel] = {"sha256": _sha256(path), "bytes": path.stat().st_size}

    if verify:
        manifest["verification"] = _verify_bundle(bundle_dir)
        transcript = bundle_dir / "verification_transcript.md"
        manifest["files"][transcript.relative_to(bundle_dir).as_posix()] = {
            "sha256": _sha256(transcript),
            "bytes": transcript.stat().st_size,
        }

    _write_text(bundle_dir / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    archive_base = out_root / bundle_name
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=bundle_dir))
    manifest["archive"] = {
        "file": archive_path.name,
        "path": str(archive_path),
        "sha256": _sha256(archive_path),
        "bytes": archive_path.stat().st_size,
    }
    _write_text(bundle_dir / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    _write_text(out_root / f"{bundle_name}.manifest.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the downloadable SCBE Black Box product bundle.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Output directory for bundle artifacts.")
    parser.add_argument("--skip-verify", action="store_true", help="Build the ZIP without temp-run verification.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_black_box_download(Path(args.out_dir), verify=not args.skip_verify)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["verification"]["ok"] is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
