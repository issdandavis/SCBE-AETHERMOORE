from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = REPO_ROOT / "packages" / "cli"
QUICKSTART = REPO_ROOT / "docs" / "downloads" / "scbe-workcell-quickstart.md"
PACKAGING_RESEARCH = REPO_ROOT / "docs" / "downloads" / "downloadable-app-packaging-research-2026-06-16.md"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "workcell_download"


def _resolve_executable(name: str) -> str:
    candidates = [name]
    if os.name == "nt":
        candidates = [f"{name}.cmd", f"{name}.exe", f"{name}.bat", f"{name}.ps1", name]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(f"Could not find required executable: {name}")


NPM = _resolve_executable("npm")


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cli_metadata() -> dict[str, Any]:
    package_json = json.loads((CLI_DIR / "package.json").read_text(encoding="utf-8"))
    return {
        "name": package_json["name"],
        "version": package_json["version"],
        "description": package_json.get("description", ""),
    }


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _copy_if_exists(source: Path, target: Path) -> None:
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _extract_pack_output(stdout: str) -> dict[str, Any]:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"npm pack did not return JSON: {stdout[:500]!r}") from exc
    if not isinstance(parsed, list) or not parsed:
        raise RuntimeError(f"npm pack returned an unexpected payload: {parsed!r}")
    return parsed[0]


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


def _verify_bundle(tarball: Path, out_dir: Path, package_name: str) -> dict[str, Any]:
    transcript_parts = [
        "# SCBE Workcell Verification Transcript",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This installs the packed Workcell CLI into a temporary npm prefix and runs the first buyer commands.",
        "",
    ]
    commands: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="scbe-workcell-verify-") as tmp:
        prefix = Path(tmp) / "prefix"
        install = _run(
            [NPM, "install", "--prefix", str(prefix), str(tarball), "--omit=dev", "--no-audit", "--no-fund"],
            cwd=REPO_ROOT,
            timeout=180,
        )
        transcript_parts.append(_command_block(["npm", "install", "--prefix", "<temp>", tarball.name], install))
        commands.append({"name": "install", "exit_code": install.returncode})
        if install.returncode != 0:
            _write_text(out_dir / "verification_transcript.md", "\n".join(transcript_parts))
            return {"ok": False, "commands": commands}

        bin_dir = prefix / "node_modules" / ".bin"
        scbe = bin_dir / ("scbe.cmd" if os.name == "nt" else "scbe")
        verification_commands = [
            [str(scbe), "version", "--json"],
            [str(scbe), "demo", "--json"],
            [str(scbe), "tools", "--json"],
            [str(scbe), "selftest"],
        ]
        for command in verification_commands:
            result = _run(command, cwd=REPO_ROOT, timeout=120)
            display_command = ["scbe", *command[1:]]
            transcript_parts.append(_command_block(display_command, result))
            commands.append({"name": " ".join(display_command), "exit_code": result.returncode})

    ok = all(item["exit_code"] == 0 for item in commands)
    _write_text(out_dir / "verification_transcript.md", "\n".join(transcript_parts))
    return {"ok": ok, "commands": commands, "package_name": package_name}


def build_workcell_download(out_root: Path = DEFAULT_OUT, verify: bool = True) -> dict[str, Any]:
    metadata = _load_cli_metadata()
    version = metadata["version"]
    package_name = metadata["name"]
    bundle_name = f"SCBE-Workcell-v{version}"
    bundle_dir = out_root / bundle_name
    pack_dir = out_root / "npm-pack"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pack_dir.mkdir(parents=True, exist_ok=True)

    pack = _run([NPM, "pack", "--json", "--pack-destination", str(pack_dir)], cwd=CLI_DIR, timeout=180)
    if pack.returncode != 0:
        raise RuntimeError(f"npm pack failed:\nSTDOUT:\n{pack.stdout}\nSTDERR:\n{pack.stderr}")
    pack_info = _extract_pack_output(pack.stdout)
    tarball = pack_dir / pack_info["filename"]
    bundled_tarball = bundle_dir / tarball.name
    shutil.copy2(tarball, bundled_tarball)

    _copy_if_exists(QUICKSTART, bundle_dir / "QUICKSTART.md")
    _copy_if_exists(PACKAGING_RESEARCH, bundle_dir / "PACKAGING_RESEARCH.md")
    _copy_if_exists(CLI_DIR / "README.md", bundle_dir / "CLI_README.md")
    _copy_if_exists(CLI_DIR / "LICENSE", bundle_dir / "LICENSE")
    _copy_if_exists(CLI_DIR / "LICENSE-APACHE", bundle_dir / "LICENSE-APACHE")
    _copy_if_exists(CLI_DIR / "LICENSE-NOTICE.md", bundle_dir / "LICENSE-NOTICE.md")

    _write_text(
        bundle_dir / "install-windows.ps1",
        f"""$ErrorActionPreference = "Stop"
npm install -g .\\{tarball.name}
scbe version
scbe demo --json
""",
    )
    _write_text(
        bundle_dir / "install-unix.sh",
        f"""#!/usr/bin/env sh
set -eu
npm install -g ./{tarball.name}
scbe version
scbe demo --json
""",
    )

    manifest: dict[str, Any] = {
        "schema": "scbe_workcell_download_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle_name,
        "package": metadata,
        "tarball": {
            "file": tarball.name,
            "sha256": _sha256(bundled_tarball),
            "bytes": bundled_tarball.stat().st_size,
            "npm_pack": pack_info,
        },
        "verification": {"ok": None, "commands": []},
    }

    if verify:
        manifest["verification"] = _verify_bundle(bundled_tarball, bundle_dir, package_name)

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
    parser = argparse.ArgumentParser(description="Build the downloadable SCBE Workcell bundle.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Output directory for bundle artifacts.")
    parser.add_argument("--skip-verify", action="store_true", help="Build the ZIP without temp-install verification.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_workcell_download(Path(args.out_dir), verify=not args.skip_verify)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["verification"]["ok"] is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
