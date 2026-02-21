#!/usr/bin/env python3
"""Review alignment between Notion sync sources, training data, and fine-tune funnel targets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_CHECKLIST = [
    "notion-sync",
    "notion-to-dataset",
    "fine-tune-funnel",
]


def _safe_load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        # Minimal parser fallback for key paths we need.
        data: Dict[str, Any] = {}
        current = ""
        in_fine_tune = False
        in_streams = False
        streams: List[Dict[str, Any]] = []
        active_stream: Dict[str, Any] | None = None

        for raw in text.splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*$", line):
                key = line[:-1]
                current = key
                if key == "fine_tune":
                    data[key] = {}
                    in_fine_tune = True
                    in_streams = False
                    continue
                if in_fine_tune and key == "streams":
                    data.setdefault("fine_tune", {})
                    data["fine_tune"]["streams"] = []
                    in_streams = True
                    continue
                in_streams = False
                in_fine_tune = False
                active_stream = None
                continue

            if not in_fine_tune:
                continue

            if in_streams and re.match(r"^\s{2,4}streams:\s*$", line):
                in_streams = True
                continue

            if in_streams and re.match(r"^\s{4}-\s*name:\s*", line):
                value = line.split(":", 1)[1].strip()
                active_stream = {"name": value}
                streams.append(active_stream)
                continue

            if in_streams and active_stream is not None and re.match(r"^\s{6}[A-Za-z_][A-Za-z0-9_-]*:\s*", line):
                key, value = [part.strip() for part in line.split(":", 1)]
                if value == "":
                    continue
                if re.match(r"^-?\d+\.\d+$", value):
                    active_stream[key] = float(value)
                elif re.match(r"^-?\d+$", value):
                    active_stream[key] = int(value)
                elif value.lower() in {"true", "false"}:
                    active_stream[key] = value.lower() == "true"
                else:
                    active_stream[key] = value.strip("'\"")
                continue

            if in_streams and active_stream is not None and re.match(r"^\s{8}-\s+", line):
                entry = line.split("-", 1)[1].strip().strip("'\"")
                if entry:
                    active_stream.setdefault("categories", []).append(entry)

        if streams:
            data.setdefault("fine_tune", {})
            data["fine_tune"]["streams"] = streams

        return data


def _list_jsonl_records(training_data_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for jsonl_path in sorted(training_data_dir.glob("*.jsonl")):
        try:
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                rows = json.loads(stripped)
                if isinstance(rows, dict):
                    rows["_source_file"] = jsonl_path.name
                    records.append(rows)
        except Exception:
            continue
    return records


def _load_metadata(training_data_dir: Path) -> Dict[str, Any]:
    metadata_path = training_data_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    return _safe_load_json(metadata_path)


def _build_task(
    title: str,
    description: str,
    component: str,
    mode: str,
    priority: str,
    evidence: Dict[str, Any],
    suggested_actions: List[str],
    confidence: float = 0.82,
) -> Dict[str, Any]:
    return {
        "task_id": hashlib.sha1(f"{title}:{component}:{priority}:{mode}".encode("utf-8")).hexdigest()[:12],
        "mode": mode,
        "title": title,
        "description": description,
        "component": component,
        "priority": priority,
        "tongue": "KO",
        "confidence": confidence,
        "evidence": evidence,
        "suggested_actions": suggested_actions,
    }


def _evaluate_sync_config(sync_config: Dict[str, Any], now: datetime, tasks: List[Dict[str, Any]]) -> None:
    if not sync_config:
        tasks.append(
            _build_task(
                title="Populate notion sync config",
                description="No sync-config.json detected; docs sync cannot validate Notion page coverage.",
                component="Notion Sync Coverage",
                mode="code-assistant",
                priority="high",
                confidence=0.95,
                evidence={"missing_file": "scripts/sync-config.json"},
                suggested_actions=[
                    "Add valid Notion page IDs to scripts/sync-config.json.",
                    "Run scripts/notion-sync.js --all to refresh docs content.",
                ],
            )
        )
        return

    for name, entry in sync_config.items():
        if not isinstance(entry, dict):
            continue
        page_id = str(entry.get("pageId", "")).strip()
        if not page_id or page_id.startswith("REPLACE_WITH_"):
            tasks.append(
                _build_task(
                    title=f"Resolve Notion placeholder for sync key '{name}'",
                    description=f"Sync entry '{name}' has no real pageId. This blocks full docs parity checks.",
                    component="Notion Sync Coverage",
                    mode="code-assistant",
                    priority="high",
                    confidence=0.96,
                    evidence={"sync_key": name, "page_id": page_id},
                    suggested_actions=[
                        "Insert the correct Notion page ID for this key.",
                        "Re-run notion-to-dataset and notion-sync workflows.",
                    ],
                )
            )
            continue

        output_path = Path(entry.get("outputPath", "") or "")
        if output_path:
            normalized = Path(output_path)
            if not normalized.is_absolute():
                normalized = Path("C:/Users/issda/SCBE-AETHERMOORE-working") / normalized
            if not normalized.exists():
                tasks.append(
                    _build_task(
                        title=f"Sync output path missing for '{name}'",
                        description=f"The configured output path '{output_path}' is missing.",
                        component="Notion Sync Coverage",
                        mode="code-assistant",
                        priority="medium",
                        confidence=0.78,
                        evidence={"sync_key": name, "output_path": output_path},
                        suggested_actions=[
                            "Verify docs folder path and run notion sync for this entry.",
                        ],
                    )
                )


def _evaluate_funnel_config(
    pipeline_config: Dict[str, Any],
    records: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> None:
    streams = (pipeline_config.get("fine_tune") or {}).get("streams", [])
    quality = (pipeline_config.get("fine_tune") or {}).get("quality_checks", {})
    total = len(records)
    if not streams:
        tasks.append(
            _build_task(
                title="Missing fine_tune streams in vertex pipeline config",
                description="fine_tune.streams is empty; training funnel balancing cannot be verified.",
                component="Fine-Tune Funnel",
                mode="fine-tune-funnel",
                priority="critical",
                confidence=0.97,
                evidence={"pipeline_config": "training/vertex_pipeline_config.yaml"},
                suggested_actions=[
                    "Add technical/lore stream definitions with required_min_records.",
                    "Re-run notion export and then run self-improvement loop.",
                ],
            )
        )
        return

    category_index: Dict[str, int] = {}
    for record in records:
        for category in record.get("categories", []) or ["general"]:
            category_index[category] = category_index.get(category, 0) + 1

    for stream in streams:
        if not isinstance(stream, dict):
            continue
        name = str(stream.get("name", "unnamed-stream"))
        required = int(stream.get("required_min_records", 0) or 0)
        stream_categories = {x.lower() for x in stream.get("categories", []) if isinstance(x, str)}

        matched = 0
        for record in records:
            cats = {str(cat).lower() for cat in record.get("categories", [])}
            if stream_categories.intersection(cats):
                matched += 1

        if required and matched < required:
            ratio = matched / required if required else 1.0
            priority = "critical" if ratio < 0.25 else "high" if ratio < 0.5 else "medium"
            tasks.append(
                _build_task(
                    title=f"Increase '{name}' training stream coverage",
                    description=(
                        f"Stream '{name}' has {matched}/{required} records from configured Notion/fine-tune sources."
                    ),
                    component="Fine-Tune Funnel",
                    mode="fine-tune-funnel",
                    priority=priority,
                    confidence=0.86,
                    evidence={
                        "stream": stream,
                        "required_min_records": required,
                        "matched_records": matched,
                        "total_records": total,
                    },
                    suggested_actions=[
                        "Export missing notion categories using the requested sync query.",
                        "Tag records for the target stream so it reaches required minimum.",
                    ],
                )
            )

    if total and quality.get("max_category_imbalance"):
        max_imbalance = float(quality.get("max_category_imbalance"))
        values = sorted(category_index.values(), reverse=True)
        if len(values) >= 2:
            highest = values[0]
            lowest = max(1, values[-1])
            if highest / lowest > max_imbalance:
                tasks.append(
                    _build_task(
                        title="Fine-tune stream imbalance exceeds quality threshold",
                        description="Training coverage is skewed across categories and may bias inference behavior.",
                        component="Fine-Tune Funnel",
                        mode="fine-tune-funnel",
                        priority="medium",
                        confidence=0.77,
                        evidence={
                            "category_counts": category_index,
                            "max_category_imbalance": max_imbalance,
                        },
                        suggested_actions=[
                            "Increase data in low-volume categories.",
                            "Add explicit curation rules for category balancing.",
                        ],
                    )
                )


def _evaluate_metadata(metadata: Dict[str, Any], tasks: List[Dict[str, Any]]) -> None:
    if not metadata:
        tasks.append(
            _build_task(
                title="Rebuild training-data metadata file",
                description="No training-data/metadata.json was found from notion-to-dataset export.",
                component="Notion Export Pipeline",
                mode="code-assistant",
                priority="high",
                confidence=0.93,
                evidence={"expected_file": "training-data/metadata.json"},
                suggested_actions=[
                    "Run notion_to_dataset.py and verify export step writes metadata.json.",
                ],
            )
        )
        return

    exported = int(metadata.get("exported_records", 0))
    if exported == 0:
        tasks.append(
            _build_task(
                title="Notion export returned zero records",
                description="The last notion-to-dataset run exported 0 records, indicating token scope or query issues.",
                component="Notion Export Pipeline",
                mode="code-assistant",
                priority="critical",
                confidence=0.98,
                evidence=metadata,
                suggested_actions=[
                    "Verify NOTION token has readable workspace scope.",
                    "Confirm notion_to_dataset filters are not over-restrictive.",
                ],
            )
        )

    export_date = metadata.get("export_date")
    if export_date:
        try:
            last = datetime.fromisoformat(str(export_date).replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - last).days
            if age_days > 10:
                tasks.append(
                    _build_task(
                        title="Notion export metadata is stale",
                        description=f"metadata.json export_date is {age_days} days old.",
                        component="Notion Export Pipeline",
                        mode="code-assistant",
                        priority="medium",
                        confidence=0.75,
                        evidence={"export_date": export_date, "age_days": age_days},
                        suggested_actions=[
                            "Run notion-to-dataset workflow more frequently.",
                            "Verify scheduled trigger is enabled.",
                        ],
                    )
                )
        except Exception:
            pass


def _build_summary(tasks: List[Dict[str, Any]], records: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    by_priority = {}
    for task in tasks:
        by_priority[task["priority"]] = by_priority.get(task["priority"], 0) + 1

    return {
        "status": "requires_attention" if tasks else "healthy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(tasks),
        "task_priority_counts": by_priority,
        "total_records": len(records),
        "exported_records": int(metadata.get("exported_records", 0) or 0),
        "category_breakdown": metadata.get("category_breakdown", {}),
        "checklist": DEFAULT_CHECKLIST,
    }


def run_gap_review(
    repo_root: Path,
    sync_config_path: Path,
    pipeline_config_path: Path,
    training_data_path: Path,
) -> Dict[str, Any]:
    sync_config = _safe_load_json(sync_config_path)
    if not sync_config:
        sync_config = {}
    pipeline_config = _safe_load_yaml(pipeline_config_path)
    records = _list_jsonl_records(training_data_path)
    metadata = _load_metadata(training_data_path)

    tasks: List[Dict[str, Any]] = []

    _evaluate_sync_config(sync_config, datetime.now(timezone.utc), tasks)
    _evaluate_funnel_config(pipeline_config, records, tasks)
    _evaluate_metadata(metadata, tasks)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "sync_config": str(sync_config_path),
        "pipeline_config": str(pipeline_config_path),
        "training_data": str(training_data_path),
        "summary": _build_summary(tasks, records, metadata),
        "tasks": tasks,
    }


def _write_summary(markdown_path: Path, manifest: Dict[str, Any]) -> None:
    lines = [
        "# Notion Pipeline Gap Review",
        f"Generated: {manifest['generated_at']}",
        f"Repo: {manifest['repo_root']}",
        f"Total tasks: {manifest['summary']['total_tasks']}",
        "",
        "## Priority Counts",
    ]
    for key, value in sorted(manifest["summary"]["task_priority_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Notion Coverage Tasks", ""])
    if manifest["tasks"]:
        for task in manifest["tasks"]:
            lines.append(f"- [{task['priority'].upper()}] {task['title']} ({task['mode']}, {task['component']})")
            lines.append(f"  - {task['description']}")
            for action in task["suggested_actions"]:
                lines.append(f"  - action: {action}")
            lines.append("")
    else:
        lines.append("No tasks. Pipeline and notion coverage are within configured expectations.")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review Notion + pipeline alignment")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root",
    )
    parser.add_argument(
        "--sync-config",
        default="scripts/sync-config.json",
        help="Notion sync config path",
    )
    parser.add_argument(
        "--pipeline-config",
        default="training/vertex_pipeline_config.yaml",
        help="Training pipeline config path",
    )
    parser.add_argument(
        "--training-data",
        default="training-data",
        help="Training-data output directory",
    )
    parser.add_argument(
        "--output",
        default="artifacts/notion_pipeline_gap_review.json",
        help="Output review JSON path",
    )
    parser.add_argument(
        "--summary-path",
        default="artifacts/notion_pipeline_gap_review.md",
        help="Output summary markdown path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    sync_config = Path(args.sync_config)
    pipeline_config = Path(args.pipeline_config)
    training_data = Path(args.training_data)

    if not sync_config.is_absolute():
        sync_config = repo_root / sync_config
    if not pipeline_config.is_absolute():
        pipeline_config = repo_root / pipeline_config
    if not training_data.is_absolute():
        training_data = repo_root / training_data

    manifest = run_gap_review(repo_root, sync_config, pipeline_config, training_data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_summary(Path(args.summary_path), manifest)

    print(f"Notion gap review written to {output_path}")
    print(f"Notion gap summary written to {args.summary_path}")
    print(f"Total tasks: {manifest['summary']['total_tasks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
