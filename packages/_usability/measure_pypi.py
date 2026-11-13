#!/usr/bin/env python3
"""Clean-install a published SCBE wheel, test its entry points, and measure it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
DEFAULT_RECEIPT = HERE / "PYPI_RECEIPT.json"


def tree_bytes(root: Path) -> tuple[int, int]:
    total = 0
    files = 0
    for directory, _, names in os.walk(root):
        base = Path(directory)
        for name in names:
            path = base / name
            try:
                total += path.stat().st_size
                files += 1
            except OSError:
                pass
    return total, files


def run(command: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def clip(value: str, limit: int = 400) -> str:
    return " ".join(value.split())[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default="scbe-aethermoore==4.3.2")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--no-deps", action="store_true")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    temporary = Path(tempfile.mkdtemp(prefix="scbe-pypi-usability-"))
    receipt: dict[str, object] = {
        "schema": "scbe_pypi_usability_receipt_v1",
        "spec": args.spec,
        "no_deps": args.no_deps,
        "temp_retained": args.keep,
        "temp_path": str(temporary) if args.keep else None,
    }
    failures: list[str] = []
    try:
        venv = temporary / "venv"
        created = run([sys.executable, "-m", "venv", str(venv)])
        if created.returncode:
            raise RuntimeError("venv creation failed: " + clip(created.stderr))
        bindir = venv / ("Scripts" if os.name == "nt" else "bin")
        python = bindir / ("python.exe" if os.name == "nt" else "python")
        baseline_bytes, baseline_files = tree_bytes(venv)

        install_command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--quiet",
        ]
        if args.no_deps:
            install_command.append("--no-deps")
        install_command.append(args.spec)
        installed = run(
            install_command,
            timeout=900,
        )
        if installed.returncode:
            raise RuntimeError("pip install failed: " + clip(installed.stderr, 1200))
        final_bytes, final_files = tree_bytes(venv)

        inventory_code = """
import importlib.metadata as m, json, pathlib
d=m.distribution('scbe-aethermoore')
own_bytes=0; own_files=0
for item in d.files or ():
    path=pathlib.Path(d.locate_file(item))
    if path.is_file():
        own_bytes += path.stat().st_size; own_files += 1
names=sorted({(x.metadata.get('Name') or '').strip() for x in m.distributions() if x.metadata.get('Name')})
print(json.dumps({'version':d.version,'own_bytes':own_bytes,'own_files':own_files,'distribution_count':len(names),'distributions':names}))
"""
        inventory = run([str(python), "-c", inventory_code])
        if inventory.returncode:
            raise RuntimeError(
                "installed metadata inventory failed: " + clip(inventory.stderr)
            )
        package = json.loads(inventory.stdout)

        checks = [
            (
                [
                    str(python),
                    "-c",
                    "import scbe_aethermoore as m; print(m.__version__)",
                ],
                package["version"],
            ),
            (
                [
                    str(bindir / ("scbe-scan.exe" if os.name == "nt" else "scbe-scan")),
                    "--help",
                ],
                "Usage",
            ),
            (
                [
                    str(bindir / ("scbe-scan.exe" if os.name == "nt" else "scbe-scan")),
                    "clean text",
                ],
                "ALLOW",
            ),
            (
                [str(bindir / ("scbe.exe" if os.name == "nt" else "scbe")), "--help"],
                "usage",
            ),
            (
                [
                    str(
                        bindir
                        / (
                            "scbe-code-prism.exe"
                            if os.name == "nt"
                            else "scbe-code-prism"
                        )
                    ),
                    "--help",
                ],
                "usage",
            ),
        ]
        rows = []
        for command, expected in checks:
            result = run(command, timeout=60)
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            passed = (
                result.returncode in (0, 1, 2) and expected.lower() in combined.lower()
            )
            if not passed:
                failures.append(
                    f"{Path(command[0]).name}: expected {expected!r}, exit={result.returncode}"
                )
            rows.append(
                {
                    "command": [Path(command[0]).name, *command[1:]],
                    "expected": expected,
                    "exit": result.returncode,
                    "passed": passed,
                    "output_head": clip(combined),
                }
            )

        receipt.update(
            {
                "package": package,
                "venv_baseline_bytes": baseline_bytes,
                "venv_baseline_files": baseline_files,
                "installed_delta_bytes": final_bytes - baseline_bytes,
                "installed_delta_files": final_files - baseline_files,
                "passed": len(rows) - len(failures),
                "failed": len(failures),
                "checks": rows,
            }
        )
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(
            f"pypi usability: {receipt['passed']} pass / {receipt['failed']} fail; "
            f"own={package['own_bytes']}B installed_delta={receipt['installed_delta_bytes']}B "
            f"distributions={package['distribution_count']}"
        )
        for failure in failures:
            print("FAIL:", failure)
        print("receipt", args.receipt)
        return 1 if failures else 0
    finally:
        if not args.keep:
            shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
