#!/usr/bin/env python3
"""
Browser-based fallback publisher for social platforms.

Use this when API credentials are missing but an authenticated browser session
exists (persistent profile or storage-state JSON).

Examples:
    python scripts/publish/post_via_browser.py --platform x --publish
    python scripts/publish/post_via_browser.py --platform linkedin --headed
    python scripts/publish/post_via_browser.py --platform medium --user-data-dir .playwright-profile
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "publish_browser"
DEFAULT_GITHUB_REPO_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE"

DEFAULT_CONTENT_FILES = {
    "x": REPO_ROOT / "content" / "articles" / "twitter_thread_geometric_skull.md",
    "linkedin": REPO_ROOT / "content" / "articles" / "linkedin_ai_governance_professional.md",
    "medium": REPO_ROOT / "content" / "articles" / "medium_geometric_skull_v2.md",
    "hackernews": REPO_ROOT / "content" / "articles" / "hackernews_harmonic_crypto.md",
    "reddit": REPO_ROOT / "content" / "articles" / "reddit_aisafety_geometric_containment.md",
}


class BrowserPostError(RuntimeError):
    """Raised when posting flow fails."""


@dataclass
class BrowserPostResult:
    platform: str
    success: bool
    status: str
    detail: str
    publish: bool
    content_file: str
    current_url: str = ""
    screenshots: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "success": self.success,
            "status": self.status,
            "detail": self.detail,
            "publish": self.publish,
            "content_file": self.content_file,
            "current_url": self.current_url,
            "screenshots": self.screenshots or [],
        }


def load_markdown_article(path: Path) -> tuple[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Content file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    lines = text.split("\n", 1)
    title = lines[0].lstrip("#").strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    return title, body


def clean_text_for_post(text: str) -> str:
    # Strip markdown links and collapse whitespace for social composer inputs.
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def platform_seed_url(platform: str) -> str:
    if platform == "x":
        return "https://x.com/compose/post"
    if platform == "linkedin":
        return "https://www.linkedin.com/feed/"
    if platform == "medium":
        return "https://medium.com/new-story"
    if platform == "hackernews":
        return "https://news.ycombinator.com/submit"
    if platform == "reddit":
        return "https://www.reddit.com/r/aisafety/submit"
    return "https://example.com"


def make_x_post_text(title: str, body: str, limit: int = 280) -> str:
    merged = clean_text_for_post(f"{title}\n\n{body}")
    if len(merged) <= limit:
        return merged
    return merged[: limit - 3].rstrip() + "..."


def make_linkedin_post_text(title: str, body: str, limit: int = 2900) -> str:
    merged = clean_text_for_post(f"{title}\n\n{body}")
    if len(merged) <= limit:
        return merged
    return merged[: limit - 3].rstrip() + "..."


async def save_page_screenshot(page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=True)


async def first_visible_locator(page, selectors: list[str], timeout_ms: int):
    for selector in selectors:
        locator = page.locator(selector)
        count = await locator.count()
        if count == 0:
            continue
        try:
            await locator.first.wait_for(state="visible", timeout=timeout_ms)
            return locator.first, selector
        except Exception:
            continue
    raise BrowserPostError(f"No visible selector matched: {selectors}")


async def fill_text_like_human(page, locator, text: str) -> None:
    await locator.click()
    try:
        await locator.fill(text)
        return
    except Exception:
        pass

    # Fallback for contenteditable elements.
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(text, delay=5)


async def detect_login_required(page, selectors: list[str]) -> bool:
    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count() == 0:
            continue
        try:
            if await locator.first.is_visible():
                return True
        except Exception:
            continue
    return False


async def detect_bot_gate(page) -> str:
    """Return a short gate identifier when anti-bot interstitial is detected."""
    try:
        title = (await page.title()).strip().lower()
    except Exception:
        title = ""
    url = (page.url or "").lower()

    if "cdn-cgi/challenge-platform" in url or "challenges.cloudflare.com" in url:
        return "cloudflare_challenge"
    if "just a moment" in title or "attention required" in title:
        return "cloudflare_interstitial"

    try:
        body_text = (await page.inner_text("body")).strip().lower()
    except Exception:
        body_text = ""
    markers = [
        "checking your browser",
        "verify you are human",
        "enable javascript and cookies",
        "ddos protection by cloudflare",
    ]
    for marker in markers:
        if marker in body_text:
            return "anti_bot_gate"
    return ""


async def post_to_x(page, title: str, body: str, publish: bool, timeout_ms: int) -> str:
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    await page.wait_for_timeout(1200)
    if "/flow/login" in page.url or "login" in page.url:
        raise BrowserPostError("X login required. Run with --bootstrap-login and --user-data-dir first.")
    if await detect_login_required(page, ["input[name='text']", "input[autocomplete='username']"]):
        raise BrowserPostError("X login required. Run with --bootstrap-login and --user-data-dir first.")

    composer, _ = await first_visible_locator(
        page,
        [
            "div[data-testid='tweetTextarea_0']",
            "div[aria-label='Post text']",
            "div[contenteditable='true'][data-testid='tweetTextarea_0']",
        ],
        timeout_ms,
    )
    await fill_text_like_human(page, composer, make_x_post_text(title, body))

    if publish:
        button, _ = await first_visible_locator(
            page,
            ["button[data-testid='tweetButtonInline']", "button[data-testid='tweetButton']"],
            timeout_ms,
        )
        await button.click()
        await page.wait_for_timeout(3000)

    return page.url


async def post_to_linkedin(page, title: str, body: str, publish: bool, timeout_ms: int) -> str:
    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    if "/login" in page.url or "checkpoint" in page.url:
        raise BrowserPostError("LinkedIn login required. Run with --bootstrap-login and --user-data-dir first.")
    if await detect_login_required(
        page,
        ["input[name='session_key']", "input#username", "a[href*='signin']"],
    ):
        raise BrowserPostError("LinkedIn login required. Run with --bootstrap-login and --user-data-dir first.")

    start_button, _ = await first_visible_locator(
        page,
        [
            "button:has-text('Start a post')",
            "button.share-box-feed-entry__trigger",
            "button[aria-label*='Start a post']",
        ],
        timeout_ms,
    )
    await start_button.click()

    editor, _ = await first_visible_locator(
        page,
        [
            "div[role='textbox'][aria-label*='Text editor']",
            "div[contenteditable='true'][role='textbox']",
            "div.ql-editor[contenteditable='true']",
        ],
        timeout_ms,
    )
    await fill_text_like_human(page, editor, make_linkedin_post_text(title, body))

    if publish:
        post_button, _ = await first_visible_locator(
            page,
            ["button:has-text('Post')", "button.share-actions__primary-action"],
            timeout_ms,
        )
        await post_button.click()
        await page.wait_for_timeout(3000)

    return page.url


async def post_to_medium(page, title: str, body: str, publish: bool, timeout_ms: int) -> str:
    await page.goto("https://medium.com/new-story", wait_until="domcontentloaded")
    await page.wait_for_timeout(1200)
    gate = await detect_bot_gate(page)
    if gate:
        raise BrowserPostError(
            "Medium anti-bot gate detected. Run with --headed --user-data-dir and complete the challenge/login once, "
            "then rerun normal posting. "
            f"gate={gate}"
        )
    if "signin" in page.url or "m/signin" in page.url:
        raise BrowserPostError("Medium login required. Run with --bootstrap-login and --user-data-dir first.")
    if await detect_login_required(
        page,
        [
            "a[href*='signin']",
            "button:has-text('Sign in')",
            "a:has-text('Sign in')",
            "button:has-text('Get started')",
        ],
    ):
        raise BrowserPostError("Medium login required. Run with --bootstrap-login and --user-data-dir first.")

    title_box, _ = await first_visible_locator(
        page,
        [
            "h1[contenteditable='true']",
            "h1[data-testid='storyTitle']",
            "h1.graf--title",
            "article h1",
        ],
        timeout_ms,
    )
    await fill_text_like_human(page, title_box, clean_text_for_post(title))

    body_box, _ = await first_visible_locator(
        page,
        [
            "div[contenteditable='true'][data-testid='editorContent']",
            "article div[contenteditable='true']",
            "p[contenteditable='true']",
        ],
        timeout_ms,
    )
    await fill_text_like_human(page, body_box, clean_text_for_post(body))

    if publish:
        publish_button, _ = await first_visible_locator(
            page,
            ["button:has-text('Publish')", "button:has-text('Review')"],
            timeout_ms,
        )
        await publish_button.click()
        await page.wait_for_timeout(2500)

    return page.url


async def post_to_hackernews(page, title: str, publish: bool, timeout_ms: int) -> str:
    await page.goto("https://news.ycombinator.com/submit", wait_until="domcontentloaded")
    if "/login" in page.url:
        raise BrowserPostError("Hacker News login required. Run with --bootstrap-login and --user-data-dir first.")
    if await detect_login_required(page, ["input[name='acct']", "input[name='pw']"]):
        raise BrowserPostError("Hacker News login required. Run with --bootstrap-login and --user-data-dir first.")

    title_box, _ = await first_visible_locator(page, ["input[name='title']"], timeout_ms)
    url_box, _ = await first_visible_locator(page, ["input[name='url']"], timeout_ms)
    await title_box.fill(clean_text_for_post(title)[:80])
    await url_box.fill(DEFAULT_GITHUB_REPO_URL)

    if publish:
        submit_button, _ = await first_visible_locator(
            page,
            ["input[type='submit'][value='submit']", "input[value='submit']"],
            timeout_ms,
        )
        await submit_button.click()
        await page.wait_for_timeout(2500)

    return page.url


async def post_to_reddit(page, title: str, body: str, publish: bool, timeout_ms: int) -> str:
    await page.goto("https://www.reddit.com/r/aisafety/submit", wait_until="domcontentloaded")
    if "/login" in page.url:
        raise BrowserPostError("Reddit login required. Run with --bootstrap-login and --user-data-dir first.")
    if await detect_login_required(page, ["input[name='username']", "a[href*='/login']"]):
        raise BrowserPostError("Reddit login required. Run with --bootstrap-login and --user-data-dir first.")

    title_box, _ = await first_visible_locator(
        page,
        ["textarea[name='title']", "input[name='title']"],
        timeout_ms,
    )
    await title_box.fill(clean_text_for_post(title)[:300])

    body_box, _ = await first_visible_locator(
        page,
        [
            "div[role='textbox'][contenteditable='true']",
            "textarea[name='text']",
            "textarea[data-testid='post-content-input']",
        ],
        timeout_ms,
    )
    await fill_text_like_human(page, body_box, clean_text_for_post(body))

    if publish:
        post_button, _ = await first_visible_locator(
            page,
            ["button:has-text('Post')", "button[data-testid='post-submit-button']"],
            timeout_ms,
        )
        await post_button.click()
        await page.wait_for_timeout(3000)

    return page.url


async def run_browser_post(args: argparse.Namespace, title: str, body: str, content_file: Path) -> BrowserPostResult:
    from playwright.async_api import async_playwright

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ARTIFACT_ROOT / f"{timestamp}_{args.platform}"
    run_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[str] = []

    async with async_playwright() as pw:
        context = None
        browser = None
        page = None

        try:
            if args.user_data_dir:
                user_data_dir = str(Path(args.user_data_dir).expanduser().resolve())
                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=not args.headed,
                    viewport={"width": 1440, "height": 960},
                )
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                browser = await pw.chromium.launch(headless=not args.headed)
                context_kwargs: dict[str, Any] = {"viewport": {"width": 1440, "height": 960}}
                if args.storage_state:
                    state_path = Path(args.storage_state).expanduser().resolve()
                    if state_path.exists():
                        context_kwargs["storage_state"] = str(state_path)
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

            page.set_default_timeout(args.timeout_ms)
            page.set_default_navigation_timeout(args.timeout_ms)

            if args.bootstrap_login:
                if not args.user_data_dir:
                    raise BrowserPostError("bootstrap-login requires --user-data-dir so session state can be saved.")
                await page.goto(platform_seed_url(args.platform), wait_until="domcontentloaded")
                await page.wait_for_timeout(args.bootstrap_seconds * 1000)
                login_path = run_dir / "bootstrap.png"
                await save_page_screenshot(page, login_path)
                screenshots.append(str(login_path))
                return BrowserPostResult(
                    platform=args.platform,
                    success=True,
                    status="bootstrap_complete",
                    detail=(
                        f"Bootstrap window closed after {args.bootstrap_seconds}s. "
                        "If login was completed, rerun without --bootstrap-login."
                    ),
                    publish=args.publish,
                    content_file=str(content_file),
                    current_url=page.url,
                    screenshots=screenshots,
                )

            before_path = run_dir / "before.png"
            await save_page_screenshot(page, before_path)
            screenshots.append(str(before_path))

            platform = args.platform
            if platform == "x":
                url = await post_to_x(page, title, body, args.publish, args.timeout_ms)
            elif platform == "linkedin":
                url = await post_to_linkedin(page, title, body, args.publish, args.timeout_ms)
            elif platform == "medium":
                url = await post_to_medium(page, title, body, args.publish, args.timeout_ms)
            elif platform == "hackernews":
                url = await post_to_hackernews(page, title, args.publish, args.timeout_ms)
            elif platform == "reddit":
                url = await post_to_reddit(page, title, body, args.publish, args.timeout_ms)
            else:
                raise BrowserPostError(f"Unsupported platform: {platform}")

            after_path = run_dir / "after.png"
            await save_page_screenshot(page, after_path)
            screenshots.append(str(after_path))

            status = "published" if args.publish else "draft_prepared"
            return BrowserPostResult(
                platform=args.platform,
                success=True,
                status=status,
                detail="Browser automation completed.",
                publish=args.publish,
                content_file=str(content_file),
                current_url=url,
                screenshots=screenshots,
            )
        except Exception as exc:
            error_path = run_dir / "error.png"
            try:
                if page:
                    await save_page_screenshot(page, error_path)
                    screenshots.append(str(error_path))
            except Exception:
                pass
            return BrowserPostResult(
                platform=args.platform,
                success=False,
                status="failed",
                detail=str(exc),
                publish=args.publish,
                content_file=str(content_file),
                current_url=(page.url if page else ""),
                screenshots=screenshots,
            )
        finally:
            if context:
                await context.close()
            if browser:
                await browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browser fallback publisher.")
    parser.add_argument(
        "--platform",
        required=True,
        choices=["x", "linkedin", "medium", "hackernews", "reddit"],
        help="Target platform.",
    )
    parser.add_argument(
        "--content-file",
        default="",
        help="Optional markdown content file path. Defaults to platform-specific article file.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Click final publish action. Without this flag, only draft/composer prep is done.",
    )
    parser.add_argument(
        "--bootstrap-login",
        action="store_true",
        help="Open target platform and wait to allow manual login into the persistent user-data-dir profile.",
    )
    parser.add_argument(
        "--bootstrap-seconds",
        type=int,
        default=120,
        help="How long to keep bootstrap window open for manual login.",
    )
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode.")
    parser.add_argument(
        "--user-data-dir",
        default="",
        help="Persistent Chromium profile directory for authenticated sessions.",
    )
    parser.add_argument(
        "--storage-state",
        default="",
        help="Playwright storage state file (JSON). Ignored when --user-data-dir is provided.",
    )
    parser.add_argument("--timeout-ms", type=int, default=30_000, help="Per-action timeout in milliseconds.")
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional file path to write result JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content_file = Path(args.content_file).expanduser().resolve() if args.content_file else DEFAULT_CONTENT_FILES[args.platform]

    try:
        title, body = load_markdown_article(content_file)
    except Exception as exc:
        payload = {
            "platform": args.platform,
            "success": False,
            "status": "failed",
            "detail": f"Failed to load content: {exc}",
            "publish": args.publish,
            "content_file": str(content_file),
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 1

    result = asyncio.run(run_browser_post(args, title=title, body=body, content_file=content_file))
    payload = result.to_dict()

    if args.output_json:
        out_path = Path(args.output_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=True))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
