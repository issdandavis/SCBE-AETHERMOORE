"""Run the topological-receipt canary smoke against the live pipeline.

Replays every canary prompt through ``governance_receipt`` and diffs the
result against the frozen ground truth. Exit code is non-zero on any
mismatch so CI / promotion gates can wire it directly.

Usage:
    python scripts/smoke_topological_receipt.py
    python scripts/smoke_topological_receipt.py --json-out artifacts/smoke/run.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python.scbe.tri_braid_embedding import governance_receipt  # noqa: E402


def run_smoke(canary_path: Path) -> dict:
    data = json.loads(canary_path.read_text(encoding="utf-8"))
    canaries = data["canaries"]
    failures = []

    for canary in canaries:
        prompt = canary["prompt"]
        params = canary.get("params") or {}
        expected = canary["expected"]
        actual = governance_receipt(
            prompt,
            masked_row=int(params.get("masked_row", 0)),
            masked_col=int(params.get("masked_col", 0)),
        )
        diffs = {}
        for key, want in expected.items():
            got = actual[key]
            if got != want:
                diffs[key] = {"expected": want, "actual": got}
        if diffs:
            failures.append(
                {
                    "category": canary.get("category", "?"),
                    "prompt": prompt[:80],
                    "diffs": diffs,
                }
            )

    return {
        "schema_version": data.get("schema_version", "unknown"),
        "n": len(canaries),
        "passed": len(canaries) - len(failures),
        "failed": len(failures),
        "coverage": data.get("coverage", {}),
        "failures": failures,
    }


def _format_table(result: dict) -> str:
    lines = []
    lines.append(f"smoke   schema={result['schema_version']}  n={result['n']}")
    lines.append(f"passed  {result['passed']}/{result['n']}")
    lines.append(f"failed  {result['failed']}")
    cov = result.get("coverage", {})
    if cov:
        lines.append(f"covers  decisions={cov.get('decisions', [])}")
        lines.append(f"        governance_states={cov.get('governance_states', [])}")
        lines.append(f"        tongues={cov.get('tongues', [])}")
    if result["failures"]:
        lines.append("")
        lines.append("FAILURES:")
        for failure in result["failures"]:
            lines.append(f"  [{failure['category']}] {failure['prompt']!r}")
            for key, diff in failure["diffs"].items():
                lines.append(f"      {key}: expected {diff['expected']!r}, actual {diff['actual']!r}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canary-file",
        type=Path,
        default=_ROOT / "tests" / "canary" / "topological_receipt_canaries.json",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    if not args.canary_file.exists():
        print(
            f"canary file not found: {args.canary_file}\n"
            "run: python scripts/build_topological_canaries.py",
            file=sys.stderr,
        )
        return 2

    result = run_smoke(args.canary_file)
    print(_format_table(result))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
