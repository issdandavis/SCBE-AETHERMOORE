#!/usr/bin/env python3
"""Build a scheduled website-betterment report for SCBE public surfaces.

The automation is intentionally read-only: it audits the current static site,
checks local app/offer config, emits model-agent packets, and creates a
bounded issue body when a human should improve the site.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system import remote_app_config_smoke  # noqa: E402
from scripts.system import website_sales_train  # noqa: E402

DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "marketing" / "website_betterment_automation"
DEFAULT_PAGE = REPO_ROOT / "docs" / "index.html"
DEFAULT_MIN_SCORE = 7.0


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def discover_public_surfaces() -> list[dict[str, Any]]:
    candidates = [
        ("home", REPO_ROOT / "docs" / "index.html"),
        ("offers_json", REPO_ROOT / "docs" / "offers.json"),
        ("app_config", REPO_ROOT / "docs" / "app-config.json"),
        ("sitemap", REPO_ROOT / "docs" / "sitemap.xml"),
        ("robots", REPO_ROOT / "docs" / "robots.txt"),
        ("llms_root", REPO_ROOT / "llms.txt"),
        ("llms_docs", REPO_ROOT / "docs" / "llms.txt"),
        ("robot_map", REPO_ROOT / "docs" / "robot.md"),
    ]
    rows: list[dict[str, Any]] = []
    for label, path in candidates:
        rows.append(
            {
                "label": label,
                "path": rel(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return rows


def build_smoke_summary(live: bool) -> dict[str, Any]:
    checks = remote_app_config_smoke.run_checks(live=live)
    failures = [asdict(check) for check in checks if not check.ok]
    return {
        "live": live,
        "ok": not failures,
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "checks": [asdict(check) for check in checks],
    }


def build_sales_summary(page: Path, output_dir: Path) -> dict[str, Any]:
    html = page.read_text(encoding="utf-8")
    audit = website_sales_train.audit_html(page, html)
    backlog = website_sales_train.build_backlog(audit)
    packets = website_sales_train.build_model_packets(audit, backlog)
    sales_dir = output_dir / "sales_audit"
    sales_dir.mkdir(parents=True, exist_ok=True)
    write_json(sales_dir / "audit.json", asdict(audit))
    write_json(sales_dir / "backlog.json", {"items": backlog})
    write_json(sales_dir / "model_packets.json", packets)
    return {
        "page": audit.path,
        "title": audit.title,
        "metrics": audit.metrics,
        "risks": audit.risks,
        "strengths": audit.strengths,
        "backlog": backlog,
        "artifact_dir": rel(sales_dir),
    }


def issue_needed(summary: dict[str, Any], min_score: float) -> bool:
    sales = summary["sales_audit"]
    smoke = summary["remote_app_config_smoke"]
    overall = float(sales["metrics"].get("overall", 0.0))
    return overall < min_score or not smoke["ok"] or bool(sales.get("risks"))


def build_issue_body(summary: dict[str, Any], min_score: float) -> str:
    sales = summary["sales_audit"]
    smoke = summary["remote_app_config_smoke"]
    risks = sales.get("risks") or ["No sales-page risks reported."]
    backlog = sales.get("backlog") or []
    failures = smoke.get("failures") or []

    lines = [
        "## Website Betterment Automation",
        "",
        f"Generated: `{summary['created_at_utc']}`",
        f"Target page: `{sales['page']}`",
        f"Overall sales score: `{sales['metrics'].get('overall')}` (threshold `{min_score}`)",
        f"Remote/config smoke: `{'pass' if smoke['ok'] else 'fail'}` ({smoke['failure_count']} failures)",
        "",
        "### Top Risks",
        "",
    ]
    lines.extend(f"- {risk}" for risk in risks[:8])
    lines.extend(["", "### Next Bounded Pages", ""])
    if backlog:
        lines.extend(f"- `{item['page_slug']}`: {item['reason']}" for item in backlog[:5])
    else:
        lines.append("- No missing support pages detected by the current audit.")
    lines.extend(["", "### Smoke Failures", ""])
    if failures:
        lines.extend(f"- `{item['name']}`: {item['detail']}" for item in failures[:10])
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "### Automation Artifacts",
            "",
            f"- Summary JSON: `{summary['summary_path']}`",
            f"- Sales audit packet dir: `{sales['artifact_dir']}`",
            "",
            "This issue is generated by the scheduled website-betterment automation. "
            "Keep fixes scoped to public website surfaces and rerun the workflow.",
        ]
    )
    return "\n".join(lines) + "\n"


def emit_github_output(values: dict[str, str]) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as fh:
        for key, value in values.items():
            fh.write(f"{key}={value}\n")


def build_report(page: Path, output_dir: Path, live: bool, min_score: float) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    issue_path = output_dir / "issue.md"
    summary: dict[str, Any] = {
        "schema": "scbe-website-betterment-automation-v1",
        "created_at_utc": now_utc(),
        "page": rel(page),
        "live": live,
        "min_score": min_score,
        "public_surfaces": discover_public_surfaces(),
        "remote_app_config_smoke": build_smoke_summary(live=live),
        "sales_audit": build_sales_summary(page, output_dir),
        "summary_path": rel(summary_path),
        "issue_path": rel(issue_path),
    }
    summary["issue_needed"] = issue_needed(summary, min_score=min_score)
    write_json(summary_path, summary)
    issue_path.write_text(build_issue_body(summary, min_score=min_score), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--live", action="store_true", help="Include live Pages/Vercel checks.")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--fail-on-issue", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    page = args.page if args.page.is_absolute() else REPO_ROOT / args.page
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    summary = build_report(page=page, output_dir=output_dir, live=args.live, min_score=args.min_score)
    emit_github_output(
        {
            "issue_needed": "true" if summary["issue_needed"] else "false",
            "summary_path": summary["summary_path"],
            "issue_path": summary["issue_path"],
            "overall": str(summary["sales_audit"]["metrics"].get("overall")),
        }
    )
    print(json.dumps({k: summary[k] for k in ("schema", "issue_needed", "summary_path", "issue_path")}, indent=2))
    return 1 if args.fail_on_issue and summary["issue_needed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
