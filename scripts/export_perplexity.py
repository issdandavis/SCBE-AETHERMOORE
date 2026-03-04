#!/usr/bin/env python3
"""
Export Perplexity Library threads to raw JSON files.

Flow:
1) Open Perplexity library (auth via saved storage state or optional credentials).
2) Scroll library feed to collect thread links.
3) Open each thread and extract message-like text blocks.
4) Save one JSON file per thread under data/perplexity/raw_json.

Examples:
  python scripts/export_perplexity.py --headless
  python scripts/export_perplexity.py --headed --state-file .secrets/perplexity_state.json
  python scripts/export_perplexity.py --email "$PERPLEXITY_EMAIL" --password "$PERPLEXITY_PASSWORD"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_LIBRARY_URL = "https://www.perplexity.ai/library"
DEFAULT_LOGIN_URL = "https://www.perplexity.ai/login"
DEFAULT_RAW_DIR = "data/perplexity/raw_json"
DEFAULT_STATE_FILE = "data/perplexity/perplexity_state.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, max_len: int = 96) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    if not value:
        value = "thread"
    return value[:max_len].rstrip("-")


def likely_thread_url(url: str, host: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc and parsed.netloc != host:
        return False

    path = (parsed.path or "/").rstrip("/")
    if path in ("", "/"):
        return False

    # Exclude known non-thread routes.
    excluded_exact = ("/library",)
    excluded_prefix = (
        "/library",
        "/discover",
        "/settings",
        "/pricing",
        "/about",
        "/pro",
        "/enterprise",
        "/auth",
        "/login",
        "/join",
    )
    if path in excluded_exact:
        return False
    if any(path.startswith(x + "/") for x in excluded_prefix if x != "/library"):
        return False

    # Typical Perplexity thread paths include /search/ or nested /library/*.
    if "/search/" in path:
        return True
    if path.startswith("/library/"):
        return True

    # Generic fallback: nested path depth with slug-like segment.
    segments = [seg for seg in path.split("/") if seg]
    return len(segments) >= 2


def unique_output_path(base_dir: Path, stem: str, source_url: str) -> Path:
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:10]
    return base_dir / f"{stem}-{digest}.json"


def thread_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    segments = [seg for seg in parsed.path.split("/") if seg]
    candidate = segments[-1] if segments else ""
    candidate = re.sub(r"[^a-zA-Z0-9._-]+", "-", candidate).strip("-")
    if candidate:
        return candidate[:96]
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def save_thread(
    thread_id: str,
    title: str,
    url: str,
    messages: list[dict[str, str]],
    label: str = "",
    output_dir: Path | None = None,
) -> Path:
    if output_dir is None:
        output_dir = Path(DEFAULT_RAW_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "-", (thread_id or "").strip())
    safe_id = safe_id.strip("-")
    if not safe_id:
        safe_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    out_path = output_dir / f"{safe_id}.json"
    payload = {
        "id": thread_id,
        "title": title,
        "url": url,
        "label": label,
        "message_count": len(messages),
        "messages": messages,
        "exported_at": utc_now(),
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


@dataclass
class ExportConfig:
    library_url: str
    login_url: str
    raw_dir: Path
    state_file: Path
    save_state_file: Path | None
    headless: bool
    timeout_ms: int
    scroll_pause_ms: int
    max_scrolls: int
    settle_ms: int
    max_threads: int
    discover_only: bool
    manual_login: bool
    email: str | None
    password: str | None


def parse_args() -> ExportConfig:
    parser = argparse.ArgumentParser(
        description="Export Perplexity Library threads to raw JSON files."
    )
    parser.add_argument("--library-url", default=DEFAULT_LIBRARY_URL)
    parser.add_argument("--login-url", default=DEFAULT_LOGIN_URL)
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--save-state-file", default="")

    head_group = parser.add_mutually_exclusive_group()
    head_group.add_argument("--headless", action="store_true")
    head_group.add_argument("--headed", action="store_true")

    parser.add_argument("--timeout-ms", type=int, default=45_000)
    parser.add_argument("--scroll-pause-ms", type=int, default=1200)
    parser.add_argument("--max-scrolls", type=int, default=80)
    parser.add_argument("--settle-ms", type=int, default=900)
    parser.add_argument("--max-threads", type=int, default=0)
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--manual-login", action="store_true")

    parser.add_argument("--email", default=os.getenv("PERPLEXITY_EMAIL"))
    parser.add_argument("--password", default=os.getenv("PERPLEXITY_PASSWORD"))

    args = parser.parse_args()
    if args.headed:
        headless = False
    elif args.headless:
        headless = True
    else:
        headless = bool(os.getenv("CI"))

    save_state_file = Path(args.save_state_file) if args.save_state_file else None
    return ExportConfig(
        library_url=str(args.library_url),
        login_url=str(args.login_url),
        raw_dir=Path(args.raw_dir),
        state_file=Path(args.state_file),
        save_state_file=save_state_file,
        headless=headless,
        timeout_ms=int(args.timeout_ms),
        scroll_pause_ms=int(args.scroll_pause_ms),
        max_scrolls=int(args.max_scrolls),
        settle_ms=int(args.settle_ms),
        max_threads=int(args.max_threads),
        discover_only=bool(args.discover_only),
        manual_login=bool(args.manual_login),
        email=(args.email or None),
        password=(args.password or None),
    )


def load_playwright() -> tuple[Any, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Playwright is required. Install with:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc
    return sync_playwright, PlaywrightTimeoutError


def login_if_needed(page: Any, cfg: ExportConfig, timeout_err: Any) -> None:
    # Heuristic: if password field exists or we are on auth route, try credentials flow.
    current_url = page.url.lower()
    needs_auth = "/auth/" in current_url or "/login" in current_url
    if not needs_auth:
        try:
            needs_auth = page.locator("input[type='password']").count() > 0
        except Exception:  # noqa: BLE001
            needs_auth = False

    if not needs_auth:
        return

    if not cfg.email or not cfg.password:
        raise RuntimeError(
            "Perplexity appears to require login, but no credentials were provided. "
            "Pass --email/--password or reuse a valid --state-file."
        )

    page.goto(cfg.login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    email_selectors = (
        "input[type='email']",
        "input[name='email']",
        "input[autocomplete='email']",
    )
    for selector in email_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.fill(cfg.email)
            break

    click_selectors = (
        "button:has-text('Continue')",
        "button:has-text('Next')",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
    )
    for selector in click_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.click()
            page.wait_for_timeout(500)
            break

    pass_selectors = (
        "input[type='password']",
        "input[name='password']",
        "input[autocomplete='current-password']",
    )
    for selector in pass_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.fill(cfg.password)
            break

    for selector in click_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.click()
            page.wait_for_timeout(900)
            break

    try:
        page.wait_for_load_state("networkidle", timeout=cfg.timeout_ms)
    except timeout_err:
        # Continue; we validate by trying to access library page next.
        pass

    page.goto(cfg.library_url, wait_until="domcontentloaded")


def collect_links(page: Any, cfg: ExportConfig) -> list[dict[str, str]]:
    host = urlparse(cfg.library_url).netloc
    collected: dict[str, dict[str, str]] = {}
    stable_rounds = 0
    prev_count = 0

    for _ in range(cfg.max_scrolls):
        # Fast-path thread discovery based on common Perplexity thread routes.
        direct_links = page.query_selector_all("a[href*='/search/'], a[href*='/library/']")
        for anchor in direct_links:
            href = str(anchor.get_attribute("href") or "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = f"https://{host}{href}"
            text = (anchor.inner_text() or "").strip()
            if likely_thread_url(href, host):
                if href not in collected:
                    collected[href] = {"url": href, "label": text}

        anchors = page.evaluate(
            """
            () => Array.from(document.querySelectorAll("a[href]")).map(a => ({
              href: a.href || "",
              text: (a.textContent || "").trim()
            }))
            """
        )
        for row in anchors:
            href = str(row.get("href") or "").strip()
            text = str(row.get("text") or "").strip()
            if not href:
                continue
            if likely_thread_url(href, host):
                if href not in collected:
                    collected[href] = {"url": href, "label": text}

        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(350)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(cfg.scroll_pause_ms)

        current_count = len(collected)
        if current_count == prev_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
            prev_count = current_count

        if stable_rounds >= 3:
            break

    rows = list(collected.values())
    rows.sort(key=lambda r: r["url"])
    return rows


def extract_messages_fallback(page: Any) -> list[dict[str, str]]:
    rows = page.evaluate(
        """
        () => {
          const picked = [];
          const selectors = [
            "[data-message-author-role]",
            "[data-testid*='message']",
            "[class*='message']",
            "[class*='answer']",
            "[class*='query']",
            "main p",
            "main li"
          ];
          const nodes = selectors.flatMap((sel) => Array.from(document.querySelectorAll(sel)));
          const seen = new Set();
          for (const node of nodes) {
            const text = (node.textContent || "").replace(/\\s+/g, " ").trim();
            if (!text || text.length < 2) continue;
            if (seen.has(text)) continue;
            seen.add(text);

            const marker = [
              node.getAttribute("data-message-author-role") || "",
              node.getAttribute("data-testid") || "",
              node.className || ""
            ].join(" ");
            let role = "unknown";
            if (/user|question|query/i.test(marker)) role = "user";
            if (/assistant|answer|response/i.test(marker)) role = "assistant";
            picked.push({ role, text });
          }

          if (picked.length === 0) {
            const main = document.querySelector("main") || document.body;
            const lines = (main.textContent || "")
              .split(/\\n+/)
              .map((x) => x.replace(/\\s+/g, " ").trim())
              .filter((x) => x.length > 8)
              .slice(0, 400);
            return lines.map((text) => ({ role: "unknown", text }));
          }

          return picked.slice(0, 800);
        }
        """
    )
    out: list[dict[str, str]] = []
    for row in rows:
        role = str(row.get("role") or "unknown")
        text = str(row.get("text") or "").strip()
        if text:
            out.append({"role": role, "content": text})
    return out


def extract_messages(page: Any) -> list[dict[str, str]]:
    # Primary strategy: message bubbles by class naming.
    bubbles = page.query_selector_all("div[class*='message']")
    messages: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for bubble in bubbles:
        text = (bubble.inner_text() or "").strip()
        if not text:
            continue

        class_attr = (bubble.get_attribute("class") or "").lower()
        if "assistant" in class_attr or "answer" in class_attr:
            role = "assistant"
        elif "user" in class_attr or "human" in class_attr or "question" in class_attr:
            role = "user"
        else:
            role = "unknown"

        key = (role, text)
        if key in seen:
            continue
        seen.add(key)
        messages.append({"role": role, "content": text})

    if messages:
        return messages

    # Fallback strategy for differing DOM structures.
    return extract_messages_fallback(page)


def export_threads(cfg: ExportConfig) -> dict[str, Any]:
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.state_file.parent.mkdir(parents=True, exist_ok=True)

    sync_playwright, timeout_err = load_playwright()
    library_links: list[dict[str, str]] = []
    exported: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=cfg.headless)

        context_kwargs: dict[str, Any] = {}
        if cfg.state_file.exists():
            context_kwargs["storage_state"] = str(cfg.state_file)
        context = browser.new_context(**context_kwargs)

        page = context.new_page()
        page.set_default_timeout(cfg.timeout_ms)
        if cfg.manual_login:
            if cfg.headless:
                raise RuntimeError("--manual-login requires headed mode. Use --headed.")
            page.goto(cfg.login_url, wait_until="domcontentloaded")
            print("Log in manually, then press Enter.")
            input()
        else:
            page.goto(cfg.library_url, wait_until="domcontentloaded")
            page.wait_for_timeout(cfg.settle_ms)
            login_if_needed(page, cfg, timeout_err)
        page.goto(cfg.library_url, wait_until="domcontentloaded")
        page.wait_for_timeout(cfg.settle_ms)

        library_links = collect_links(page, cfg)
        if cfg.max_threads > 0:
            library_links = library_links[: cfg.max_threads]
        print(f"Found {len(library_links)} threads.")

        index_payload = {
            "generated_at": utc_now(),
            "library_url": cfg.library_url,
            "thread_count": len(library_links),
            "threads": library_links,
        }
        (cfg.raw_dir / "_index.json").write_text(
            json.dumps(index_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if not cfg.discover_only:
            for idx, row in enumerate(library_links):
                url = row["url"]
                label = row.get("label") or ""
                print(f"[{idx + 1}/{len(library_links)}] Exporting: {url}")
                thread_page = context.new_page()
                thread_page.set_default_timeout(cfg.timeout_ms)
                try:
                    thread_page.goto(url, wait_until="domcontentloaded")
                    thread_page.wait_for_timeout(cfg.settle_ms)
                    title = thread_page.title()
                    final_url = thread_page.url
                    messages = extract_messages(thread_page)
                    thread_url = final_url or url
                    thread_id = thread_id_from_url(thread_url)
                    out_path = save_thread(
                        thread_id=thread_id,
                        title=title,
                        url=thread_url,
                        messages=messages,
                        label=label,
                        output_dir=cfg.raw_dir,
                    )
                    exported.append(
                        {
                            "index": idx + 1,
                            "id": thread_id,
                            "title": title,
                            "url": thread_url,
                            "file": str(out_path),
                            "message_count": len(messages),
                        }
                    )
                finally:
                    thread_page.close()

        save_path = cfg.save_state_file or cfg.state_file
        context.storage_state(path=str(save_path))
        context.close()
        browser.close()

    manifest = {
        "generated_at": utc_now(),
        "library_url": cfg.library_url,
        "raw_dir": str(cfg.raw_dir),
        "discover_only": cfg.discover_only,
        "thread_links_found": len(library_links),
        "thread_files_written": len(exported),
        "threads": exported,
    }
    (cfg.raw_dir / "_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def main() -> int:
    cfg = parse_args()
    try:
        manifest = export_threads(cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"[export_perplexity] ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
