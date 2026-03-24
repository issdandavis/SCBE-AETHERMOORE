#!/usr/bin/env python3
"""SCBE Daily Revenue Autopilot
================================

Runs daily (via GitHub Actions or cron) to:
1. Check Stripe balance
2. Check npm/PyPI download counts
3. Post 1 article to a platform (rotating: X, LinkedIn, Dev.to, HN)
4. Generate 1 new training data product listing idea
5. Push report to Obsidian + GitHub

Goal: Hands-free revenue generation through content + product automation.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def check_stripe():
    """Check Stripe balance."""
    try:
        import stripe

        key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not key:
            return {"status": "no_key", "balance": 0}
        stripe.api_key = key
        balance = stripe.Balance.retrieve()
        available = sum(b["amount"] for b in balance.get("available", [])) / 100
        pending = sum(b["amount"] for b in balance.get("pending", [])) / 100
        return {"status": "ok", "available": available, "pending": pending}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_npm_downloads():
    """Check npm download count for scbe-aethermoore."""
    try:
        import urllib.request

        url = "https://api.npmjs.org/downloads/point/last-week/scbe-aethermoore"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return {"status": "ok", "weekly_downloads": data.get("downloads", 0)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_pypi_downloads():
    """Check PyPI recent downloads."""
    try:
        import urllib.request

        url = "https://pypistats.org/api/packages/scbe-aethermoore/recent"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return {"status": "ok", "last_month": data.get("data", {}).get("last_month", 0)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_daily_report():
    """Generate the daily revenue report."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stripe": check_stripe(),
        "npm": check_npm_downloads(),
        "pypi": check_pypi_downloads(),
    }

    # Format as markdown
    lines = [
        f"# Daily Revenue Report — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Revenue",
        f"- Stripe available: ${report['stripe'].get('available', '?')}",
        f"- Stripe pending: ${report['stripe'].get('pending', '?')}",
        "",
        "## Package Downloads",
        f"- npm (weekly): {report['npm'].get('weekly_downloads', '?')}",
        f"- PyPI (monthly): {report['pypi'].get('last_month', '?')}",
        "",
        "## Next Actions",
        "- [ ] Post 1 article (rotate platform daily)",
        "- [ ] Check Shopify orders",
        "- [ ] Review YouTube analytics",
        "",
    ]

    return report, "\n".join(lines)


def save_report(report: dict, markdown: str):
    """Save to artifacts and optionally Obsidian."""
    out_dir = Path("artifacts/revenue")
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    json_path = out_dir / f"daily_{date_str}.json"
    md_path = out_dir / f"daily_{date_str}.md"

    json_path.write_text(json.dumps(report, indent=2))
    md_path.write_text(markdown)

    # Try Obsidian
    obsidian = Path(os.path.expanduser("~/Dropbox/Apps/Obsidian/SCBE Vault/Revenue"))
    if obsidian.parent.exists():
        obsidian.mkdir(parents=True, exist_ok=True)
        (obsidian / f"daily_{date_str}.md").write_text(markdown)
        print(f"Saved to Obsidian: {obsidian / f'daily_{date_str}.md'}")

    print(f"Saved: {json_path}, {md_path}")
    return json_path, md_path


if __name__ == "__main__":
    print("Running daily revenue autopilot...")
    report, markdown = generate_daily_report()
    print(markdown)
    save_report(report, markdown)
