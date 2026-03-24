#!/usr/bin/env python3
"""Run a long-form Colab smoke sweep across one or more SCBE notebooks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.system import colab_notebook_smoke as smoke
from scripts.system import colab_workflow_catalog as catalog


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "colab_soak"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _select_notebooks(
    *,
    names: list[str],
    categories: list[str],
    limit: int,
    include_missing: bool,
) -> list[dict[str, Any]]:
    if names:
        selected = [catalog.resolve_notebook_payload(name) for name in names]
    else:
        selected = catalog.list_notebook_payloads()

    if categories:
        wanted = {item.strip().lower() for item in categories if item.strip()}
        selected = [row for row in selected if str(row.get("category", "")).lower() in wanted]

    if not include_missing:
        selected = [row for row in selected if bool(row.get("exists"))]

    if limit > 0:
        selected = selected[:limit]
    return selected


def _classify_result(result: dict[str, Any]) -> dict[str, Any]:
    runtime_after_connect = dict(result.get("runtime_after_connect") or {})
    smoke_result = dict(result.get("smoke_result") or {})
    output_result = dict(smoke_result.get("output_result") or {})
    runtime_attached = smoke._runtime_attached(runtime_after_connect)
    smoke_success = bool(smoke_result.get("success"))
    return {
        "name": result["notebook"]["name"],
        "category": result["notebook"]["category"],
        "opened": bool(result.get("cells_before", {}).get("cell_count")),
        "runtime_attached": runtime_attached,
        "kernel_state": runtime_after_connect.get("kernel_state", ""),
        "connect_clicked": bool(result.get("connect_result", {}).get("clicked")),
        "smoke_success": smoke_success,
        "execution_count": output_result.get("execution_count"),
        "output_count": output_result.get("output_count"),
        "artifact_path": result.get("artifact_path", ""),
        "screenshot_path": result.get("screenshot_path", ""),
        "failure_stage": smoke_result.get("stage", ""),
    }


def run_soak(
    *,
    notebooks: list[dict[str, Any]],
    profile_dir: Path,
    artifact_root: Path,
    headless: bool,
    timeout_ms: int,
    connect_runtime: bool,
    connect_attempts: int,
    connect_wait_ms: int,
    run_smoke_cell: bool,
    smoke_code: str,
) -> dict[str, Any]:
    stamp = _utc_stamp()
    artifact_dir = artifact_root / f"soak-{stamp}"
    runs_root = artifact_dir / "runs"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    raw_results: list[dict[str, Any]] = []
    for notebook in notebooks:
        try:
            result = smoke.run_notebook_smoke(
                notebook_query=str(notebook["name"]),
                profile_dir=profile_dir,
                artifact_root=runs_root,
                headless=headless,
                timeout_ms=timeout_ms,
                connect_runtime=connect_runtime,
                connect_attempts=connect_attempts,
                connect_wait_ms=connect_wait_ms,
                run_smoke_cell=run_smoke_cell,
                smoke_code=smoke_code,
            )
            raw_results.append(result)
            rows.append(_classify_result(result))
        except Exception as exc:  # pragma: no cover - exercised in live runs
            rows.append(
                {
                    "name": notebook["name"],
                    "category": notebook["category"],
                    "opened": False,
                    "runtime_attached": False,
                    "kernel_state": "",
                    "connect_clicked": False,
                    "smoke_success": False,
                    "execution_count": None,
                    "output_count": None,
                    "artifact_path": "",
                    "screenshot_path": "",
                    "failure_stage": "exception",
                    "error": str(exc),
                }
            )

    summary = {
        "schema_version": "scbe_colab_soak_v1",
        "artifact_root": str(artifact_dir),
        "headless": headless,
        "profile_dir": str(profile_dir),
        "connect_runtime": connect_runtime,
        "connect_attempts": connect_attempts,
        "connect_wait_ms": connect_wait_ms,
        "run_smoke_cell": run_smoke_cell,
        "notebook_count": len(rows),
        "opened_count": sum(1 for row in rows if row["opened"]),
        "runtime_attached_count": sum(1 for row in rows if row["runtime_attached"]),
        "smoke_success_count": sum(1 for row in rows if row["smoke_success"]),
        "rows": rows,
    }
    summary_path = artifact_dir / "summary.json"
    raw_path = artifact_dir / "raw_results.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    raw_path.write_text(json.dumps(raw_results, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    summary["raw_results_path"] = str(raw_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a long-form Colab smoke sweep.")
    parser.add_argument(
        "--notebook", action="append", default=[], help="Notebook name or alias. Repeat to select multiple."
    )
    parser.add_argument(
        "--category", action="append", default=[], help="Notebook category filter. Repeat to select multiple."
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum notebooks to test.")
    parser.add_argument(
        "--include-missing", action="store_true", help="Include catalog entries whose local files are missing."
    )
    parser.add_argument("--profile-dir", default=str(smoke.DEFAULT_PROFILE_DIR))
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-ms", type=int, default=90000)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--connect-runtime", action="store_true")
    parser.add_argument("--connect-attempts", type=int, default=smoke.DEFAULT_CONNECT_ATTEMPTS)
    parser.add_argument("--connect-wait-ms", type=int, default=smoke.DEFAULT_CONNECT_WAIT_MS)
    parser.add_argument("--run-smoke-cell", action="store_true")
    parser.add_argument("--smoke-code", default=smoke.DEFAULT_SMOKE_CODE)
    parser.set_defaults(headless=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    notebooks = _select_notebooks(
        names=list(args.notebook),
        categories=list(args.category),
        limit=max(0, int(args.limit)),
        include_missing=bool(args.include_missing),
    )
    summary = run_soak(
        notebooks=notebooks,
        profile_dir=Path(args.profile_dir),
        artifact_root=Path(args.artifact_root),
        headless=bool(args.headless),
        timeout_ms=int(args.timeout_ms),
        connect_runtime=bool(args.connect_runtime),
        connect_attempts=max(1, int(args.connect_attempts)),
        connect_wait_ms=max(500, int(args.connect_wait_ms)),
        run_smoke_cell=bool(args.run_smoke_cell),
        smoke_code=args.smoke_code,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
