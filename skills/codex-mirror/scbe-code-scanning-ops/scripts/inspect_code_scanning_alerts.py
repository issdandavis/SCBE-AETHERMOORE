#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect GitHub code-scanning alerts or summarize an offline snapshot.")
    parser.add_argument("--repo", default="issdandavis/SCBE-AETHERMOORE", help="GitHub owner/repo slug")
    parser.add_argument("--state", default="open", choices=("open", "dismissed", "fixed"))
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--alerts-file", default="", help="Offline JSON file containing alert payloads")
    parser.add_argument("--output", default="", help="Optional output JSON path")
    parser.add_argument("--top", type=int, default=10, help="How many alert rows to include in text output")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def _friendly_api_error(result: subprocess.CompletedProcess[str]) -> str:
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or "unknown error"
    if "404" in detail or '"status": "404"' in detail:
        return (
            "GitHub returned 404 for the code-scanning API. "
            "That usually means code scanning is not enabled yet, or the current gh token cannot read security alerts."
        )
    return f"Unable to read code-scanning alerts: {detail}"


def fetch_alerts(repo: str, state: str, per_page: int) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/code-scanning/alerts", "-f", f"state={state}", "-F", f"per_page={per_page}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(_friendly_api_error(result))
    payload = json.loads(result.stdout or "[]")
    if not isinstance(payload, list):
        raise RuntimeError("GitHub code-scanning API returned a non-list payload.")
    return payload


def load_alerts_from_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("Alert snapshot must be a JSON list.")
    return payload


def normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    rule = dict(alert.get("rule") or {})
    location = dict((alert.get("most_recent_instance") or {}).get("location") or {})
    return {
        "number": int(alert.get("number") or 0),
        "rule_id": str(rule.get("id") or rule.get("name") or "unknown"),
        "rule_name": str(rule.get("name") or rule.get("id") or "unknown"),
        "severity": str(rule.get("security_severity_level") or alert.get("security_severity_level") or "unknown"),
        "state": str(alert.get("state") or "unknown"),
        "tool": str((alert.get("tool") or {}).get("name") or "unknown"),
        "path": str(location.get("path") or ""),
        "start_line": int(location.get("start_line") or 0),
        "html_url": str(alert.get("html_url") or ""),
    }


def summarize_alerts(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_alert(alert) for alert in alerts]
    rule_counts = Counter(alert["rule_id"] for alert in normalized)
    severity_counts = Counter(alert["severity"] for alert in normalized)
    path_counts = Counter(alert["path"] for alert in normalized if alert["path"])
    return {
        "schema_version": "scbe_code_scanning_alert_summary_v1",
        "alert_count": len(normalized),
        "rule_counts": dict(rule_counts),
        "severity_counts": dict(severity_counts),
        "top_paths": [{"path": path, "count": count} for path, count in path_counts.most_common(20)],
        "alerts": normalized,
    }


def render_text(summary: dict[str, Any], top: int) -> str:
    lines = [
        "SCBE code-scanning alerts",
        f"count: {summary['alert_count']}",
        "rules:",
    ]
    for rule_id, count in sorted(summary["rule_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {rule_id}: {count}")
    lines.append("top paths:")
    for row in summary["top_paths"][:top]:
        lines.append(f"- {row['count']:>2} {row['path']}")
    lines.append("alerts:")
    for alert in summary["alerts"][:top]:
        location = alert["path"]
        if alert["start_line"]:
            location = f"{location}:{alert['start_line']}"
        lines.append(f"- #{alert['number']} [{alert['severity']}] {alert['rule_id']} -> {location}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        if args.alerts_file:
            alerts = load_alerts_from_file(Path(args.alerts_file))
            source = {"mode": "offline", "alerts_file": args.alerts_file}
        else:
            alerts = fetch_alerts(args.repo, args.state, args.per_page)
            source = {"mode": "live", "repo": args.repo, "state": args.state}
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = summarize_alerts(alerts)
    summary["source"] = source

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.json_output:
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        print(render_text(summary, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
