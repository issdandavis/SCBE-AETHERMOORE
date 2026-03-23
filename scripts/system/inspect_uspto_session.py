#!/usr/bin/env python3
"""Inspect a live USPTO browser session through the AetherBrowser CDP lane.

This script is intentionally conservative:
- it does not capture form field values
- it does not print cookies
- it only records structural/auth-state metadata for session triage
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agents.browsers.cdp_backend import CDPBackend


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_URL = "https://patentcenter.uspto.gov/"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def trim_text(value: str, limit: int = 180) -> str:
    collapsed = " ".join((value or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def cookie_domain_summary(cookies: list[dict[str, Any]]) -> dict[str, Any]:
    domains: dict[str, int] = {}
    secure = 0
    http_only = 0
    for cookie in cookies:
        domain = str(cookie.get("domain", "")).lstrip(".") or "<unknown>"
        domains[domain] = domains.get(domain, 0) + 1
        if cookie.get("secure"):
            secure += 1
        if cookie.get("httpOnly"):
            http_only += 1
    ordered_domains = sorted(domains.items(), key=lambda item: (-item[1], item[0]))
    return {
        "total": len(cookies),
        "secure_count": secure,
        "http_only_count": http_only,
        "domains": [{"domain": name, "count": count} for name, count in ordered_domains[:20]],
    }


def classify_session(url: str, dom: dict[str, Any]) -> dict[str, Any]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    title = str(dom.get("title", ""))
    headings = [str(h) for h in dom.get("headings", [])]
    forms = dom.get("forms", [])
    has_password = any(field.get("type") == "password" for form in forms for field in form.get("fields", []))
    patent_center_markers = ("patentcenter.uspto.gov" in hostname) or ("Patent Center" in title)
    auth_markers = ("auth.uspto.gov" in hostname) or has_password or any(
        "sign in" in heading.lower() or "login" in heading.lower() for heading in headings
    )

    if auth_markers:
        state = "auth_wall"
    elif patent_center_markers:
        state = "patent_center_surface"
    else:
        state = "unknown_surface"

    return {
        "state": state,
        "has_password_field": has_password,
        "hostname": hostname,
        "patent_center_markers": patent_center_markers,
        "auth_markers": auth_markers,
    }


async def extract_dom_summary(browser: CDPBackend) -> dict[str, Any]:
    script = """
(() => {
  const text = (v) => (v || "").replace(/\\s+/g, " ").trim();
  const short = (v, n = 180) => {
    const t = text(v);
    return t.length <= n ? t : `${t.slice(0, n - 3)}...`;
  };
  const headings = Array.from(document.querySelectorAll("h1,h2,h3"))
    .map((el) => short(el.textContent, 120))
    .filter(Boolean)
    .slice(0, 12);
  const buttons = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button']"))
    .map((el) => short(el.innerText || el.value || el.getAttribute("aria-label") || "", 80))
    .filter(Boolean)
    .slice(0, 20);
  const links = Array.from(document.querySelectorAll("a[href]"))
    .map((el) => ({
      text: short(el.textContent || el.getAttribute("aria-label") || "", 80),
      href: el.href || ""
    }))
    .filter((row) => row.text || row.href)
    .slice(0, 20);
  const forms = Array.from(document.forms).slice(0, 10).map((form) => ({
    id: form.id || "",
    name: form.getAttribute("name") || "",
    method: (form.getAttribute("method") || "get").toLowerCase(),
    action: form.action || "",
    fields: Array.from(form.querySelectorAll("input, select, textarea")).slice(0, 20).map((field) => ({
      tag: field.tagName.toLowerCase(),
      type: (field.getAttribute("type") || "").toLowerCase(),
      name: field.getAttribute("name") || "",
      id: field.id || "",
      placeholder: short(field.getAttribute("placeholder") || "", 60),
      autocomplete: field.getAttribute("autocomplete") || "",
      required: !!field.required
    }))
  }));
  return {
    title: document.title || "",
    heading: short(document.querySelector("h1,h2,h3")?.textContent || "", 160),
    headings,
    buttons,
    links,
    forms
  };
})()
"""
    result = await browser.execute_script(script)
    if not isinstance(result, dict):
        raise RuntimeError("DOM extraction returned a non-object payload")
    return result


async def inspect_session(host: str, port: int, url: str, settle_seconds: float) -> dict[str, Any]:
    browser = CDPBackend(host=host, port=port)
    if not await browser.initialize():
        raise RuntimeError(f"Failed to initialize CDP on {host}:{port}")

    try:
        await browser.navigate(url)
        await asyncio.sleep(settle_seconds)
        final_url = await browser.execute_script("window.location.href")
        dom = await extract_dom_summary(browser)
        cookies = await browser.get_cookies()
        screenshot = await browser.screenshot()
    finally:
        await browser.close()

    final_url = str(final_url or url)
    classification = classify_session(final_url, dom)
    cookie_summary = cookie_domain_summary(cookies)

    report_dir = PROJECT_ROOT / "artifacts" / "smokes" / f"uspto-session-{utc_stamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = report_dir / "uspto_session.png"
    screenshot_path.write_bytes(screenshot)

    report = {
        "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_url": url,
        "final_url": final_url,
        "classification": classification,
        "title": trim_text(str(dom.get("title", "")), 200),
        "heading": trim_text(str(dom.get("heading", "")), 200),
        "headings": dom.get("headings", []),
        "buttons": dom.get("buttons", []),
        "links": dom.get("links", []),
        "forms": dom.get("forms", []),
        "cookie_summary": cookie_summary,
        "screenshot_path": str(screenshot_path),
    }
    report_path = report_dir / "uspto_session_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"report_path": str(report_path), **report}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a live USPTO browser session via Chrome CDP.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = asyncio.run(inspect_session(args.host, args.port, args.url, args.settle_seconds))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"USPTO session report: {payload['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
