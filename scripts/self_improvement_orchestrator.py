#!/usr/bin/env python3
"""Self-Improvement Agent Loop for SCBE-AETHERMOORE.

Modes:
- code-assistant: converts reliability/coherence signals into concrete coding tasks
- ai-nodal-dev-specialist: assigns tasks to role lanes for execution planning
- fine-tune-funnel: audits Notion-to-HF dual-stream training funnel health
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ImprovementTask:
    task_id: str
    mode: str
    title: str
    description: str
    component: str
    tongue: str
    priority: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)


def _hash_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_coherence(path: Path) -> Dict[str, Any]:
    data = _safe_load_json(path) or {}
    if not data:
        return {"status": "missing", "coherence": 1.0, "metrics": {}, "details": {}}
    return data


def _coherence_tasks(coherence: Dict[str, Any]) -> List[ImprovementTask]:
    tasks: List[ImprovementTask] = []
    metrics = coherence.get("metrics", {})

    def add(metric: str, value: float, threshold: float, priority: str) -> None:
        if value >= threshold:
            return
        tasks.append(
            ImprovementTask(
                task_id=_hash_id("code", metric, str(value)),
                mode="code-assistant",
                title=f"Restore {metric} gate",
                description=(
                    f"Coherence metric `{metric}` is {value:.2f} and below threshold {threshold:.2f}."
                ),
                component="Layer 11 Coherence",
                tongue="KO",
                priority=priority,
                confidence=0.84,
                evidence={"metric": metric, "value": value, "threshold": threshold},
                suggested_actions=[
                    "Inspect the exact step that produced this metric.",
                    "Patch root cause and re-run the failing command.",
                    "Attach a concise root-cause note in the next improvement issue.",
                ],
            )
        )

    if coherence.get("status") != "pass":
        tasks.append(
            ImprovementTask(
                task_id=_hash_id("code", "coherence", coherence.get("status", "fail")),
                mode="code-assistant",
                title="Resume from coherence failure before merge/release",
                description="Layer 11 coherence status is failing and should be treated as a release gate.",
                component="Daily Review Workflow",
                tongue="DR",
                priority="critical",
                confidence=0.98,
                evidence={"status": coherence.get("status"), "coherence": coherence.get("coherence", 0)},
                suggested_actions=[
                    "Create a focused hotfix branch for the failing checks.",
                    "Validate test/lint/typecheck manually and regenerate coherence artifact.",
                ],
            )
        )

    for metric, threshold, priority in (
        ("test_pass_rate", 1.0, "critical"),
        ("type_coverage", 1.0, "high"),
        ("lint_score", 1.0, "high"),
        ("doc_coverage", 0.9, "medium"),
    ):
        value = metrics.get(metric)
        if value is not None:
            add(metric, float(value), threshold, priority)

    return tasks


def _notion_gap_review_tasks(gap_report: Path) -> List[ImprovementTask]:
    data = _safe_load_json(gap_report) or {}
    tasks_payload = data.get("tasks", [])
    if not isinstance(tasks_payload, list):
        return []

    tasks: List[ImprovementTask] = []
    for item in tasks_payload:
        if not isinstance(item, dict):
            continue

        priority = str(item.get("priority", "medium")).lower()
        if priority not in {"critical", "high", "medium", "low"}:
            priority = "medium"

        title = str(item.get("title", "").strip()) or "Review Notion/AI pipeline gap"
        description = str(item.get("description", "").strip()) or "Gap review produced no detailed description."
        component = str(item.get("component", "Notion + pipeline health"))
        mode = str(item.get("mode", "code-assistant")).lower()
        if mode not in {"code-assistant", "ai-nodal-dev-specialist", "fine-tune-funnel"}:
            mode = "code-assistant"

        confidence = item.get("confidence", 0.77)
        if not isinstance(confidence, (int, float)):
            confidence = 0.77

        tasks.append(
            ImprovementTask(
                task_id=_hash_id("gap", gap_report.name, title, component),
                mode=mode,
                title=title,
                description=description,
                component=component,
                tongue="KO",
                priority=priority,
                confidence=float(confidence),
                evidence={
                    "source": "scripts/notion_pipeline_gap_review.py",
                    "source_path": str(gap_report),
                    "status": data.get("status"),
                    "evidence": item.get("evidence", {}),
                },
                suggested_actions=[
                    "Open artifacts/notion_pipeline_gap_review.md and implement the referenced remediation.",
                    "Re-run the notion pipeline review after updates.",
                ],
            )
        )

    return tasks


def _dedupe_tasks(tasks: List[ImprovementTask]) -> List[ImprovementTask]:
    seen = set()
    deduped: List[ImprovementTask] = []
    for task in tasks:
        key = (task.mode, task.title, task.component)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    return deduped


def _mode_fallback_task(mode_name: str, result: Dict[str, Any], priority: str = "low") -> ImprovementTask:
    return ImprovementTask(
        task_id=_hash_id("si", mode_name, result.get("status", "missing")),
        mode=mode_name,
        title=f"No strong signal for {mode_name} in this run",
        description="No strong telemetry signal was found for this mode.",
        component="Self-improvement orchestrator",
        tongue="UM",
        priority=priority,
        confidence=0.41,
        evidence=result,
        suggested_actions=["Capture richer telemetry artifacts in next run."],
    )


def _read_jsonl_records(training_data_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for source in sorted(training_data_path.glob("*.jsonl")):
        try:
            for line in source.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                records.append(json.loads(line))
        except Exception:
            continue
    return records


def _fine_tune_funnel_tasks(training_data_path: Path, config: Dict[str, Any]) -> List[ImprovementTask]:
    records = _read_jsonl_records(training_data_path)
    streams = (config.get("fine_tune") or {}).get("streams", [])
    if not streams:
        return [_mode_fallback_task("fine-tune-funnel", {"training_data_path": str(training_data_path)})]

    if not records:
        return [
            ImprovementTask(
                task_id=_hash_id("fine", "tune", "empty"),
                mode="fine-tune-funnel",
                title="Seed Notion export for dual-stream training data",
                description="No JSONL training rows were found in training-data/.",
                component="Notion-to-Dataset Pipeline",
                tongue="CA",
                priority="high",
                confidence=0.93,
                evidence={"training_data_path": str(training_data_path)},
                suggested_actions=[
                    "Run notion-to-dataset workflow first.",
                    "Verify NOTION_TOKEN has read permission for both technical and lore spaces.",
                ],
            )
        ]

    category_counts: Dict[str, int] = {}
    for record in records:
        for cat in record.get("categories", []):
            category_counts[cat] = category_counts.get(cat, 0) + 1

    tasks: List[ImprovementTask] = []
    total = len(records)

    def record_count_for(stream: Dict[str, Any]) -> int:
        categories = {x.lower() for x in stream.get("categories", [])}
        return sum(1 for row in records if categories.intersection({c.lower() for c in row.get("categories", [])}))

    for stream in streams:
        if not isinstance(stream, dict):
            continue
        name = stream.get("name", "unknown-stream")
        lane = stream.get("lane", "canonical")
        required_min = int(stream.get("required_min_records", 0) or 0)
        count = record_count_for(stream)
        coverage = count / total if total else 0.0

        if required_min and count < required_min:
            tasks.append(
                ImprovementTask(
                    task_id=_hash_id("fine", name, str(count), str(required_min)),
                    mode="fine-tune-funnel",
                    title=f"Increase {name} records",
                    description=(
                        f"Stream '{name}' is {count}/{required_min} records ({coverage:.2%} of corpus)."
                    ),
                    component="Fine-tune Funnel",
                    tongue="RU" if lane == "emotional" else "KO",
                    priority="high" if coverage < 0.20 else "medium",
                    confidence=0.81,
                    evidence={
                        "stream": stream,
                        "record_count": count,
                        "coverage": coverage,
                        "category_counts": category_counts,
                    },
                    suggested_actions=[
                        "Add missing docs to the relevant Notion sync page set.",
                        "Tag and rebalance around dual-stream split ratios.",
                        "Re-run notion-to-dataset and verify manifest update.",
                    ],
                )
            )

    if not tasks:
        tasks.append(
            ImprovementTask(
                task_id=_hash_id("fine", "funnel", "balanced"),
                mode="fine-tune-funnel",
                title="Fine-tune funnel remains healthy",
                description="Both canonical and emotional streams meet minimum volume targets.",
                component="Fine-tune Funnel",
                tongue="DR",
                priority="low",
                confidence=0.58,
                evidence={"total_records": total, "streams": [s.get("name") for s in streams]},
                suggested_actions=[
                    "Archive this funnel snapshot for model training lineage.",
                    "Monitor stream drift at next weekly run.",
                ],
            )
        )

    return tasks


def _ai_nodal_tasks(code_tasks: List[ImprovementTask], training_tasks: List[ImprovementTask]) -> List[ImprovementTask]:
    tasks: List[ImprovementTask] = []
    if code_tasks:
        tasks.append(
            ImprovementTask(
                task_id=_hash_id("ai", "nodal", "routing"),
                mode="ai-nodal-dev-specialist",
                title="Route code tasks to repair lanes",
                description="Repair tasks were generated and should be assigned by tongue lanes.",
                component="Task Coordination",
                tongue="AV",
                priority="medium",
                confidence=0.73,
                evidence={"code_task_count": len(code_tasks), "task_ids": [t.task_id for t in code_tasks[:6]]},
                suggested_actions=[
                    "Assign KO tasks to code execution, RU to research traceability, DR to final risk checks.",
                    "Execute in small batches with release notes in session artifact.",
                ],
            )
        )

    if any(task.priority == "critical" for task in code_tasks + training_tasks):
        tasks.append(
            ImprovementTask(
                task_id=_hash_id("ai", "nodal", "critical"),
                mode="ai-nodal-dev-specialist",
                title="Escalate critical self-improvement findings",
                description="Critical issues were detected and should pause automation until resolved.",
                component="Release Coordination",
                tongue="DR",
                priority="high",
                confidence=0.86,
                evidence={
                    "critical_count": len([t for t in code_tasks + training_tasks if t.priority == "critical"])
                },
                suggested_actions=[
                    "Hold next release candidate.",
                    "Run only security and coherence verification until fixed.",
                ],
            )
        )

    if not tasks:
        tasks.append(_mode_fallback_task("ai-nodal-dev-specialist", {"status": "idle"}))

    return tasks


def _build_summary(tasks: List[ImprovementTask]) -> Dict[str, Any]:
    priority_counts: Dict[str, int] = {}
    mode_counts: Dict[str, int] = {}
    for task in tasks:
        priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
        mode_counts[task.mode] = mode_counts.get(task.mode, 0) + 1
    critical_count = priority_counts.get("critical", 0)
    return {
        "total_tasks": len(tasks),
        "critical_tasks": critical_count,
        "priority_breakdown": priority_counts,
        "mode_breakdown": mode_counts,
        "release_safe": critical_count == 0,
    }


def _write_summary_markdown(manifest: Dict[str, Any], output_path: Path) -> None:
    summary = manifest["summary"]
    lines: List[str] = [
        "# Self-Improvement Agent Loop",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Mode: {manifest['requested_mode']}",
        f"Total tasks: {summary['total_tasks']}",
        f"Critical tasks: {summary['critical_tasks']}",
        f"Release safe: {summary['release_safe']}",
        "",
        "## Priority Breakdown",
    ]

    for key, value in sorted(summary["priority_breakdown"].items()):
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Task List")
    for task in manifest["tasks"]:
        lines.append(f"- **[{task['priority'].upper()}] {task['title']}** ({task['mode']}, {task['component']})")
        lines.append(f"  - {task['description']}")
        if task["suggested_actions"]:
            lines.append("  - Suggested actions:")
            for action in task["suggested_actions"]:
                lines.append(f"    - {action}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def _load_fine_tune_config(config_path: Path) -> Dict[str, Any]:
    text = config_path.read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass

    # Minimal YAML fallback for the parts we need.
    data: Dict[str, Any] = {}
    in_fine_tune = False
    in_streams = False
    streams: List[Dict[str, Any]] = []
    active_stream: Optional[Dict[str, Any]] = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*$", line):
            key = line[:-1]
            in_fine_tune = key == "fine_tune"
            in_streams = False
            if in_fine_tune and "fine_tune" not in data:
                data["fine_tune"] = {}
            active_stream = None
            continue

        if not in_fine_tune:
            continue

        if re.match(r"^\s+streams:\s*$", line):
            in_streams = True
            continue

        if re.match(r"^\s+quality_checks:\s*$", line):
            in_streams = False
            continue

        if in_streams and re.match(r"^\s{4}-\s+name:\s+", line):
            value = line.split(":", 1)[1].strip()
            active_stream = {"name": value}
            streams.append(active_stream)
            continue

        if in_streams and active_stream is not None and re.match(r"^\s{6}[A-Za-z_][A-Za-z0-9_-]*:\s*", line):
            key, value = [part.strip() for part in line.split(":", 1)]
            if not value:
                continue
            key = key.strip()
            if key == "categories":
                continue
            if value.lower() in {"true", "false"}:
                active_stream[key] = value.lower() == "true"
            elif re.match(r"^-?\d+\.\d+$", value):
                active_stream[key] = float(value)
            elif re.match(r"^-?\d+$", value):
                active_stream[key] = int(value)
            else:
                active_stream[key] = value
            continue

        if in_streams and active_stream is not None and re.match(r"^\s{8}-\s+", line):
            # Preserve explicit stream categories from YAML list entries
            entry = line.split("-", 1)[1].strip().strip("'\"")
            if entry:
                active_stream.setdefault("categories", []).append(entry)

        if in_streams and active_stream is None and re.match(r"^\s{4}-\s*", line):
            # ignore malformed stream items
            continue

    if in_fine_tune:
        data["fine_tune"]["streams"] = streams

        # Try to parse quality checks linearly
        quality_checks: Dict[str, Any] = {}
        for line in text.splitlines():
            if re.match(r"^\s+quality_checks:\s*$", line):
                continue
            q_match = re.match(r"^\s{4}([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", line)
            if q_match and data.get("fine_tune") is not None:
                key, val = q_match.group(1), q_match.group(2).strip()
                if val.lower() in {"true", "false"}:
                    quality_checks[key] = val.lower() == "true"
                elif re.match(r"^-?\d+\.\d+$", val):
                    quality_checks[key] = float(val)
                elif re.match(r"^-?\d+$", val):
                    quality_checks[key] = int(val)
                else:
                    quality_checks[key] = val
        if quality_checks:
            data["fine_tune"]["quality_checks"] = quality_checks

    return data


def run_self_improvement(
    mode: str,
    repo_root: Path,
    coherence_report: Path,
    training_data: Path,
    config_data: Dict[str, Any],
    notion_gap_report: Optional[Path] = None,
) -> Dict[str, Any]:
    coherence = _read_coherence(coherence_report)
    code_tasks: List[ImprovementTask] = []
    training_tasks: List[ImprovementTask] = []
    ai_tasks: List[ImprovementTask] = []

    if mode in {"all", "code-assistant"}:
        code_tasks = _coherence_tasks(coherence)
        if notion_gap_report and notion_gap_report.exists():
            code_tasks.extend(_notion_gap_review_tasks(notion_gap_report))

    if mode in {"all", "fine-tune-funnel"}:
        training_tasks = _fine_tune_funnel_tasks(training_data, config_data)

    if mode in {"all", "ai-nodal-dev-specialist"}:
        ai_tasks = _ai_nodal_tasks(code_tasks, training_tasks)

    tasks = code_tasks + training_tasks + ai_tasks
    if not tasks:
        tasks = [_mode_fallback_task("orchestrator", {"status": "no_findings", "mode": mode})]

    tasks = _dedupe_tasks(tasks)

    manifest: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "requested_mode": mode,
        "coherence_report": str(coherence_report),
        "summary": _build_summary(tasks),
        "coherence": coherence,
        "training_data_path": str(training_data),
        "pipeline_config": "training/vertex_pipeline_config.yaml",
        "tasks": [asdict(task) for task in tasks],
    }

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE self-improvement loop")
    parser.add_argument(
        "--mode",
        default="all",
        choices=("all", "code-assistant", "ai-nodal-dev-specialist", "fine-tune-funnel"),
        help="Agent mode",
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")
    parser.add_argument(
        "--coherence-report",
        default="coherence-report.json",
        help="Path to coherence report file",
    )
    parser.add_argument(
        "--training-data",
        default=str(REPO_ROOT / "training-data"),
        help="Path to exported training data",
    )
    parser.add_argument(
        "--pipeline-config",
        default=str(REPO_ROOT / "training" / "vertex_pipeline_config.yaml"),
        help="Path to vertex pipeline config",
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "artifacts" / "self_improvement_manifest.json"),
        help="Output artifact JSON",
    )
    parser.add_argument(
        "--summary-path",
        default=str(REPO_ROOT / "artifacts" / "self_improvement_summary.md"),
        help="Optional summary markdown path",
    )
    parser.add_argument(
        "--notion-gap-report",
        default="",
        help="Optional gap review JSON from notion/pipeline review",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coherence_report = Path(args.coherence_report)
    if not coherence_report.is_absolute():
        coherence_report = repo_root / coherence_report
    training_data = Path(args.training_data)
    if not training_data.is_absolute():
        training_data = repo_root / training_data
    config_path = Path(args.pipeline_config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    if config_path.exists():
        config_data = _load_fine_tune_config(config_path)
    else:
        config_data = {}

    notion_gap_report = Path(args.notion_gap_report) if args.notion_gap_report else None
    if notion_gap_report and not notion_gap_report.is_absolute():
        notion_gap_report = repo_root / notion_gap_report

    manifest = run_self_improvement(
        args.mode,
        repo_root,
        coherence_report,
        training_data,
        config_data,
        notion_gap_report=notion_gap_report,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary_path = Path(args.summary_path)
    _write_summary_markdown(manifest, summary_path)

    print(f"Self-improvement manifest written to {output_path}")
    print(f"Self-improvement summary written to {summary_path}")
    print(f"Task count: {manifest['summary']['total_tasks']}")
    print(f"Critical tasks: {manifest['summary']['critical_tasks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
