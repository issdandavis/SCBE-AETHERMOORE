#!/usr/bin/env python3
"""Build a repo-grounded adapter registry from model-training profiles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "model_training"
DEFAULT_JSON = REPO_ROOT / "artifacts" / "training_hub" / "adapter_registry.json"
DEFAULT_MD = REPO_ROOT / "artifacts" / "training_hub" / "adapter_registry.md"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _profile_row(path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    hub = payload.get("hub") if isinstance(payload.get("hub"), dict) else {}
    adapter_repo = hub.get("adapter_repo") or payload.get("adapter_repo")
    output_model_repo = payload.get("output_model_repo")
    if not adapter_repo and not output_model_repo and not payload.get("adapters"):
        return None

    return {
        "profile_id": payload.get("profile_id") or payload.get("merge_id") or path.stem,
        "schema_version": payload.get("schema_version", ""),
        "title": payload.get("title", path.stem),
        "base_model": payload.get("base_model", ""),
        "adapter_repo": adapter_repo or "",
        "output_model_repo": output_model_repo or "",
        "push_adapter": bool(hub.get("push_adapter", payload.get("push_adapter", False))),
        "gate_required": bool(hub.get("gate_required", payload.get("gate_required", False))),
        "is_merge_profile": bool(payload.get("adapters")),
        "adapter_count": len(payload.get("adapters") or []),
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def build_registry(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(config_dir.glob("*.json")):
        payload = _load_json(path)
        row = _profile_row(path, payload)
        if row is not None:
            rows.append(row)

    pushed = [row for row in rows if row["adapter_repo"] and row["push_adapter"]]
    merge_profiles = [row for row in rows if row["is_merge_profile"]]
    return {
        "schema_version": "scbe_adapter_registry_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(config_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "adapter_count": len(rows),
        "push_candidate_count": len(pushed),
        "merge_profile_count": len(merge_profiles),
        "rows": rows,
    }


def render_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# SCBE Adapter Registry",
        "",
        f"Generated: `{registry['generated_utc']}`",
        "",
        "| Profile | Adapter Repo | Base Model | Gate | Merge | Path |",
        "|---|---|---|---|---|---|",
    ]
    for row in registry["rows"]:
        lines.append(
            "| `{profile}` | `{adapter}` | `{base}` | `{gate}` | `{merge}` | `{path}` |".format(
                profile=row["profile_id"],
                adapter=row["adapter_repo"] or row["output_model_repo"] or "-",
                base=row["base_model"] or "-",
                gate="yes" if row["gate_required"] else "no",
                merge="yes" if row["is_merge_profile"] else "no",
                path=row["path"],
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    registry = build_registry()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(registry), encoding="utf-8")
    result = {"ok": True, "adapter_count": registry["adapter_count"], "paths": {"json": str(args.json_out), "markdown": str(args.md_out)}}
    print(json.dumps(registry if args.json else result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
