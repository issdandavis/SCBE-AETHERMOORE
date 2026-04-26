"""Collect saved Colab run receipts into reports and SFT records.

The Colab lane is remote compute; repo-local datasets are the source of truth.
This collector turns browser smoke tests, handoff packets, execution receipts,
and service logs into a compact inventory plus supervised records that teach
the operator model what actually happened during each run.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = ROOT / "artifacts"
DEFAULT_REPORT_DIR = DEFAULT_ARTIFACTS / "training_reports"
DEFAULT_SFT_PATH = ROOT / "training-data" / "sft" / "colab_run_evidence_v1.sft.jsonl"
DEFAULT_MANIFEST_PATH = ROOT / "training-data" / "sft" / "colab_run_evidence_v1_manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return {"_read_error": str(exc)}
    return data if isinstance(data, dict) else {"_value": data}


def short_text(value: Any, limit: int = 700) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    value = value.replace("\r", "").strip()
    return value[:limit]


def sanitize_log_line(value: str) -> str:
    """Keep operational signal without leaking noisy local/browser details."""
    replacements = {
        "--password-store=basic": "--browser-password-store=<redacted>",
        '"token_result"': '"auth_result"',
        '"token_sanitized"': '"auth_sanitized"',
        "token_result": "auth_result",
        "token_sanitized": "auth_sanitized",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    if "<launching>" in value and "chrome.exe" in value:
        return "  - <launching> chromium browser with Colab worker flags <redacted>"
    return value


def file_exists(path_text: str | None) -> bool:
    if not path_text:
        return False
    return Path(path_text).exists()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def classify_execute(data: dict[str, Any]) -> str:
    trainer = data.get("trainer_result")
    install = data.get("install_result")
    runtime_wait = data.get("runtime_wait", {})
    runtime_after = data.get("runtime_after", {})
    if isinstance(trainer, dict):
        if trainer.get("success") or trainer.get("ok"):
            return "trainer_completed"
        if trainer.get("error") or trainer.get("stderr"):
            return "trainer_error"
    if trainer is None and install is None:
        state = runtime_after.get("kernel_state") if isinstance(runtime_after, dict) else ""
        ready = runtime_wait.get("ready") if isinstance(runtime_wait, dict) else None
        if state == "allocating" or ready is False:
            return "runtime_allocation_only"
        return "notebook_open_no_execution"
    return "partial_execution"


def collect_smoke(artifacts_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((artifacts_root / "colab_smoke").glob("*/result.json")):
        data = read_json(path)
        notebook = data.get("notebook", {})
        cells = data.get("cells_before", {})
        rows.append(
            {
                "kind": "smoke",
                "path": rel(path),
                "session": path.parent.name,
                "schema": data.get("schema_version") or data.get("schema"),
                "notebook": notebook.get("name") if isinstance(notebook, dict) else "",
                "title": data.get("title"),
                "url": data.get("current_url"),
                "cell_count": cells.get("cell_count") if isinstance(cells, dict) else None,
                "code_cell_count": cells.get("code_cell_count") if isinstance(cells, dict) else None,
                "markdown_cell_count": cells.get("markdown_cell_count") if isinstance(cells, dict) else None,
                "runtime_state": (data.get("runtime_after") or data.get("runtime_before") or {}).get("kernel_state")
                if isinstance(data.get("runtime_after") or data.get("runtime_before") or {}, dict)
                else None,
                "screenshot": file_exists(str(path.parent / "page.png")),
                "classification": "browser_verified_notebook",
            }
        )
    return rows


def collect_handoffs(artifacts_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((artifacts_root / "colab_training_handoffs").rglob("*.json")):
        data = read_json(path)
        if path.name == "colab_training_handoff.json":
            preflight = data.get("preflight", {})
            plan = preflight.get("plan", {}) if isinstance(preflight, dict) else {}
            deps = preflight.get("dependencies", {}) if isinstance(preflight, dict) else {}
            rows.append(
                {
                    "kind": "handoff",
                    "path": rel(path),
                    "session": path.parent.name,
                    "schema": data.get("schema_version"),
                    "profile_id": data.get("profile_id"),
                    "mission_id": data.get("mission_id"),
                    "dry_run": data.get("dry_run"),
                    "notebook": data.get("notebook", {}).get("name")
                    if isinstance(data.get("notebook"), dict)
                    else "",
                    "notebook_path": data.get("notebook", {}).get("path")
                    if isinstance(data.get("notebook"), dict)
                    else "",
                    "backend": plan.get("backend") if isinstance(plan, dict) else None,
                    "base_model": plan.get("base_model") if isinstance(plan, dict) else None,
                    "recommended_target": preflight.get("recommended_target") if isinstance(preflight, dict) else None,
                    "plan_ready": preflight.get("plan_ready") if isinstance(preflight, dict) else None,
                    "dependencies": deps,
                    "classification": "handoff_ready" if data.get("dry_run") else "handoff_live",
                }
            )
        elif "error" in path.name:
            rows.append(
                {
                    "kind": "handoff_error",
                    "path": rel(path),
                    "session": path.parent.parent.name if path.parent.name == "worker" else path.parent.name,
                    "state": data.get("state"),
                    "dry_run": data.get("dry_run"),
                    "error_type": data.get("error_type"),
                    "error": short_text(data.get("error"), 500),
                    "classification": "browser_worker_blocked",
                }
            )
        elif "session" in path.name:
            probe = data.get("runtime_probe", {})
            rows.append(
                {
                    "kind": "worker_session",
                    "path": rel(path),
                    "session": path.parent.parent.name if path.parent.name == "worker" else path.parent.name,
                    "state": data.get("state"),
                    "title": data.get("title"),
                    "url": data.get("current_url"),
                    "headless": data.get("headless"),
                    "notebook_loaded": probe.get("notebook_loaded") if isinstance(probe, dict) else None,
                    "runtime_state": probe.get("kernel_state") if isinstance(probe, dict) else None,
                    "screenshot": file_exists(data.get("screenshot_path")),
                    "classification": "browser_worker_verified",
                }
            )
    return rows


def collect_execute(artifacts_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((artifacts_root / "colab_training_execute").rglob("result.json")):
        data = read_json(path)
        cells = data.get("cells_before", {})
        runtime_wait = data.get("runtime_wait", {})
        runtime_after = data.get("runtime_after", {})
        rows.append(
            {
                "kind": "execute_result",
                "path": rel(path),
                "session": path.parent.name,
                "profile_id": data.get("profile_id"),
                "schema": data.get("schema_version"),
                "cell_count": cells.get("cell_count") if isinstance(cells, dict) else None,
                "code_cell_count": cells.get("code_cell_count") if isinstance(cells, dict) else None,
                "runtime_ready": runtime_wait.get("ready") if isinstance(runtime_wait, dict) else None,
                "runtime_state": runtime_after.get("kernel_state") if isinstance(runtime_after, dict) else None,
                "trainer_present": data.get("trainer_result") is not None,
                "install_present": data.get("install_result") is not None,
                "bootstrap_present": data.get("bootstrap_result") is not None,
                "screenshot": file_exists(data.get("screenshot_path")),
                "classification": classify_execute(data),
            }
        )
    for path in sorted((artifacts_root / "colab_training_execute").rglob("status.json")):
        data = read_json(path)
        payload = data.get("payload", {})
        rows.append(
            {
                "kind": "execute_status",
                "path": rel(path),
                "session": path.parent.name,
                "updated_at_utc": data.get("updated_at_utc"),
                "stage": data.get("stage"),
                "payload_classification": classify_execute(payload) if isinstance(payload, dict) else None,
                "classification": "status_receipt",
            }
        )
    return rows


def collect_runs(artifacts_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((artifacts_root / "colab_training_runs").rglob("*.json")):
        data = read_json(path)
        rows.append(
            {
                "kind": "run_packet",
                "path": rel(path),
                "profile": path.parts[-3] if len(path.parts) >= 3 else "",
                "session": path.parent.name,
                "schema": data.get("schema_version"),
                "keys": sorted(data.keys())[:20],
                "profile_id": data.get("profile_id"),
                "mission_id": data.get("mission_id"),
                "status": data.get("status") or data.get("state"),
                "classification": "run_packet",
            }
        )
    return rows


def collect_service_logs(artifacts_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    needles = ("error", "traceback", "failed", "blocked", "success", "trainer_result", "runtime_after")
    for path in sorted((artifacts_root / "colab_training_service").rglob("service.log")):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        hits = [sanitize_log_line(line.strip()) for line in lines if any(n in line.lower() for n in needles)]
        classification = "service_log"
        if any("modulenotfounderror" in hit.lower() or "targetclosederror" in hit.lower() for hit in hits):
            classification = "service_error"
        elif any("trainer_result" in hit.lower() for hit in hits):
            classification = "service_result_dump"
        rows.append(
            {
                "kind": "service_log",
                "path": rel(path),
                "profile": path.parts[-3] if len(path.parts) >= 3 else "",
                "session": path.parent.name,
                "line_count": len(lines),
                "hit_count": len(hits),
                "tail": [sanitize_log_line(line) for line in lines[-12:]],
                "signals": hits[-12:],
                "classification": classification,
            }
        )
    return rows


def build_sft_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        prompt = (
            "Classify this saved SCBE Colab run receipt. "
            "Return the evidence path, what happened, whether it is promotion evidence, "
            "and the next operational action.\n\n"
            f"Receipt:\n{json.dumps(row, ensure_ascii=True, sort_keys=True)}"
        )
        cls = row.get("classification")
        promotion = cls in {"trainer_completed"}
        if cls in {"runtime_allocation_only", "notebook_open_no_execution", "browser_verified_notebook"}:
            next_action = "Do not promote. Reopen in browser/sidebar, verify runtime connection, then rerun execution cells."
        elif cls in {"browser_worker_blocked", "service_error"}:
            next_action = "Fix local browser/Playwright/module issue, then retry the Colab worker."
        elif promotion:
            next_action = "Run frozen eval and register adapter only if eval gates pass."
        else:
            next_action = "Keep as audit evidence and correlate with matching training output before promotion."
        answer = {
            "evidence_path": row.get("path"),
            "classification": cls,
            "promotion_evidence": promotion,
            "next_action": next_action,
        }
        records.append(
            {
                "messages": [
                    {"role": "system", "content": "You are an SCBE Colab training evidence triage assistant."},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": json.dumps(answer, ensure_ascii=True, sort_keys=True)},
                ],
                "metadata": {
                    "source": "colab_run_evidence_v1",
                    "row_index": idx,
                    "kind": row.get("kind"),
                    "classification": cls,
                    "promotion_evidence": promotion,
                },
            }
        )
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Colab Saved Run Inventory",
        "",
        f"Generated: `{summary['generated_at_utc']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary["counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Operational Finding", ""])
    if summary["counts_by_classification"].get("trainer_completed", 0):
        lines.append("- At least one Colab receipt is trainer-completed and should move to frozen eval.")
    else:
        lines.append(
            "- No saved Colab receipt found here is completed trainer output. The recovered evidence is browser, handoff, runtime-allocation, and service-log evidence."
        )
    lines.append("- These records are still useful: they teach the operator what failed, what was verified, and what must be fixed before promotion.")
    lines.extend(["", "## Classification Counts", ""])
    for key, value in sorted(summary["counts_by_classification"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Key Receipts", ""])
    for row in rows:
        if row.get("kind") in {"smoke", "execute_result", "handoff_error", "worker_session", "service_log"}:
            desc = row.get("notebook") or row.get("profile_id") or row.get("profile") or row.get("session")
            lines.append(f"- `{row['classification']}` | `{row['kind']}` | `{desc}` | `{row['path']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-root", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--sft-path", type=Path, default=DEFAULT_SFT_PATH)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    rows.extend(collect_smoke(args.artifacts_root))
    rows.extend(collect_handoffs(args.artifacts_root))
    rows.extend(collect_execute(args.artifacts_root))
    rows.extend(collect_runs(args.artifacts_root))
    rows.extend(collect_service_logs(args.artifacts_root))

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
        cls = str(row.get("classification"))
        class_counts[cls] = class_counts.get(cls, 0) + 1

    report = {
        "schema_version": "scbe_colab_run_evidence_inventory_v1",
        "generated_at_utc": generated,
        "source_root": rel(args.artifacts_root),
        "counts": counts,
        "counts_by_classification": class_counts,
        "rows": rows,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "colab_saved_runs_inventory_20260426.json"
    md_path = args.report_dir / "colab_saved_runs_inventory_20260426.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md_path, report, rows)

    records = build_sft_records(rows)
    write_jsonl(args.sft_path, records)
    manifest = {
        "schema_version": "scbe_sft_manifest_v1",
        "generated_at_utc": generated,
        "source_report": rel(json_path),
        "output": rel(args.sft_path),
        "record_count": len(records),
        "counts": counts,
        "counts_by_classification": class_counts,
        "promotion_evidence_count": sum(1 for record in records if record["metadata"]["promotion_evidence"]),
    }
    args.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"report": rel(json_path), "markdown": rel(md_path), "sft": rel(args.sft_path), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
