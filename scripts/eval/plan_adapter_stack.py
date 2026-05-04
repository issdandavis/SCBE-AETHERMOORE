#!/usr/bin/env python3
"""Plan the next adapter stack from registry and merge-profile evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.model_training.build_adapter_registry import REPO_ROOT, build_registry

CONFIG_DIR = REPO_ROOT / "config" / "model_training"
DEFAULT_JSON = REPO_ROOT / "artifacts" / "training_hub" / "adapter_stack_plan.json"
DEFAULT_MD = REPO_ROOT / "artifacts" / "training_hub" / "adapter_stack_plan.md"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _merge_profiles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(CONFIG_DIR.glob("*.json")):
        payload = _load_json(path)
        adapters = payload.get("adapters")
        if not isinstance(adapters, list):
            continue
        rows.append(
            {
                "merge_id": payload.get("merge_id") or path.stem,
                "title": payload.get("title", path.stem),
                "output_model_repo": payload.get("output_model_repo", ""),
                "adapter_count": len(adapters),
                "required_count": sum(1 for item in adapters if isinstance(item, dict) and item.get("required")),
                "weight_total": round(
                    sum(float(item.get("weight") or 0.0) for item in adapters if isinstance(item, dict)),
                    6,
                ),
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            }
        )
    return rows


def build_stack_plan() -> dict[str, Any]:
    registry = build_registry()
    promoted = [
        row
        for row in registry["rows"]
        if row["adapter_repo"] and row["push_adapter"] and row["gate_required"]
    ]
    merge_profiles = _merge_profiles()
    next_actions = [
        "Run live adapter smoke against the promoted GeoShell paired-agent adapter.",
        "If smoke passes, add the adapter to the next weighted merge profile with a conservative weight.",
        "Regenerate this stack plan and run the merged-model evaluator before public promotion.",
    ]
    return {
        "schema_version": "scbe_adapter_stack_plan_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "promoted_adapter_candidates": promoted,
        "merge_profiles": merge_profiles,
        "next_actions": next_actions,
        "decision": "PROMOTE_TO_LIVE_SMOKE" if promoted else "HOLD_NO_PROMOTED_ADAPTER",
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# SCBE Adapter Stack Plan",
        "",
        f"Generated: `{plan['generated_utc']}`",
        f"Decision: `{plan['decision']}`",
        "",
        "## Promoted Adapter Candidates",
        "",
        "| Profile | Adapter Repo | Base Model | Path |",
        "|---|---|---|---|",
    ]
    for row in plan["promoted_adapter_candidates"]:
        lines.append(f"| `{row['profile_id']}` | `{row['adapter_repo']}` | `{row['base_model'] or '-'}` | `{row['path']}` |")
    lines.extend(["", "## Merge Profiles", "", "| Merge | Repo | Adapters | Required | Weight | Path |", "|---|---|---:|---:|---:|---|"])
    for row in plan["merge_profiles"]:
        lines.append(
            f"| `{row['merge_id']}` | `{row['output_model_repo'] or '-'}` | {row['adapter_count']} | {row['required_count']} | {row['weight_total']:.3f} | `{row['path']}` |"
        )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in plan["next_actions"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan = build_stack_plan()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(plan), encoding="utf-8")
    result = {
        "ok": True,
        "decision": plan["decision"],
        "promoted_adapter_candidates": len(plan["promoted_adapter_candidates"]),
        "merge_profiles": len(plan["merge_profiles"]),
        "paths": {"json": str(args.json_out), "markdown": str(args.md_out)},
    }
    print(json.dumps(plan if args.json else result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
