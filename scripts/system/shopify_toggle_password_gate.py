#!/usr/bin/env python3
"""Inspect or toggle Shopify storefront password protection via Playwright."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from playwright.sync_api import sync_playwright


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_store_slug(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    raw = raw.split("/", 1)[0]
    if raw.endswith(".myshopify.com"):
        raw = raw.split(".myshopify.com", 1)[0]
    if raw.startswith("admin.shopify.com/store/"):
        raw = raw.split("/", 3)[-1]
    if "." in raw:
        raw = raw.split(".", 1)[0]
    if not raw:
        raise ValueError("Invalid store value")
    return raw


def detect_storefront_gate(page: Any) -> Tuple[Optional[Any], bool]:
    probes = [
        "label:has-text('Restrict access to visitors with the password') input[type='checkbox']",
        "label:has-text('Password protection') input[type='checkbox']",
        "input[name*='password'][type='checkbox']",
        "input[id*='password'][type='checkbox']",
    ]
    for selector in probes:
        locator = page.locator(selector)
        if locator.count() > 0:
            checkbox = locator.first
            return checkbox, bool(checkbox.is_checked())
    return None, False


def click_save(page: Any) -> bool:
    save_selectors = [
        "button:has-text('Save')",
        "[data-save-bar] button:has-text('Save')",
        "button[aria-label='Save']",
    ]
    for selector in save_selectors:
        locator = page.locator(selector)
        if locator.count() == 0:
            continue
        try:
            locator.first.click(timeout=5000)
            page.wait_for_timeout(1600)
            return True
        except Exception:
            continue
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit or disable Shopify storefront password gate.")
    parser.add_argument("--store", default="aethermore-code", help="Store slug or domain")
    parser.add_argument("--user-data-dir", default=str(Path.home() / ".scbe-playwright-shopify"))
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--headed", dest="headless", action="store_false")
    parser.add_argument("--apply", action="store_true", help="Disable password protection if currently enabled")
    parser.add_argument("--out", default="artifacts/shopify-password-gate")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store_slug = normalize_store_slug(args.store)
    target_url = f"https://admin.shopify.com/store/{store_slug}/settings/preferences"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    screenshot_path = out_dir / f"{stamp}-preferences.png"
    report_path = out_dir / f"{stamp}-report.json"

    report: Dict[str, Any] = {
        "generated_at": now_iso(),
        "store_slug": store_slug,
        "target_url": target_url,
        "apply": bool(args.apply),
        "ok": False,
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            headless=args.headless,
        )
        page = context.new_page()
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2600)

            # Shopify admin may briefly present anti-bot interstitial pages.
            # Give it time to settle before we inspect controls.
            for _ in range(8):
                title = page.title()
                if "just a moment" not in title.lower():
                    break
                page.wait_for_timeout(1500)

            report["final_url"] = page.url
            report["title"] = page.title()

            checkbox, gate_enabled = detect_storefront_gate(page)
            report["gate_found"] = checkbox is not None
            report["gate_status"] = "enabled" if gate_enabled else "disabled" if checkbox is not None else "not_found"

            action = "none"
            save_clicked = False
            if args.apply and checkbox is not None and gate_enabled:
                checkbox.click()
                page.wait_for_timeout(900)
                save_clicked = click_save(page)
                action = "disabled_password_gate" if save_clicked else "toggled_without_save"
                checkbox_after, gate_enabled_after = detect_storefront_gate(page)
                report["gate_found_after"] = checkbox_after is not None
                report["gate_status_after"] = (
                    "enabled" if gate_enabled_after else "disabled" if checkbox_after is not None else "not_found"
                )

            report["action"] = action
            report["save_clicked"] = save_clicked
            report["ok"] = True
        except Exception as exc:  # noqa: BLE001
            report["error"] = str(exc)
        finally:
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass
            report["screenshot"] = str(screenshot_path)
            context.close()

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report.get("ok", False), "report": str(report_path), "data": report}, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
