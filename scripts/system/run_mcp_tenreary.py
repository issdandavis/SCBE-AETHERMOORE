#!/usr/bin/env python3
"""Run a custom MCP tenreary workflow file.

Example:
  python scripts/system/run_mcp_tenreary.py --file workflows/tenreary/sample_dual_browser_monetization.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hydra.tenreary import MCPTenrearyRunner, load_tenreary
from scripts.system.tenreary_benchmark_harness import score_run


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run custom MCP tenreary workflows.")
    parser.add_argument("--file", required=True, help="Path to tenreary JSON file.")
    parser.add_argument("--scbe-url", default="http://127.0.0.1:8080")
    parser.add_argument("--allow-network", action="store_true", default=True)
    parser.add_argument("--no-allow-network", dest="allow_network", action="store_false")
    parser.add_argument("--benchmark", dest="benchmark", action="store_true", default=True)
    parser.add_argument("--no-benchmark", dest="benchmark", action="store_false")
    parser.add_argument("--set", action="append", default=[], help="Context override key=value (repeatable).")
    parser.add_argument("--output-dir", default="artifacts/tenreary")
    parser.add_argument("--json", action="store_true", help="Print raw JSON only.")
    return parser.parse_args()


def _parse_context_overrides(items: list[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            continue
        key, _, raw = item.partition("=")
        key = key.strip()
        if not key:
            continue
        raw = raw.strip()
        if not raw:
            out[key] = ""
            continue
        try:
            out[key] = json.loads(raw)
        except Exception:
            out[key] = raw
    return out


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    workflow_path = Path(args.file).resolve()
    tenreary = load_tenreary(workflow_path)
    runner = MCPTenrearyRunner(scbe_url=args.scbe_url, allow_network=bool(args.allow_network))
    context_seed = _parse_context_overrides(list(args.set))
    result = await runner.run(tenreary, context_seed=context_seed)
    result["workflow_path"] = str(workflow_path)

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = (REPO_ROOT / args.output_dir / day).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tenreary-run-{_utc_stamp()}.json"

    if bool(args.benchmark):
        try:
            result["benchmark"] = score_run(result, artifact_path=str(out_path)).to_dict()
        except Exception as exc:
            result["benchmark"] = {"error": f"{type(exc).__name__}: {exc}"}

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    result["artifact_path"] = str(out_path)
    return result


def main() -> int:
    args = parse_args()
    result = asyncio.run(run(args))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[tenreary] name={result.get('tenreary_name')} ok={result.get('ok')}")
        print(f"[tenreary] steps={result.get('steps_ok')}/{result.get('steps_total')}")
        if isinstance(result.get("benchmark"), dict):
            benchmark = result["benchmark"]
            if benchmark.get("overall_score") is not None:
                print(
                    "[tenreary] benchmark="
                    f"{benchmark.get('truth_assessment')} "
                    f"overall={benchmark.get('overall_score')}"
                )
        print(f"[tenreary] artifact={result.get('artifact_path')}")
    return 0 if bool(result.get("ok")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
