#!/usr/bin/env python3
"""Check whether the local harness benchmark packet is release-ready.

This is intentionally an evidence check, not a model-capability claim. It reads
the latest local benchmark artifacts and reports whether the harness surface has
the receipts needed to say it is operational.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "harness_release_readiness"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _artifact(
    path: Path, checks: dict[str, bool], details: dict[str, Any] | None = None
) -> dict[str, Any]:
    ok = path.exists() and all(checks.values())
    return {
        "path": str(
            path.relative_to(REPO_ROOT)
            if path.is_absolute() and path.is_relative_to(REPO_ROOT)
            else path
        ),
        "exists": path.exists(),
        "ok": ok,
        "checks": checks,
        "details": details or {},
    }


def build_report(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    cli_path = (
        REPO_ROOT
        / "artifacts"
        / "benchmarks"
        / "cli_competitive"
        / "cli_competitive_benchmark_latest.json"
    )
    wedge_path = (
        REPO_ROOT
        / "artifacts"
        / "benchmarks"
        / "agentbus_competitive_wedge"
        / "latest_report.json"
    )
    operator_path = (
        REPO_ROOT
        / "artifacts"
        / "benchmarks"
        / "operator_agent_bus_eval"
        / "latest_report.json"
    )
    checklist_path = (
        REPO_ROOT
        / "artifacts"
        / "benchmarks"
        / "workflow_completion_checklist"
        / "latest_completion_checklist.json"
    )

    cli = _read_json(cli_path)
    ranking = cli.get("ranking", []) if isinstance(cli.get("ranking"), list) else []
    scbe_cli = next(
        (item for item in ranking if item.get("name") == "scbe-geoseal"), {}
    )

    wedge = _read_json(wedge_path)
    operator = _read_json(operator_path)
    checklist = _read_json(checklist_path)

    artifacts = {
        "cli_competitive": _artifact(
            cli_path,
            {
                "has_ranking": bool(ranking),
                "scbe_ranked": bool(scbe_cli),
                "scbe_full_score": float(scbe_cli.get("score", 0.0) or 0.0) >= 1.0,
            },
            {"scbe_geoseal": scbe_cli},
        ),
        "agentbus_competitive_wedge": _artifact(
            wedge_path,
            {
                "decision_pass": wedge.get("summary", {}).get("decision") == "PASS",
                "bus_wins_all_tasks": wedge.get("summary", {}).get("bus_wins")
                == wedge.get("summary", {}).get("task_count"),
                "local_zero_cost_surface": all(
                    score.get("checks", {}).get("local_private")
                    and score.get("checks", {}).get("zero_cost")
                    for score in wedge.get("scbe_bus_scores", [])
                ),
            },
            wedge.get("summary", {}),
        ),
        "operator_agent_bus_eval": _artifact(
            operator_path,
            {
                "decision_pass": operator.get("decision") == "PASS",
                "endpoint_score_full": float(operator.get("endpoint_score", 0.0) or 0.0)
                >= 1.0,
                "dataset_score_full": float(operator.get("dataset_score", 0.0) or 0.0)
                >= 1.0,
            },
            {
                "score": operator.get("score"),
                "dataset_score": operator.get("dataset_score"),
                "endpoint_score": operator.get("endpoint_score"),
            },
        ),
        "workflow_completion_checklist": _artifact(
            checklist_path,
            {
                "ready_to_claim_done": checklist.get("completion_status")
                == "ready_to_claim_done",
                "no_known_failures": int(checklist.get("known_failure_count", -1)) == 0,
            },
            {
                "completion_status": checklist.get("completion_status"),
                "known_failure_count": checklist.get("known_failure_count"),
            },
        ),
    }

    missing = [name for name, payload in artifacts.items() if not payload["exists"]]
    failed = [
        name
        for name, payload in artifacts.items()
        if payload["exists"] and not payload["ok"]
    ]
    decision = "PASS" if not missing and not failed else "BLOCK"
    payload = {
        "schema_version": "scbe_harness_release_readiness_v1",
        "generated_at_utc": _utc_now(),
        "decision": decision,
        "scope": "local harness release readiness; not model intelligence or public leaderboard parity",
        "artifacts": artifacts,
        "missing_artifacts": missing,
        "failed_artifacts": failed,
        "claim_boundary": [
            "PASS means the local harness surface emitted benchmark receipts and readiness artifacts.",
            "PASS does not mean the agent can solve real repository repair benchmarks yet.",
            "Next external proof should run real patch tasks and score tests passed, edit quality, and time-to-fix.",
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest_readiness.json"
    md_path = out_dir / "LATEST.md"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    payload["json"] = str(json_path.relative_to(REPO_ROOT))
    payload["markdown"] = str(md_path.relative_to(REPO_ROOT))
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    rows = [
        "| Artifact | Status | Path |",
        "|---|---:|---|",
    ]
    for name, item in payload["artifacts"].items():
        rows.append(
            f"| `{name}` | `{'PASS' if item['ok'] else 'FAIL'}` | `{item['path']}` |"
        )
    return "\n".join(
        [
            "# SCBE Harness Release Readiness",
            "",
            f"- Generated: `{payload['generated_at_utc']}`",
            f"- Decision: `{payload['decision']}`",
            f"- Scope: {payload['scope']}",
            "",
            "## Artifacts",
            "",
            *rows,
            "",
            "## Claim Boundary",
            "",
            *[f"- {item}" for item in payload["claim_boundary"]],
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = build_report(Path(args.out_dir))
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"{payload['decision']} {payload['json']}")
    raise SystemExit(0 if payload["decision"] == "PASS" else 1)


if __name__ == "__main__":
    main()
