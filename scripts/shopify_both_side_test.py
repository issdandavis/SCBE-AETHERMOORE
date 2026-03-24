#!/usr/bin/env python3
"""Headless Shopify both-side smoke test (admin + storefront).

This script uses one persistent Playwright profile so admin auth can be reused
across runs. It captures screenshots and writes a JSON report.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADMIN_AUTH_HINTS = (
    "accounts.shopify.com",
    "/challenge",
    "/login",
    "/auth",
)

STOREFRONT_PASSWORD_HINTS = (
    "/password",
    "password protected",
)

APP_AUTH_HINTS = (
    "accounts.shopify.com",
    "/oauth",
    "/auth",
    "/login",
)


@dataclass
class SideReport:
    side: str
    requested_url: str
    final_url: str = ""
    title: str = ""
    status: str = "unknown"
    issue: str = ""
    screenshot: str = ""
    marker_count: int = 0
    sample_links: list[str] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_store_domain(value: str) -> str:
    domain = value.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/", 1)[0]
    if not domain:
        raise ValueError("Store domain cannot be empty.")
    if "." not in domain:
        domain = f"{domain}.myshopify.com"
    return domain


def ensure_path_fragment(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return "/"
    if not trimmed.startswith("/"):
        return f"/{trimmed}"
    return trimmed


def sample_links(page: Any, limit: int = 8) -> list[str]:
    script = "els => els.map(e => e.href || '').filter(Boolean).slice(0, " f"{max(limit, 1)})"
    try:
        values = page.eval_on_selector_all("a[href]", script)
        return [str(v) for v in values]
    except Exception:
        return []


def has_any_locator(page: Any, selector: str) -> bool:
    try:
        return page.locator(selector).count() > 0
    except Exception:
        return False


def evaluate_admin_page(page: Any, report: SideReport, expected_text: str) -> SideReport:
    try:
        report.final_url = page.url
        report.title = page.title()
    except Exception as exc:
        report.status = "error"
        report.issue = f"Unable to inspect admin page: {exc}"
        return report

    report.sample_links = sample_links(page)
    report.marker_count = page.locator("a[href*='/products/']").count()
    url_lower = report.final_url.lower()
    title_lower = report.title.lower()

    needs_auth = any(token in url_lower for token in ADMIN_AUTH_HINTS)
    needs_auth = needs_auth or has_any_locator(page, "input[type='email'], input[name='account[email]']")
    if needs_auth:
        report.status = "auth_required"
        report.issue = "Admin session is not authenticated for this Playwright profile."
    else:
        report.status = "ok"
        report.issue = ""

    if expected_text:
        page_text = ""
        try:
            page_text = page.inner_text("body").lower()
        except Exception:
            pass
        if expected_text.lower() not in title_lower and expected_text.lower() not in page_text:
            report.status = "assertion_failed"
            report.issue = f"Expected text not found on admin side: {expected_text!r}"

    return report


def evaluate_storefront_page(page: Any, report: SideReport, expected_text: str) -> SideReport:
    try:
        report.final_url = page.url
        report.title = page.title()
    except Exception as exc:
        report.status = "error"
        report.issue = f"Unable to inspect storefront page: {exc}"
        return report

    report.sample_links = sample_links(page)
    report.marker_count = page.locator("a[href*='/products/']").count()

    url_lower = report.final_url.lower()
    title_lower = report.title.lower()
    has_password_gate = any(token in url_lower for token in STOREFRONT_PASSWORD_HINTS)
    has_password_gate = has_password_gate or has_any_locator(page, "form[action*='password'], input[type='password']")
    has_password_gate = has_password_gate or "password" in title_lower

    if has_password_gate:
        report.status = "password_gate"
        report.issue = "Storefront appears password protected."
    else:
        report.status = "ok"
        report.issue = ""

    if expected_text:
        page_text = ""
        try:
            page_text = page.inner_text("body").lower()
        except Exception:
            pass
        if expected_text.lower() not in title_lower and expected_text.lower() not in page_text:
            report.status = "assertion_failed"
            report.issue = f"Expected text not found on storefront side: {expected_text!r}"

    return report


def evaluate_app_page(page: Any, report: SideReport, expected_text: str) -> SideReport:
    try:
        report.final_url = page.url
        report.title = page.title()
    except Exception as exc:
        report.status = "error"
        report.issue = f"Unable to inspect app page: {exc}"
        return report

    report.sample_links = sample_links(page)
    report.marker_count = page.locator("a[href], button").count()

    url_lower = report.final_url.lower()
    title_lower = report.title.lower()
    needs_auth = any(token in url_lower for token in APP_AUTH_HINTS)
    needs_auth = needs_auth or has_any_locator(page, "input[type='email'], input[type='password']")

    if needs_auth:
        report.status = "auth_required"
        report.issue = "App surface needs authentication or app session handoff."
    else:
        report.status = "ok"
        report.issue = ""

    if expected_text:
        page_text = ""
        try:
            page_text = page.inner_text("body").lower()
        except Exception:
            pass
        if expected_text.lower() not in title_lower and expected_text.lower() not in page_text:
            report.status = "assertion_failed"
            report.issue = f"Expected text not found on app side: {expected_text!r}"

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Shopify both-side smoke test in Playwright.")
    parser.add_argument("--store-domain", required=True, help="Store domain (prefix or full myshopify domain).")
    parser.add_argument(
        "--admin-url",
        default="",
        help="Optional explicit admin URL override. Default: https://<store-domain>/admin/products",
    )
    parser.add_argument(
        "--storefront-url",
        default="",
        help="Optional explicit storefront URL override. Default: https://<store-domain>/collections/all",
    )
    parser.add_argument(
        "--app-url",
        default="",
        help="Optional Shopify app URL to validate in the same session.",
    )
    parser.add_argument("--admin-path", default="/admin/products", help="Admin path if --admin-url is not provided.")
    parser.add_argument(
        "--storefront-path",
        default="/collections/all",
        help="Storefront path if --storefront-url is not provided.",
    )
    parser.add_argument(
        "--user-data-dir",
        default="",
        help="Playwright persistent profile directory. Default: ~/.scbe-playwright-shopify",
    )
    parser.add_argument("--timeout-ms", type=int, default=60000, help="Navigation timeout in milliseconds.")
    parser.add_argument(
        "--screenshot-dir",
        default="artifacts/shopify-both-side",
        help="Output directory for screenshots and report.",
    )
    parser.add_argument("--expect-admin-text", default="", help="Optional text assertion for admin page.")
    parser.add_argument("--expect-storefront-text", default="", help="Optional text assertion for storefront page.")
    parser.add_argument("--expect-app-text", default="", help="Optional text assertion for app page.")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True, help="Run in headless mode.")
    parser.add_argument("--headed", dest="headless", action="store_false", help="Run with visible browser window.")
    parser.add_argument("--keep-open", action="store_true", help="Keep browser open until Enter is pressed.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless both sides are status=ok.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    store_domain = normalize_store_domain(args.store_domain)
    admin_url = args.admin_url or f"https://{store_domain}{ensure_path_fragment(args.admin_path)}"
    storefront_url = args.storefront_url or f"https://{store_domain}{ensure_path_fragment(args.storefront_path)}"

    profile_dir = args.user_data_dir or str(Path.home() / ".scbe-playwright-shopify")
    out_dir = Path(args.screenshot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    admin_report = SideReport(side="admin", requested_url=admin_url)
    storefront_report = SideReport(side="storefront", requested_url=storefront_url)
    app_report = SideReport(side="app", requested_url=args.app_url) if args.app_url else None

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=profile_dir, headless=args.headless)
        admin_page = context.new_page()
        storefront_page = context.new_page()
        app_page = context.new_page() if args.app_url else None

        try:
            admin_page.goto(admin_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            storefront_page.goto(storefront_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            if app_page and args.app_url:
                app_page.goto(args.app_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        except Exception as exc:
            admin_report.status = "error"
            storefront_report.status = "error"
            admin_report.issue = f"Navigation error: {exc}"
            storefront_report.issue = f"Navigation error: {exc}"
            if app_report is not None:
                app_report.status = "error"
                app_report.issue = f"Navigation error: {exc}"

        admin_png = out_dir / f"{stamp}-admin.png"
        storefront_png = out_dir / f"{stamp}-storefront.png"
        app_png = out_dir / f"{stamp}-app.png"
        try:
            admin_page.screenshot(path=str(admin_png), full_page=True)
            admin_report.screenshot = str(admin_png)
        except Exception as exc:
            admin_report.issue = (
                admin_report.issue + " | " if admin_report.issue else ""
            ) + f"Admin screenshot failed: {exc}"
        try:
            storefront_page.screenshot(path=str(storefront_png), full_page=True)
            storefront_report.screenshot = str(storefront_png)
        except Exception as exc:
            storefront_report.issue = (storefront_report.issue + " | " if storefront_report.issue else "") + (
                f"Storefront screenshot failed: {exc}"
            )
        if app_page and app_report is not None:
            try:
                app_page.screenshot(path=str(app_png), full_page=True)
                app_report.screenshot = str(app_png)
            except Exception as exc:
                app_report.issue = (
                    app_report.issue + " | " if app_report.issue else ""
                ) + f"App screenshot failed: {exc}"

        if admin_report.status != "error":
            admin_report = evaluate_admin_page(admin_page, admin_report, args.expect_admin_text)
        if storefront_report.status != "error":
            storefront_report = evaluate_storefront_page(
                storefront_page, storefront_report, args.expect_storefront_text
            )
        if app_page and app_report is not None and app_report.status != "error":
            app_report = evaluate_app_page(app_page, app_report, args.expect_app_text)

        report = {
            "generated_at": now_iso(),
            "store_domain": store_domain,
            "headless": args.headless,
            "profile_dir": profile_dir,
            "admin": asdict(admin_report),
            "storefront": asdict(storefront_report),
        }
        if app_report is not None:
            report["app"] = asdict(app_report)

        report_path = out_dir / f"{stamp}-report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(f"[shopify-both-side] store={store_domain}")
        print(f"[shopify-both-side] admin_status={admin_report.status} url={admin_report.final_url or admin_url}")
        print(
            f"[shopify-both-side] storefront_status={storefront_report.status} url={storefront_report.final_url or storefront_url}"
        )
        if app_report is not None:
            print(f"[shopify-both-side] app_status={app_report.status} url={app_report.final_url or args.app_url}")
        print(f"[shopify-both-side] report={report_path}")

        if args.keep_open:
            input("Browser is open. Press Enter to close... ")

        context.close()

    if args.strict:
        statuses = [admin_report.status, storefront_report.status]
        if app_report is not None:
            statuses.append(app_report.status)
        return 0 if all(status == "ok" for status in statuses) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
