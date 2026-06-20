"""colab_run: drive a Colab notebook from the terminal by attaching to YOUR already-running Chrome.

Google ships no headless CLI for hosted Colab, so the robust path is to reuse your authenticated
browser session: launch Chrome ONCE with --remote-debugging-port, log into Colab, then this tool
attaches over CDP (Playwright connect_over_cdp), opens the notebook, runs all cells, waits out the
run, and prints the output that contains a completion marker back to your terminal.

TRANSPORTS (this implements #1; #2 is a flag; #3 is documented):
  1. ATTACH (default, recommended NOW): connect to a running Chrome you started with
     --remote-debugging-port=9222 -- reuses your live Google login, no re-auth, works with HOSTED
     paid Colab. The most robust PRACTICAL choice for hosted Colab.
  2. LAUNCH (--launch): Playwright opens its own Chrome with a persistent --profile you log into once.
     Use if you cannot expose a debug port. Google may flag automation in that profile.
  3. RUNTIME SOCKET (not built here): talk to the Jupyter kernel directly, bypassing the UI -- the most
     robust ceiling, but for HOSTED Colab the kernel endpoint is proxied/rotated by Google and not
     cleanly extractable. It only pays off for a LOCAL/self-hosted runtime (see scbe-n8n-colab-bridge).

SETUP (one time, on the machine with your browser):
  Windows:  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
              --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\\.colab-cdp-profile"
  Log into Colab in that window, then:
  python tools/colab/colab_run.py --dry-run                       # confirm attach + notebook load
  python tools/colab/colab_run.py --run                           # run-all, wait, print the result

DOM caveat: Colab's UI is not a stable automation target. Run-all uses the Ctrl+F9 shortcut (robust);
completion is detected by polling for --done-marker in the outputs (robust -- it watches YOUR notebook's
printed result, not Colab's run-state DOM). The trust-dialog / Connect-button selectors are best-effort;
--dry-run lets you confirm the attach + load before committing to a long training run.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Optional

# the VTC lift notebook on GitHub, opened through Colab's github loader (no manual import)
DEFAULT_NOTEBOOK = (
    "https://colab.research.google.com/github/issdandavis/SCBE-AETHERMOORE/blob/main/"
    "notebooks/vtc_lift_qwen15_colab.ipynb"
)
DEFAULT_MARKER = "NET LIFT"  # code_lift.render() prints this at the very end of the run


def _log(msg: str) -> None:
    print("[colab_run] %s" % msg, file=sys.stderr, flush=True)


def resolve_notebook(name_or_url: Optional[str]) -> str:
    """A full URL passes through. A bare name is looked up in the repo's Colab catalog if available,
    else falls back to the default VTC notebook."""
    if not name_or_url:
        return DEFAULT_NOTEBOOK
    if name_or_url.startswith("http"):
        return name_or_url
    try:  # reuse the existing catalog instead of reinventing URL construction
        sys.path.insert(0, ".")
        from scripts.system.colab_workflow_catalog import resolve_notebook_payload  # type: ignore

        payload = resolve_notebook_payload(name_or_url)
        url = (payload or {}).get("colab_url")
        if url:
            return url
    except Exception as exc:
        _log("catalog lookup failed (%s); using the name as-is" % exc)
    return name_or_url


def _find_colab_page(browser: Any, want_url: str):
    """Return an existing Colab tab if one is open, else None (caller opens a fresh page)."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                if "colab.research.google.com" in (pg.url or ""):
                    return pg
            except Exception:
                continue
    return None


def _click_text(page: Any, texts: list, timeout_ms: int = 4000) -> bool:
    """Best-effort: click the first visible button/menuitem whose text matches (trust dialog, Connect)."""
    for t in texts:
        try:
            loc = page.get_by_role("button", name=t)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=timeout_ms)
                _log("clicked %r" % t)
                return True
        except Exception:
            pass
        try:
            loc = page.get_by_text(t, exact=False)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=timeout_ms)
                _log("clicked text %r" % t)
                return True
        except Exception:
            pass
    return False


def _outputs_text(page: Any) -> str:
    """Concatenate all rendered cell output text (robust to Colab's exact cell DOM)."""
    js = (
        "Array.from(document.querySelectorAll("
        "'.output_area, .output, .output_text, pre, .lazy-output'))"
        ".map(e => e.innerText || e.textContent || '').join('\\n')"
    )
    try:
        return page.evaluate(js) or ""
    except Exception:
        return ""


def open_notebook(page: Any, url: str, load_timeout_ms: int = 60000) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=load_timeout_ms)
    page.wait_for_timeout(3000)
    # non-Google notebooks pop a trust modal; runtime may need connecting
    _click_text(page, ["Run anyway", "Run Anyway"])
    _click_text(page, ["Connect", "Reconnect"])


def run_all(page: Any) -> None:
    """Trigger Run all. Ctrl+F9 is Colab's shortcut and survives DOM churn better than menu-clicking."""
    page.bring_to_front()
    page.keyboard.press("Control+F9")
    page.wait_for_timeout(1500)
    # a fresh tab may surface the trust modal only now
    if _click_text(page, ["Run anyway", "Run Anyway"]):
        page.wait_for_timeout(1000)
        page.keyboard.press("Control+F9")


def _extract_block(text: str, marker: str) -> Optional[str]:
    """Return the output block ending at/after the LAST occurrence of `marker` (from the preceding
    blank line), or None if the marker is absent. Pure -- unit-tested without a browser."""
    if not text or marker not in text:
        return None
    idx = text.rfind(marker)
    start = text.rfind("\n\n", 0, idx)
    return text[start if start >= 0 else 0 :].strip()


def wait_for_marker(page: Any, marker: str, timeout_s: int, poll_s: int = 15) -> Optional[str]:
    """Poll the rendered outputs until `marker` appears (the run finished and printed its result), or
    timeout. Returns the output block containing the marker, or None on timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        text = _outputs_text(page)
        block = _extract_block(text, marker)
        if block is not None:
            return block
        remaining = int(deadline - time.time())
        _log("running... (%ds left, %d chars of output so far)" % (remaining, len(text)))
        page.wait_for_timeout(poll_s * 1000)
    return None


def run(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        raise SystemExit("playwright not installed -- run: pip install playwright")

    url = resolve_notebook(args.notebook)
    _log("notebook: %s" % url)
    with sync_playwright() as p:
        if args.launch:
            _log("LAUNCH mode: own Chrome, persistent profile %s (log into Colab if prompted)" % args.profile)
            ctx = p.chromium.launch_persistent_context(args.profile, headless=False)
            browser = ctx.browser
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
        else:
            _log("ATTACH mode: connecting to Chrome on CDP port %d" % args.port)
            browser = p.chromium.connect_over_cdp("http://localhost:%d" % args.port)
            page = _find_colab_page(browser, url)
            if page is None:
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if args.upload:  # best-effort: hand a local file to a pending files.upload() input
            _log("will try to satisfy a files.upload() input with %s" % args.upload)

        # always (re)load the target notebook so we know what is running
        open_notebook(page, url)
        cells = 0
        try:
            cells = page.evaluate("document.querySelectorAll('.cell').length")
        except Exception:
            pass
        _log("notebook loaded (%s cells detected)" % cells)

        if args.dry_run:
            print("DRY RUN ok: attached + loaded the notebook. Re-run with --run to execute.")
            return 0

        if args.upload:
            try:
                page.set_input_files("input[type=file]", args.upload, timeout=8000)
                _log("uploaded %s into a file input" % args.upload)
            except Exception as exc:
                _log("no file input ready (%s); prefer Drive/URL delivery in the notebook" % exc)

        _log("triggering Run all (Ctrl+F9)...")
        run_all(page)
        block = wait_for_marker(page, args.done_marker, args.timeout)
        if block is None:
            print("TIMEOUT after %ds without seeing marker %r." % (args.timeout, args.done_marker))
            print("The run may still be going -- check the browser, or raise --timeout.")
            return 2
        print("\n===== Colab result (matched marker %r) =====" % args.done_marker)
        print(block)
        return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="colab-run", description="drive a Colab notebook from the terminal via your browser"
    )
    ap.add_argument("--notebook", default=None, help="Colab URL, a catalog name, or omit for the VTC lift notebook")
    ap.add_argument("--port", type=int, default=9222, help="CDP port of your running Chrome (ATTACH mode)")
    ap.add_argument(
        "--launch", action="store_true", help="LAUNCH mode: own Chrome + persistent profile instead of attach"
    )
    ap.add_argument("--profile", default=".colab-cdp-profile", help="profile dir for --launch mode")
    ap.add_argument("--upload", default=None, help="best-effort: local file to feed a pending files.upload() input")
    ap.add_argument(
        "--done-marker", default=DEFAULT_MARKER, help="text that signals the run finished (default: 'NET LIFT')"
    )
    ap.add_argument("--timeout", type=int, default=5400, help="max seconds to wait for the marker (default 90 min)")
    ap.add_argument("--dry-run", action="store_true", help="attach + load the notebook, but do NOT run (verify setup)")
    ap.add_argument("--run", action="store_true", help="run all cells and wait for the result")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if not (a.run or a.dry_run):
        ap.error("pass --dry-run (verify setup) or --run (execute)")
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
