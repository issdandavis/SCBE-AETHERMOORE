#!/usr/bin/env python3
"""Audit every active npm lockfile in the repository.

The npm CLI audits one dependency tree at a time. SCBE contains several independent
trees, so auditing only the repository root leaves nested applications invisible.
This command discovers active package-lock.json files, runs npm audit without
installing packages or lifecycle scripts, and emits one aggregate report.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable

SEVERITIES = ("info", "low", "moderate", "high", "critical")
DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".npm-cache",
        ".vercel",
        "archive",
        "artifacts",
        "cloud-archive",
        "dist",
        "external",
        "external_repos",
        "hioujhn",
        "node_modules",
        "scbe-aethermoore",
        "spiralverse-protocol",
        "training-data",
        "_quarantine",
    }
)


@dataclass(frozen=True)
class Project:
    directory: Path
    relative_directory: str
    lockfile: str
    manifest_exists: bool


def discover_projects(root: Path, excluded_directories: Iterable[str] = DEFAULT_EXCLUDED_DIRECTORIES) -> list[Project]:
    """Return every non-vendored npm dependency tree beneath *root*."""

    root = root.resolve()
    excluded = set(excluded_directories)
    projects: list[Project] = []

    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in excluded)
        if "package-lock.json" not in files:
            continue

        directory = Path(current)
        relative = directory.relative_to(root).as_posix() or "."
        projects.append(
            Project(
                directory=directory,
                relative_directory=relative,
                lockfile=(Path(relative) / "package-lock.json").as_posix() if relative != "." else "package-lock.json",
                manifest_exists=(directory / "package.json").is_file(),
            )
        )

    return sorted(projects, key=lambda project: project.relative_directory)


def parse_json_document(text: str) -> dict[str, Any]:
    """Parse npm JSON even when the CLI writes a warning before the document."""

    stripped = text.strip()
    if not stripped:
        raise ValueError("npm audit returned no JSON")

    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise ValueError("npm audit output did not contain a JSON object")


def vulnerability_counts(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("metadata", {}).get("vulnerabilities", {})
    counts = {severity: int(raw.get(severity, 0) or 0) for severity in SEVERITIES}
    counts["total"] = int(raw.get("total", sum(counts.values())) or 0)
    return counts


def finding_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for name, value in sorted(payload.get("vulnerabilities", {}).items()):
        if not isinstance(value, dict):
            continue
        findings.append(
            {
                "name": name,
                "severity": value.get("severity", "unknown"),
                "direct": bool(value.get("isDirect", False)),
                "range": value.get("range", ""),
                "fix_available": value.get("fixAvailable", False),
            }
        )
    return findings


def resolve_npm_command(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    candidates = ("npm.cmd", "npm") if os.name == "nt" else ("npm",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("npm was not found on PATH")


def audit_project(project: Project, npm_command: str, timeout_seconds: int) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": project.relative_directory,
        "lockfile": project.lockfile,
        "vulnerabilities": {**{severity: 0 for severity in SEVERITIES}, "total": 0},
        "findings": [],
        "error": None,
    }
    if not project.manifest_exists:
        base["error"] = "package-lock.json has no sibling package.json"
        return base

    environment = os.environ.copy()
    environment.update(
        {
            "npm_config_audit": "true",
            "npm_config_fund": "false",
            "npm_config_ignore_scripts": "true",
            "npm_config_update_notifier": "false",
        }
    )
    try:
        completed = subprocess.run(
            [npm_command, "audit", "--package-lock-only", "--json", "--audit-level=none"],
            cwd=project.directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        base["error"] = f"npm audit timed out after {timeout_seconds}s"
        return base
    except OSError as exc:
        base["error"] = f"npm audit could not start: {exc}"
        return base

    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    try:
        payload = parse_json_document(combined)
    except ValueError as exc:
        base["error"] = f"{exc} (exit {completed.returncode})"
        return base

    if payload.get("error"):
        error = payload["error"]
        base["error"] = error.get("summary", str(error)) if isinstance(error, dict) else str(error)
        return base

    base["vulnerabilities"] = vulnerability_counts(payload)
    base["findings"] = finding_rows(payload)
    return base


def aggregate_counts(results: Iterable[dict[str, Any]]) -> dict[str, int]:
    totals = {severity: 0 for severity in SEVERITIES}
    totals["total"] = 0
    for result in results:
        counts = result["vulnerabilities"]
        for key in totals:
            totals[key] += int(counts.get(key, 0) or 0)
    return totals


def exceeds_threshold(totals: dict[str, int], audit_level: str) -> bool:
    if audit_level == "none":
        return False
    minimum = SEVERITIES.index(audit_level)
    return any(totals[severity] > 0 for severity in SEVERITIES[minimum:])


def markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "## npm dependency audit",
        "",
        "| Project | Critical | High | Moderate | Low | Total | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in report["projects"]:
        counts = result["vulnerabilities"]
        status = f"ERROR: {result['error']}" if result["error"] else ("clean" if counts["total"] == 0 else "review")
        lines.append(
            f"| `{result['path']}` | {counts['critical']} | {counts['high']} | "
            f"{counts['moderate']} | {counts['low']} | {counts['total']} | {status} |"
        )
    totals = report["totals"]
    lines.append(
        f"| **Total** | **{totals['critical']}** | **{totals['high']}** | "
        f"**{totals['moderate']}** | **{totals['low']}** | **{totals['total']}** | "
        f"**{report['status']}** |"
    )
    return "\n".join(lines) + "\n"


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--audit-level", choices=("none", *SEVERITIES), default="high")
    parser.add_argument("--report", type=Path, help="Write the aggregate JSON report here")
    parser.add_argument("--npm", help="Explicit npm executable")
    parser.add_argument("--timeout", type=int, default=120, help="Per-project timeout in seconds")
    parser.add_argument("--list", action="store_true", help="List discovered projects without auditing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    projects = discover_projects(root)

    if args.list:
        for project in projects:
            print(project.relative_directory)
        return 0

    try:
        npm_command = resolve_npm_command(args.npm)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results = [audit_project(project, npm_command, args.timeout) for project in projects]
    totals = aggregate_counts(results)
    errors = [result["path"] for result in results if result["error"]]
    threshold_failed = exceeds_threshold(totals, args.audit_level)
    status = "error" if errors else ("vulnerable" if totals["total"] else "clean")
    report = {
        "schema": "scbe.npm-audit-all.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_level": args.audit_level,
        "status": status,
        "project_count": len(projects),
        "totals": totals,
        "projects": results,
        "errors": errors,
        "threshold_failed": threshold_failed,
    }

    summary = markdown_summary(report)
    print(summary, end="")
    if args.report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        write_json_atomic(report_path, report)
        print(f"report: {report_path}")

    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with Path(github_summary).open("a", encoding="utf-8") as stream:
            stream.write(summary)

    if errors:
        return 2
    return 1 if threshold_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
