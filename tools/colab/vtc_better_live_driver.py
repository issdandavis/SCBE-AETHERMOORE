"""Drive the live VTC Better Colab run over a single CDP connection.

This script owns the CDP session for the duration of the run. Other monitors
should read only the log file it writes, not attach to Chrome concurrently.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


TARGET = (
    "https://colab.research.google.com/github/issdandavis/SCBE-AETHERMOORE/"
    "blob/main/notebooks/vtc_better_colab.ipynb#scrollTo=SILKYVpiO3uG"
)


def write_log(path: Path, line: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {line}\n")
        fh.flush()
    print(line, flush=True)


def find_colab_page(browser):
    pages = [page for context in browser.contexts for page in context.pages]
    for page in pages:
        if "colab.research.google.com" in page.url:
            return page
    if not pages:
        raise RuntimeError("No browser pages are available over CDP")
    return pages[0]


def click_first(page, labels: list[str], timeout: int = 2500) -> bool:
    for label in labels:
        candidates = [
            lambda: page.get_by_text(label, exact=True),
            lambda: page.get_by_role("button", name=re.compile(re.escape(label), re.I)),
        ]
        for make_locator in candidates:
            try:
                loc = make_locator()
                if loc.count() > 0:
                    loc.first.click(timeout=timeout)
                    return True
            except Exception:
                continue
    return False


def body_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception as exc:  # pragma: no cover - live browser diagnostic
        return f"BODY_TEXT_ERROR: {exc!r}"


def feed_upload_if_present(page, upload: Path, log: Path) -> bool:
    frames = [page.main_frame, *[frame for frame in page.frames if frame is not page.main_frame]]
    for frame_index, frame in enumerate(frames):
        try:
            inputs = frame.locator("input[type=file]")
            count = inputs.count()
        except Exception:
            continue
        for idx in range(count):
            try:
                inputs.nth(idx).set_input_files(str(upload), timeout=8000)
                write_log(log, f"fed upload frame={frame_index} input={idx}: {upload}")
                return True
            except Exception as exc:
                write_log(log, f"upload frame={frame_index} input={idx} not ready: {exc!r}")
    return False


def extract_result(text: str) -> str | None:
    markers = [
        r"NET LIFT[^\n\r]*",
        r"newly solved ids:[^\n\r]*",
        r"regressed ids\s*:[^\n\r]*",
    ]
    hits: list[str] = []
    for pattern in markers:
        hits.extend(re.findall(pattern, text, flags=re.I))
    if not hits:
        return None
    return "\n".join(dict.fromkeys(hits))


def ensure_runtime_connected(page, log: Path, timeout_s: int = 600) -> bool:
    deadline = time.time() + timeout_s
    clicked = False
    while time.time() < deadline:
        text = body_text(page)
        if "RAM" in text and "Connect" not in text[:1200]:
            write_log(log, "runtime appears connected")
            return True
        if not clicked or "Connect" in text[:1600]:
            if click_first(page, ["Connect"], timeout=5000):
                write_log(log, "clicked Connect")
                clicked = True
        click_first(page, ["Run anyway", "Yes", "OK"], timeout=1000)
        time.sleep(10)
    write_log(log, "BLOCKED: runtime did not connect before timeout")
    page.screenshot(path=str(log.with_suffix(".connect-timeout.png")), full_page=False)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--upload", required=True)
    parser.add_argument("--notebook-url", default=TARGET)
    parser.add_argument("--log", default=r"C:\Users\issda\AppData\Local\Temp\vtc_better_live_driver.log")
    parser.add_argument("--timeout-min", type=int, default=180)
    args = parser.parse_args()

    upload = Path(args.upload)
    log = Path(args.log)
    if not upload.exists():
        raise FileNotFoundError(upload)
    if log.exists():
        log.unlink()

    deadline = time.time() + args.timeout_min * 60
    last_len = -1
    last_upload = 0.0

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
        page = find_colab_page(browser)
        write_log(log, f"attached title={page.title()!r} url={page.url}")

        target = args.notebook_url
        if "vtc_better_colab.ipynb" not in page.url or "feat/vtc-better-colab-runnable" not in page.url:
            write_log(log, "navigating to vtc_better_colab")
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
        if "vtc_better_colab.ipynb" not in page.url:
            write_log(log, f"BLOCKED: target navigation did not stick; url={page.url}")
            return 6

        text = body_text(page)
        if "Sign in" in text:
            write_log(log, "BLOCKED: Chrome profile is not signed in")
            page.screenshot(path=str(log.with_suffix(".signin.png")), full_page=False)
            return 2

        write_log(log, f"ready title={page.title()!r} url={page.url}")
        page.screenshot(path=str(log.with_suffix(".before.png")), full_page=False)

        if not ensure_runtime_connected(page, log):
            return 7

        if click_first(page, ["Run all"], timeout=5000):
            write_log(log, "clicked visible Run all")
        else:
            write_log(log, "Run all button not found; opening Runtime menu")
            if not click_first(page, ["Runtime"], timeout=5000):
                write_log(log, "BLOCKED: Runtime menu not found")
                return 3
            page.wait_for_timeout(750)
            if not click_first(page, ["Run all", "Run all cells"], timeout=5000):
                write_log(log, "BLOCKED: Runtime -> Run all not found")
                return 3

        page.wait_for_timeout(1500)
        click_first(page, ["Run anyway", "Yes", "OK"], timeout=2000)

        while time.time() < deadline:
            if "vtc_better_colab.ipynb" not in page.url:
                write_log(log, f"BLOCKED: Colab bounced to another notebook; url={page.url}")
                page.screenshot(path=str(log.with_suffix(".wrong-notebook.png")), full_page=False)
                return 6

            text = body_text(page)
            if len(text) != last_len:
                write_log(log, f"page_chars={len(text)}")
                last_len = len(text)

            lowered = text.lower()
            if "sign in" in lowered:
                write_log(log, "BLOCKED: sign-in returned during run")
                page.screenshot(path=str(log.with_suffix(".signin-returned.png")), full_page=False)
                return 2

            if "runtime disconnected" in lowered or "reconnect" in lowered:
                write_log(log, "WARNING: runtime disconnected/reconnect text visible")

            if time.time() - last_upload > 15:
                if feed_upload_if_present(page, upload, log):
                    last_upload = time.time()
                else:
                    last_upload = time.time()

            result = extract_result(text)
            if result and "newly solved ids" in result.lower():
                write_log(log, "RESULT:\n" + result)
                page.screenshot(path=str(log.with_suffix(".result.png")), full_page=False)
                return 0

            if "Traceback (most recent call last)" in text or "CUDA out of memory" in text:
                tail = text[-3000:].replace("\r", "")
                write_log(log, "ERROR_TEXT_TAIL:\n" + tail)
                page.screenshot(path=str(log.with_suffix(".error.png")), full_page=False)
                return 4

            time.sleep(20)

        page.screenshot(path=str(log.with_suffix(".timeout.png")), full_page=False)
        write_log(log, "TIMEOUT waiting for NET LIFT/result")
        return 5


if __name__ == "__main__":
    sys.exit(main())
