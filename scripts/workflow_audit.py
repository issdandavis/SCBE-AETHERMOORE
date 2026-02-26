#!/usr/bin/env python3
"""Workflow policy audit helper for SCBE repositories.

This script scans workflow YAML files for recurring reliability issues that
commonly hide failures in CI (masked errors, deprecated action pins, etc.).
It generates a JSON report and a short markdown summary.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Issue:
    workflow: str
    rule: str
    severity: str
    line: int
    text: str


@dataclass
class WorkflowResult:
    workflow: str
    issues: List[Issue]


RULES = [
    {
        "id": "MASKED_ERROR_OR_TRUE",
        "pattern": "|| true",
        "severity": "high",
        "description": "Error masking can hide failing CI checks.",
    },
    {
        "id": "MASKED_ERROR_OR_ECHO",
        "pattern": "|| echo",
        "severity": "high",
        "description": "Error masking can hide failures and create false-positive success.",
    },
    {
        "id": "CONTINUE_ON_ERROR",
        "pattern": "continue-on-error: true",
        "severity": "medium",
        "description": "Non-failing CI jobs can conceal regressions.",
    },
    {
        "id": "DEPRECATED_GH_RELEASE_V1",
        "pattern": "softprops/action-gh-release@v1",
        "severity": "low",
        "description": "Legacy release action version; v2 is preferred.",
    },
    {
        "id": "OLD_CHECKOUT_ACTION",
        "pattern": "actions/checkout@v3",
        "severity": "low",
        "description": "v4 checkout is the current recommended baseline.",
    },
    {
        "id": "SET_PLUS_E_WITHOUT_EXIT_HANDLING",
        "pattern": "set +e",
        "severity": "low",
        "description": "set +e requires explicit status handling to avoid silent failures.",
    },
]


def resolve_workspace(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"workspace path does not exist: {root}")
    return root


def scan_workflows(workspace: Path) -> List[WorkflowResult]:
    workflow_dir = workspace / ".github" / "workflows"
    results: List[WorkflowResult] = []

    if not workflow_dir.exists():
        return results

    workflow_files = sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    )
    for workflow in workflow_files:
        issues: List[Issue] = []
        text = workflow.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for rule in RULES:
            needle = rule["pattern"]
            for idx, line in enumerate(lines, start=1):
                if needle in line:
                    issues.append(
                        Issue(
                            workflow=workflow.name,
                            rule=f"{rule['id']} ({rule['description']})",
                            severity=rule["severity"],
                            line=idx,
                            text=line.strip(),
                        )
                    )
        results.append(WorkflowResult(workflow=workflow.name, issues=issues))

    return results


def aggregate_results(results: List[WorkflowResult]) -> Dict[str, int]:
    totals = {"high": 0, "medium": 0, "low": 0}
    for result in results:
        for issue in result.issues:
            sev = issue.severity.lower()
            totals[sev] = totals.get(sev, 0) + 1
    totals["total"] = sum(totals.values())
    return totals


def write_markdown_summary(results: List[WorkflowResult], output_path: Path, totals: Dict[str, int]) -> None:
    high = totals.get("high", 0)
    medium = totals.get("medium", 0)
    low = totals.get("low", 0)
    total = totals.get("total", 0)

    lines = [
        "# Workflow Governance Audit",
        "",
        f"- Total workflows: {len(results)}",
        f"- Total findings: {total}",
        f"- High: {high}",
        f"- Medium: {medium}",
        f"- Low: {low}",
        "",
    ]

    for result in results:
        if not result.issues:
            continue
        lines.append(f"## {result.workflow}")
        lines.append("")
        for issue in result.issues:
            lines.append(f"- [{issue.severity.upper()}] line {issue.line}: {issue.rule}")
            lines.append(f"  - `{issue.text}`")
        lines.append("")

    if total == 0:
        lines.append("No issues detected.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_github_outputs(totals: Dict[str, int]) -> None:
    github_output = Path(__import__("os").environ.get("GITHUB_OUTPUT", ""))
    if not github_output.name:
        return
    payload = [
        f"workflow_count={totals.get('workflow_count', 0)}",
        f"issue_count={totals.get('total', 0)}",
        f"high_count={totals.get('high', 0)}",
        f"medium_count={totals.get('medium', 0)}",
        f"low_count={totals.get('low', 0)}",
        f"status={ 'fail' if totals.get('high', 0) > 0 else 'pass' }",
    ]
    github_output.write_text("\n".join(payload) + "\n", encoding="utf-8")


def flatten_results(results: List[WorkflowResult]) -> List[dict]:
    output: List[dict] = []
    for item in results:
        output.append(
            {
                "workflow": item.workflow,
                "issue_count": len(item.issues),
                "issues": [asdict(i) for i in item.issues],
            }
        )
    return output


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--report", default=".github/workflows/workflow-audit-report.json")
    parser.add_argument("--summary", default=".github/workflows/workflow-audit-summary.md")
    args = parser.parse_args(argv)

    workspace = resolve_workspace(args.workspace)
    results = scan_workflows(workspace)
    totals = aggregate_results(results)

    totals["workflow_count"] = len(results)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "totals": totals,
        "workflows": flatten_results(results),
    }

    report_path = resolve_workspace(args.workspace) / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary_path = workspace / args.summary
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_summary(results, summary_path, totals)

    emit_github_outputs(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
