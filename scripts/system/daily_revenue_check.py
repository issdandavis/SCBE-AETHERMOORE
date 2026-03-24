#!/usr/bin/env python3
"""Daily revenue check — Stripe balance, npm/PyPI downloads, GitHub stars.

Produces a JSON report at artifacts/revenue/daily_check.json and prints
a one-line summary to stdout.

Usage:
    python scripts/system/daily_revenue_check.py
    python scripts/system/daily_revenue_check.py --dry-run
    python scripts/system/daily_revenue_check.py --check stripe
    python scripts/system/daily_revenue_check.py --check downloads
    python scripts/system/daily_revenue_check.py --check github
    python scripts/system/daily_revenue_check.py --check sponsors
    python scripts/system/daily_revenue_check.py --output artifacts/revenue/custom_report.json

Environment:
    STRIPE_SECRET_KEY   — Stripe API key (rk_live_* or sk_live_*)
    GITHUB_TOKEN        — GitHub PAT (optional, raises rate limit)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "revenue" / "daily_check.json"

NPM_PACKAGE = "scbe-aethermoore"
PYPI_PACKAGE = "scbe-aethermoore"
GITHUB_REPO = "issdandavis/SCBE-AETHERMOORE"

VALID_CHECKS = ("stripe", "downloads", "github", "sponsors", "all")


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------


def _load_env_file() -> None:
    """Load credentials from connector oauth file if not already in env."""
    env_files = [
        REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth",
        REPO_ROOT / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value and value != "REPLACE_ME" and key not in os.environ:
                        os.environ[key] = value
            except OSError:
                pass


def _get_env(*names: str) -> str:
    """Return the first non-empty env var from the given names."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> tuple[int, dict[str, Any] | list[Any]]:
    """GET request returning (status_code, parsed_json)."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "scbe-revenue-check/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return int(resp.status), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            return int(exc.code), json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            return int(exc.code), {"error": body_text[:300]}
    except Exception as exc:
        return 0, {"error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------


def check_stripe() -> dict[str, Any]:
    """Check Stripe balance, active subscriptions, and recent charges."""
    secret_key = _get_env("STRIPE_SECRET_KEY", "STRIPE_KEY")
    if not secret_key:
        return {"status": "skipped", "reason": "STRIPE_SECRET_KEY not set"}

    # Basic auth header for Stripe
    auth_value = base64.b64encode(f"{secret_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth_value}"}

    result: dict[str, Any] = {"status": "ok"}

    # Balance
    code, data = _get_json("https://api.stripe.com/v1/balance", headers=headers)
    if code == 200 and isinstance(data, dict):
        result["balance_available"] = data.get("available", [])
        result["balance_pending"] = data.get("pending", [])
    else:
        result["status"] = "error"
        result["balance_error"] = f"HTTP {code}"

    # Active subscriptions count
    code, data = _get_json(
        "https://api.stripe.com/v1/subscriptions?status=active&limit=1",
        headers=headers,
    )
    if code == 200 and isinstance(data, dict):
        # Stripe returns has_more and data; total_count is in the response if expand is used.
        # Without expand, we get the list. Use has_more + len(data) as approximation.
        subs = data.get("data", [])
        result["active_subscriptions"] = len(subs)
        result["subscriptions_has_more"] = data.get("has_more", False)
    else:
        result["active_subscriptions"] = "unknown"

    # Recent charges (last 10)
    code, data = _get_json(
        "https://api.stripe.com/v1/charges?limit=10",
        headers=headers,
    )
    if code == 200 and isinstance(data, dict):
        charges = data.get("data", [])
        result["recent_charges_count"] = len(charges)
        total_cents = sum(int(c.get("amount", 0)) for c in charges if c.get("paid"))
        result["recent_charges_total_cents"] = total_cents
    else:
        result["recent_charges_count"] = 0
        result["recent_charges_total_cents"] = 0

    return result


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------


def check_npm() -> dict[str, Any]:
    """Check npm weekly downloads for the package."""
    url = f"https://api.npmjs.org/downloads/point/last-week/{NPM_PACKAGE}"
    code, data = _get_json(url)

    if code == 200 and isinstance(data, dict):
        return {
            "status": "ok",
            "package": NPM_PACKAGE,
            "downloads_last_week": data.get("downloads", 0),
            "period_start": data.get("start", ""),
            "period_end": data.get("end", ""),
        }

    return {
        "status": "error",
        "package": NPM_PACKAGE,
        "http_code": code,
        "downloads_last_week": 0,
    }


# ---------------------------------------------------------------------------
# PyPI
# ---------------------------------------------------------------------------


def check_pypi() -> dict[str, Any]:
    """Check PyPI recent downloads via pypistats API."""
    url = f"https://pypistats.org/api/packages/{PYPI_PACKAGE}/recent"
    code, data = _get_json(url)

    if code == 200 and isinstance(data, dict):
        recent = data.get("data", {})
        return {
            "status": "ok",
            "package": PYPI_PACKAGE,
            "downloads_last_day": recent.get("last_day", 0),
            "downloads_last_week": recent.get("last_week", 0),
            "downloads_last_month": recent.get("last_month", 0),
        }

    return {
        "status": "error",
        "package": PYPI_PACKAGE,
        "http_code": code,
        "downloads_last_day": 0,
        "downloads_last_week": 0,
        "downloads_last_month": 0,
    }


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


def check_github() -> dict[str, Any]:
    """Check GitHub repo stars, forks, issues, watchers."""
    token = _get_env("GITHUB_TOKEN", "GH_TOKEN")
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{GITHUB_REPO}"
    code, data = _get_json(url, headers=headers)

    if code == 200 and isinstance(data, dict):
        return {
            "status": "ok",
            "repo": GITHUB_REPO,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "watchers": data.get("watchers_count", 0),
            "subscribers": data.get("subscribers_count", 0),
            "default_branch": data.get("default_branch", "main"),
        }

    return {
        "status": "error",
        "repo": GITHUB_REPO,
        "http_code": code,
        "stars": 0,
        "forks": 0,
        "open_issues": 0,
        "watchers": 0,
    }


# ---------------------------------------------------------------------------
# GitHub Sponsors
# ---------------------------------------------------------------------------


def check_sponsors() -> dict[str, Any]:
    """Check GitHub Sponsors count via GraphQL API."""
    token = _get_env("GITHUB_TOKEN", "GH_TOKEN")
    if not token:
        return {"status": "skipped", "reason": "GITHUB_TOKEN not set"}

    query = json.dumps(
        {
            "query": """{
            viewer {
                sponsorsListing { isPublic }
                sponsors(first: 20) {
                    totalCount
                    nodes {
                        sponsorEntity {
                            ... on User { login }
                            ... on Organization { login }
                        }
                    }
                }
            }
        }"""
        }
    )

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=query.encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "scbe-revenue-check/1.0")

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        viewer = body.get("data", {}).get("viewer", {})
        sponsors_data = viewer.get("sponsors", {})
        total = sponsors_data.get("totalCount", 0)
        nodes = sponsors_data.get("nodes", [])
        logins = []
        for node in nodes:
            entity = node.get("sponsorEntity", {})
            login = entity.get("login", "")
            if login:
                logins.append(login)

        listing = viewer.get("sponsorsListing") or {}
        return {
            "status": "ok",
            "sponsors_count": total,
            "sponsor_logins": logins,
            "listing_public": listing.get("isPublic", False),
        }
    except urllib.error.HTTPError as exc:
        return {
            "status": "error",
            "http_code": int(exc.code),
            "sponsors_count": 0,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc)[:200],
            "sponsors_count": 0,
        }


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------


def _format_dollars(cents: int) -> str:
    """Format cents as $X.XX."""
    return f"${cents / 100:.2f}"


def build_summary_line(report: dict[str, Any]) -> str:
    """Build a one-line human-readable summary from the full report."""
    parts: list[str] = []

    # Stripe
    stripe = report.get("stripe", {})
    if stripe.get("status") == "ok":
        available = stripe.get("balance_available", [])
        if available:
            total_cents = sum(b.get("amount", 0) for b in available)
            parts.append(f"Stripe {_format_dollars(total_cents)} avail")
        else:
            parts.append("Stripe $0.00 avail")
    elif stripe.get("status") == "skipped":
        parts.append("Stripe [no key]")
    else:
        parts.append("Stripe [error]")

    # npm
    npm = report.get("npm", {})
    if npm.get("status") == "ok":
        dl = npm.get("downloads_last_week", 0)
        parts.append(f"npm {dl}/wk")
    else:
        parts.append("npm [error]")

    # PyPI
    pypi = report.get("pypi", {})
    if pypi.get("status") == "ok":
        dl = pypi.get("downloads_last_month", 0)
        parts.append(f"PyPI {dl}/mo")
    else:
        parts.append("PyPI [error]")

    # GitHub
    gh = report.get("github", {})
    if gh.get("status") == "ok":
        stars = gh.get("stars", 0)
        parts.append(f"GH {stars} stars")
    else:
        parts.append("GH [error]")

    # Sponsors
    sponsors = report.get("sponsors", {})
    if sponsors.get("status") == "ok":
        count = sponsors.get("sponsors_count", 0)
        if count > 0:
            parts.append(f"{count} sponsors")

    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily revenue check — Stripe, npm, PyPI, GitHub",
    )
    parser.add_argument(
        "--check",
        choices=VALID_CHECKS,
        default="all",
        help="Run only a specific check (default: all)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path (default: artifacts/revenue/daily_check.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be checked without making API calls",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the summary line (suppress progress messages)",
    )
    args = parser.parse_args()

    _load_env_file()

    run_all = args.check == "all"

    if args.dry_run:
        checks_to_run = []
        if run_all or args.check == "stripe":
            key = _get_env("STRIPE_SECRET_KEY", "STRIPE_KEY")
            checks_to_run.append(f"stripe: {'configured' if key else 'MISSING STRIPE_SECRET_KEY'}")
        if run_all or args.check == "downloads":
            checks_to_run.append(f"npm: {NPM_PACKAGE} (public API)")
            checks_to_run.append(f"pypi: {PYPI_PACKAGE} (public API)")
        if run_all or args.check == "github":
            token = _get_env("GITHUB_TOKEN", "GH_TOKEN")
            checks_to_run.append(f"github: {GITHUB_REPO} ({'authenticated' if token else 'unauthenticated'})")
        if run_all or args.check == "sponsors":
            token = _get_env("GITHUB_TOKEN", "GH_TOKEN")
            checks_to_run.append(f"sponsors: {'configured' if token else 'MISSING GITHUB_TOKEN'}")

        print("[DRY RUN] Would check:")
        for item in checks_to_run:
            print(f"  - {item}")
        print(f"Output: {args.output}")
        return 0

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    def _log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    # Stripe
    if run_all or args.check == "stripe":
        _log("Checking Stripe...")
        report["stripe"] = check_stripe()
        status = report["stripe"]["status"]
        _log(f"  Stripe: {status}")

    # npm + PyPI
    if run_all or args.check == "downloads":
        _log("Checking npm downloads...")
        report["npm"] = check_npm()
        npm_dl = report["npm"].get("downloads_last_week", "?")
        _log(f"  npm: {npm_dl} downloads last week")

        _log("Checking PyPI downloads...")
        report["pypi"] = check_pypi()
        pypi_dl = report["pypi"].get("downloads_last_month", "?")
        _log(f"  PyPI: {pypi_dl} downloads last month")

    # GitHub
    if run_all or args.check == "github":
        _log("Checking GitHub repo...")
        report["github"] = check_github()
        stars = report["github"].get("stars", "?")
        _log(f"  GitHub: {stars} stars")

    # Sponsors
    if run_all or args.check == "sponsors":
        _log("Checking GitHub Sponsors...")
        report["sponsors"] = check_sponsors()
        sc = report["sponsors"].get("sponsors_count", "?")
        _log(f"  Sponsors: {sc}")

    # Summary line
    summary = build_summary_line(report)
    report["summary_line"] = summary

    # Write report
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path = out_path.resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    _log(f"\nReport: {out_path}")
    print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
