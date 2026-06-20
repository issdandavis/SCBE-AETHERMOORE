from __future__ import annotations

import json
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.system.build_black_box_download import DEFAULT_OUT, build_black_box_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and run SCBE Black Box, then print the top finding.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Output directory for the buyer ZIP and proof run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    manifest = build_black_box_download(out_dir, verify=True)
    bundle_dir = out_dir / manifest["bundle_name"]
    proof_dir = bundle_dir / "proof-run"
    scanner = bundle_dir / "scbe_black_box.py"

    result = subprocess.run(
        [
            sys.executable,
            str(scanner),
            "--no-fail-on-high",
            "--out-dir",
            str(proof_dir),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    report_json = proof_dir / "latest_black_box_report.json"
    report_text = proof_dir / "latest_black_box_report.txt"
    report = json.loads(report_json.read_text(encoding="utf-8"))
    findings = report.get("findings", [])
    top = findings[0] if findings else {}

    print("SCBE Black Box proof run")
    print("========================")
    print(report.get("summary", "No summary"))
    print()
    if top:
        print(f"Top finding: [{top.get('severity', '?').upper()}] {top.get('title', '?')}")
        if top.get("evidence"):
            print(f"Evidence: {top['evidence'][0]}")
        if top.get("action"):
            print(f"Action: {top['action']}")
    else:
        print("Top finding: none")
    print()
    print(f"Buyer ZIP: {manifest['archive']['path']}")
    print(f"ZIP SHA-256: {manifest['archive']['sha256']}")
    print(f"Text report: {report_text}")
    print(f"JSON report: {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
