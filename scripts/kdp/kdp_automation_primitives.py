"""KDP browser-automation primitives — the hard-won parts.

WHY THIS EXISTS
---------------
Publishing one Kindle eBook through KDP via Playwright took ~3 hours of trial
and error. Every wall hit during that run is captured below as a reusable
primitive so the next book is minutes, not hours.

KDP's forms are React-bound on top of Amazon's AUI (Amazon UI) widgets. The
React layer does NOT fire its onChange/onInput handlers when DOM values are
set the normal way (Playwright `fill()`, JS `el.value = x`, JS `el.click()`).
You must either dispatch synthetic events on the native HTMLElement prototype
setter, or use OS-level mouse events (Playwright `locator.click()`).

READ-ME-FIRST GOTCHAS
---------------------
1.  Never kill the user's main Chrome to enable CDP. Launch a SECOND Chrome
    with `--remote-debugging-port=9222 --user-data-dir=<isolated profile>`.
    Cookies persist across launches if the profile dir is preserved.

2.  AUI selects (`<select name="react-aui-N">`) need the native prototype
    setter PLUS dispatched input+change events. `select_option` alone does
    not reliably propagate to React state.

3.  Text inputs (price fields, etc.) need character-by-character typing with
    a per-char delay so React's onInput synthetic event fires for each char.
    Playwright `fill()` and JS `.value=` both bypass React.

4.  KDP's category modal uses cascading react-aui selects (react-aui-1 →
    react-aui-3 → react-aui-5 ...). Each option's value is JSON-encoded like
    `{"level":N,"key":"X","nodeId":"NNN"}`. Selecting a higher level
    dynamically creates the next-level select in the DOM.

5.  AI questionnaire confirmation is an MDN-style checkbox: `role="checkbox"`
    with `aria-labelledby`. Standard `<input type="checkbox">` does not exist
    for those. Use real-click on the element.

6.  When the Publish click succeeds, Playwright throws "Execution context
    was destroyed, most likely because of a navigation" — this exception IS
    the success signal. URL ends at `/bookshelf?publishedId=<asin>`.

7.  Use "+ Create Kindle eBook" on the bookshelf row of an existing paperback
    to seed the Kindle flow with pre-filled title/subtitle/description/
    keywords/author. URL: `/title-setup/kindle/new/details?existing=<id>&item=<id>`.

8.  Pandoc-built EPUBs need an explicit CSS rule to put each chapter on its
    own page. See packages/bookforge/src/scbe_bookforge/ebook.py for the
    `h1 { page-break-before: always; -epub-page-break-before: always; }` fix.

9.  Detect upload completion by searching `document.body.innerText` for
    "uploaded successfully!" — KDP does NOT use "Upload Successful" anywhere.

10. The save-error banner reads "Please fix the highlighted error(s) to
    continue" generically — the real reason lives in the side-nav status
    ("Pricing Not Started...") and the hidden `div[id$="-field-error"]`
    elements. If a "save successful" toast appeared but Publish failed, the
    save persisted draft state but a different field is failing server-side
    validation. Trace the navigation status, not the banner.

USAGE
-----
    from kdp_automation_primitives import (
        connect_cdp, react_select, react_type, click_mdn_checkbox,
        wait_for_upload, click_publish_via_navigation,
    )

    page = connect_cdp("http://localhost:9222", url_substr="/title-setup/kindle/")
    react_select(page, 'select[name="react-aui-1"]',
                 match=lambda t: "Religion & Spirituality" in t)
    react_type(page, 'input[name="data[digital][channels][amazon][US][price_vat_inclusive]"]', "5.99")
    click_mdn_checkbox(page, label_substr="confirm that my answers are accurate")
    wait_for_upload(page, filename="miracle-memory.epub")
    new_url = click_publish_via_navigation(page, "#save-and-publish-announce")
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

try:
    from playwright.sync_api import Page, sync_playwright
    from playwright._impl._errors import Error as PlaywrightError
except ImportError as e:
    raise SystemExit("Install: pip install playwright && playwright install chromium") from e


CDP_URL_DEFAULT = "http://localhost:9222"


def launch_cdp_chrome(
    profile_dir: str,
    url: str = "https://kdp.amazon.com/en_US/bookshelf",
    chrome_exe: Optional[str] = None,
    port: int = 9222,
) -> None:
    """Launch a separate CDP-enabled Chrome on an isolated profile.

    Never kills the user's main Chrome. Cookies persist if the profile dir
    is reused across launches.
    """
    chrome_exe = chrome_exe or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            chrome_exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--new-window",
            url,
        ],
        close_fds=True,
    )


def connect_cdp(cdp_url: str = CDP_URL_DEFAULT, url_substr: Optional[str] = None) -> Page:
    """Attach to a CDP-enabled Chrome and return the matching page.

    The Playwright object stays alive for the caller's lifetime — caller
    is responsible for not letting `sync_playwright()` exit prematurely.
    Prefer calling this from inside a `with sync_playwright() as p:` block
    and using `p.chromium.connect_over_cdp(...)` directly.
    """
    p = sync_playwright().start()
    browser = p.chromium.connect_over_cdp(cdp_url)
    pages = [pg for ctx in browser.contexts for pg in ctx.pages]
    if url_substr:
        page = next((pg for pg in pages if url_substr in pg.url), None)
        if page is None:
            raise RuntimeError(f"No page matching '{url_substr}'. Open tabs: {[pg.url for pg in pages]}")
    else:
        page = pages[0] if pages else None
        if page is None:
            raise RuntimeError("No pages open")
    page.bring_to_front()
    return page


def react_select(page: Page, selector: str, *, match: Callable[[str], bool]) -> dict:
    """Pick an option in a React-bound AUI <select> so React state updates.

    Uses the native HTMLSelectElement prototype setter + dispatches input
    and change events on the element so React picks up the value change.
    Plain JS `el.value = x` does NOT work — React tracks the previous value
    on the element instance via a hidden property and skips its handler
    when the value changes "outside" its event pipeline.
    """
    # Pass the textual matcher into the page so it can find the right option
    result = page.evaluate(
        """([sel, needleRegexSrc]) => {
            const el = document.querySelector(sel);
            if (!el) return {error: 'no element', sel};
            const re = new RegExp(needleRegexSrc, 'i');
            const opt = Array.from(el.options).find(o => re.test(o.text));
            if (!opt) return {error: 'no matching option', sel, optsCount: el.options.length};
            const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
            setter.call(el, opt.value);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return {set: opt.value.slice(0, 200), text: opt.text};
        }""",
        [selector, _callable_to_regex(match)],
    )
    return result


def _callable_to_regex(match: Callable[[str], bool]) -> str:
    """If `match` was created via `make_regex`, recover its source. Otherwise
    fall back to a wildcard — caller should pass `make_regex(...)` directly."""
    src = getattr(match, "_regex_src", None)
    return src if src else ".*"


def make_regex(pattern: str) -> Callable[[str], bool]:
    """Wrap a regex string so `react_select` can ship it to the page.

    Example: `react_select(page, sel, match=make_regex(r"^Religious Fiction$"))`
    """
    rx = re.compile(pattern, re.IGNORECASE)
    fn: Callable[[str], bool] = lambda t: bool(rx.search(t))
    fn._regex_src = pattern  # type: ignore[attr-defined]
    return fn


def react_type(page: Page, selector: str, value: str, delay_ms: int = 80) -> None:
    """Type a value into a React-bound text input so its onInput fires.

    Playwright `fill()` and JS `.value=` both bypass React's onInput. The
    only reliable way is character-by-character keyboard typing with a
    small per-char delay. Tab at the end commits any blur-based handler.
    """
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    el.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    time.sleep(0.3)
    page.keyboard.type(value, delay=delay_ms)
    time.sleep(0.4)
    page.keyboard.press("Tab")
    time.sleep(1.5)


def click_mdn_checkbox(page: Page, *, label_substr: str) -> dict:
    """Click an MDN-style checkbox (`role="checkbox"`, no <input>).

    Used by KDP for AI questionnaire confirmation and several other
    attestation boxes. Real DOM click fires React's handler.
    """
    return page.evaluate(
        """(needle) => {
            const re = new RegExp(needle.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'i');
            const cb = Array.from(document.querySelectorAll('[role="checkbox"]')).find(e => {
                if (e.getAttribute('aria-checked') === 'true') return false;
                const parent = e.parentElement;
                return re.test((parent?.innerText || '') + ' ' + (e.getAttribute('aria-labelledby') || ''));
            });
            if (!cb) return {error: 'no checkbox', needle};
            cb.click();
            return {clicked: true, ariaChecked: cb.getAttribute('aria-checked'),
                    label: (cb.parentElement?.innerText||'').slice(0,150)};
        }""",
        label_substr,
    )


def wait_for_upload(page: Page, *, filename: str, timeout_s: int = 180, poll_s: float = 2.0) -> bool:
    """Wait until KDP shows the uploaded filename in the page body.

    KDP's success text reads `"<filename>" uploaded successfully!`. There
    is no progress bar polling; the file appears in the body when ready.
    """
    fn_escaped = re.escape(filename)
    elapsed = 0.0
    while elapsed < timeout_s:
        ok = page.evaluate(f"""() => {{
                const body = (document.body.innerText || '').replace(/\\s+/g, ' ');
                return /{fn_escaped}/i.test(body);
            }}""")
        if ok:
            return True
        time.sleep(poll_s)
        elapsed += poll_s
    return False


def click_publish_via_navigation(page: Page, selector: str, timeout_s: int = 30) -> str:
    """Click a Publish/Save-and-Publish button. Catches the navigation
    exception (which IS the success signal) and returns the post-publish URL.

    On the Kindle pricing page, the publish button is `#save-and-publish-announce`.
    Successful publish redirects to `/bookshelf?publishedId=<asin>`.
    """
    btn = page.locator(selector).first
    btn.scroll_into_view_if_needed()
    time.sleep(0.5)
    pre_url = page.url
    try:
        btn.click()
    except PlaywrightError:
        pass

    elapsed = 0.0
    while elapsed < timeout_s:
        try:
            url = page.url
        except PlaywrightError:
            time.sleep(1.0)
            elapsed += 1.0
            continue
        if url != pre_url:
            return url
        time.sleep(1.0)
        elapsed += 1.0
    return page.url


KINDLE_FROM_PAPERBACK_URL = (
    "https://kdp.amazon.com/en_US/title-setup/kindle/new/details" "?existing={paperback_id}&item={paperback_id}"
)


def kindle_from_paperback_url(paperback_asin: str) -> str:
    """URL that seeds a new Kindle setup from a published paperback.

    Pre-fills title, subtitle, description (CKEditor HTML), keywords,
    author. You still pick categories and answer AI/accessibility/DRM.
    """
    return KINDLE_FROM_PAPERBACK_URL.format(paperback_id=paperback_asin)


if __name__ == "__main__":
    # Print the gotcha list so curl-style invocation surfaces the key knowledge.
    print(__doc__)
