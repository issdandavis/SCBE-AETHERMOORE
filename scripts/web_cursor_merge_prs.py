#!/usr/bin/env python3
"""
Interface-side PR merge helper using Playwright.

Defaults to dry-run. Designed for "web cursor" merge control from GitHub UI.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge PRs from GitHub UI via Playwright web cursor.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--prs", nargs="*", type=int, default=[], help="PR numbers (space-separated)")
    parser.add_argument("--queue", default="", help="Optional queue JSON with `prs` list")
    parser.add_argument("--approval-file", default="", help="Optional approval JSON")
    parser.add_argument("--user-data-dir", default="", help="Playwright persistent profile directory")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--out", default="artifacts/pr_merge_report.json", help="Output report JSON")
    parser.add_argument("--execute", action="store_true", help="Actually click merge buttons")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_prs(args: argparse.Namespace) -> List[int]:
    prs = [int(x) for x in args.prs if int(x) > 0]
    if args.queue:
        queue = read_json(Path(args.queue), default={})
        if isinstance(queue, dict):
            raw = queue.get("prs", [])
            if isinstance(raw, list):
                for x in raw:
                    try:
                        n = int(x)
                    except (TypeError, ValueError):
                        continue
                    if n > 0 and n not in prs:
                        prs.append(n)
    return sorted(prs)


def normalize_approvals(payload: Any) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    if isinstance(payload, dict):
        rows = payload.get("approvals")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    prn = int(row.get("pr", 0))
                except (TypeError, ValueError):
                    continue
                out[prn] = row
        return out
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            try:
                prn = int(row.get("pr", 0))
            except (TypeError, ValueError):
                continue
            out[prn] = row
    return out


def is_approved(row: Dict[str, Any]) -> Tuple[bool, str]:
    if not row:
        return False, ""
    if not bool(row.get("approved", False)):
        return False, ""
    expires_at = str(row.get("expires_at", "")).strip()
    if expires_at:
        try:
            check = expires_at
            if check.endswith("Z"):
                check = check[:-1] + "+00:00"
            if datetime.now(timezone.utc) > datetime.fromisoformat(check).astimezone(timezone.utc):
                return False, ""
        except ValueError:
            return False, ""
    approver = str(row.get("approved_by", "")).strip() or "unknown"
    return True, approver


def has_login_page(page: Any) -> bool:
    try:
        return "login" in page.url.lower() or bool(page.locator('input[name="login"]').count())
    except Exception:
        return False


def first_merge_button(page: Any) -> Any:
    selectors = [
        'button:has-text("Merge pull request")',
        'button:has-text("Squash and merge")',
        'button:has-text("Rebase and merge")',
        'summary:has-text("Merge pull request")',
    ]
    for sel in selectors:
        btn = page.locator(sel).first
        try:
            if btn.count() > 0:
                return btn
        except Exception:
            continue
    return None


def first_confirm_button(page: Any) -> Any:
    selectors = [
        'button:has-text("Confirm merge")',
        'button:has-text("Confirm squash and merge")',
        'button:has-text("Confirm rebase and merge")',
    ]
    for sel in selectors:
        btn = page.locator(sel).first
        try:
            if btn.count() > 0:
                return btn
        except Exception:
            continue
    return None


def run(args: argparse.Namespace, prs: List[int], approvals: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    if not prs:
        return {"generated_at": now_iso(), "rows": [], "summary": {"prs": 0}}

    # Local import to keep --help lightweight.
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    profile_dir = args.user_data_dir or str(Path.home() / ".scbe-playwright-github")
    rows: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=profile_dir, headless=args.headless)
        page = context.new_page()

        for pr in prs:
            row: Dict[str, Any] = {"pr": pr, "ts": now_iso(), "status": "unknown"}
            url = f"https://github.com/{args.repo}/pull/{pr}"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            if has_login_page(page):
                row["status"] = "blocked_login_required"
                rows.append(row)
                continue

            merge_btn = first_merge_button(page)
            if merge_btn is None:
                row["status"] = "blocked_no_merge_button"
                rows.append(row)
                continue

            if not args.execute:
                row["status"] = "dry_run_mergeable"
                rows.append(row)
                continue

            approval_row = approvals.get(pr, {})
            approved, approver = is_approved(approval_row)
            if not approved:
                row["status"] = "blocked_unapproved"
                rows.append(row)
                continue

            try:
                merge_btn.click(timeout=15000)
                confirm_btn = first_confirm_button(page)
                if confirm_btn is None:
                    row["status"] = "failed_confirm_button_missing"
                else:
                    confirm_btn.click(timeout=15000)
                    row["status"] = "merged"
                    row["approved_by"] = approver
            except Exception as exc:
                row["status"] = "failed_click"
                row["reason"] = type(exc).__name__
            rows.append(row)

        context.close()

    merged = len([r for r in rows if r.get("status") == "merged"])
    dry = len([r for r in rows if r.get("status") == "dry_run_mergeable"])
    blocked = len([r for r in rows if str(r.get("status", "")).startswith("blocked_")])
    failed = len([r for r in rows if str(r.get("status", "")).startswith("failed_")])
    return {
        "generated_at": now_iso(),
        "repo": args.repo,
        "execute": args.execute,
        "rows": rows,
        "summary": {
            "prs": len(prs),
            "merged": merged,
            "dry_run_mergeable": dry,
            "blocked": blocked,
            "failed": failed,
        },
    }


def main() -> int:
    args = parse_args()
    prs = load_prs(args)
    approvals = normalize_approvals(read_json(Path(args.approval_file), default={})) if args.approval_file else {}

    report = run(args, prs=prs, approvals=approvals)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(
        f"PR merge report: {out_path} | prs={report['summary']['prs']} merged={report['summary']['merged']} blocked={report['summary']['blocked']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
