"""colab_run: drive a hosted Colab notebook from the terminal, in a real (logged-in) Chrome.

Google ships no headless CLI for hosted Colab, and it BLOCKS sign-in in a Playwright-launched browser
(the --enable-automation flag trips Chrome's 'unsupported command-line flag' bar + Google's 'this
browser may not be secure' wall). The robust path, validated live: launch a PLAIN chrome.exe ourselves
with only a debug port (no automation flags, so Google lets you sign in), ATTACH over CDP (attaching
adds no automation flag), open the notebook, run all cells (Ctrl+F9), and print the output block that
contains a completion marker back to your terminal.

FLOW (default):
  1. We start chrome.exe with --remote-debugging-port + a persistent --profile (login persists there).
  2. First run only: a window opens; you do the ONE-TIME Google sign-in (a human must -- Google blocks
     automated credential entry). The tool waits for it, then proceeds; later runs are zero-touch.
  3. It attaches over CDP, opens the notebook, handles the 'Run anyway'/Connect prompts, runs all, and
     feeds --upload into the notebook's files.upload() cell so the run never blocks on the file dialog.
  4. Completion is detected by polling the OUTPUTS for --done-marker (YOUR notebook's printed result,
     e.g. 'NET LIFT'), not Colab's brittle run-state DOM.

  python tools/colab/colab_run.py --dry-run --keep-open 240    # open + (first time) sign in; verify
  python tools/colab/colab_run.py --run --upload corpus.jsonl  # run-all, wait, print the result

  --attach connects to a debug Chrome you started yourself instead of launching one. A LOCAL/self-hosted
  runtime could be driven over its Jupyter socket directly (most robust, no UI) -- but for HOSTED Colab
  that endpoint is proxied/rotated by Google, so attach-to-real-Chrome is the best practical option.

DOM caveat: Colab's UI is not a stable automation target; the trust-dialog / Connect / sign-in selectors
are best-effort and may need a one-line tweak. --dry-run confirms attach + load before a long run.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Any, Optional

# the VTC lift notebook on GitHub, opened through Colab's github loader (no manual import)
DEFAULT_NOTEBOOK = (
    "https://colab.research.google.com/github/issdandavis/SCBE-AETHERMOORE/blob/main/"
    "notebooks/vtc_lift_qwen15_colab.ipynb"
)
DEFAULT_MARKER = "NET LIFT"  # code_lift.render() prints this at the very end of the run
_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def _log(msg: str) -> None:
    print("[colab_run] %s" % msg, file=sys.stderr, flush=True)


def _chrome_path(explicit: Optional[str] = None) -> str:
    """Find a real chrome.exe. We launch Chrome OURSELVES (not via Playwright) so it carries NO
    --enable-automation flag -- that flag triggers Chrome's 'unsupported command-line' bar AND Google's
    'this browser may not be secure' login block. A plainly-launched Chrome lets you sign in normally."""
    for c in [explicit] + _CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    found = shutil.which("chrome") or shutil.which("chrome.exe")
    if found:
        return found
    raise SystemExit("could not find chrome.exe -- pass --chrome-path")


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _launch_chrome(chrome: str, port: int, profile: str, url: str) -> "subprocess.Popen":
    """Start a NORMAL Chrome with a debugging port + persistent profile (login persists, and is done in a
    non-automated browser so Google allows it). Returns the process; Playwright then attaches over CDP."""
    os.makedirs(profile, exist_ok=True)
    args = [
        chrome,
        "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % profile,
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]
    _log("launching Chrome with a debug port (sign in normally if prompted -- Google allows it here)")
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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


def _feed_upload(page: Any, upload: str) -> bool:
    """If a files.upload() input is on the page, hand it the local corpus. Returns True once fed."""
    try:
        if page.query_selector("input[type=file]"):
            page.set_input_files("input[type=file]", upload, timeout=5000)
            _log("fed corpus %s to the notebook's upload cell" % upload)
            return True
    except Exception:
        pass
    return False


def _signed_in(page: Any) -> bool:
    """True only on a POSITIVE logged-in signal (avatar, or the 'New notebook' UI that Colab shows only
    when authed). Requiring a positive signal avoids the race where a half-loaded/redirecting page has an
    empty body and a mere absence-of-'sign in' check false-positives."""
    try:
        return bool(
            page.evaluate(
                "() => {"
                "  const t=(document.body&&document.body.innerText)||'';"
                "  if (t.length<30) return false;"
                "  if ((location.host||'').includes('accounts.google.com')) return false;"
                "  if (/\\bnew notebook\\b/i.test(t)) return true;"
                "  if (document.querySelector('[aria-label*=\"Google Account\"]')) return true;"
                "  if (document.querySelector('a[href*=\"SignOutOptions\"]')) return true;"
                "  return false;"
                "}"
            )
        )
    except Exception:
        return False


def wait_for_login(page: Any, timeout_s: int, poll_s: int = 5) -> bool:
    """Hold the window open and poll until the human completes Google's sign-in (Google blocks automated
    credential entry, so the login itself is the one manual step). Returns True once signed in."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _signed_in(page):
            return True
        _log("waiting for Google sign-in in the open window... (%ds left)" % int(deadline - time.time()))
        page.wait_for_timeout(poll_s * 1000)
    return False


def wait_for_marker(
    page: Any, marker: str, timeout_s: int, poll_s: int = 12, upload: Optional[str] = None
) -> Optional[str]:
    """Poll the rendered outputs until `marker` appears (the run finished and printed its result), or
    timeout. Along the way, feed `upload` to a files.upload() input if/when one appears (so a
    terminal-driven run never blocks on the file dialog). Returns the matching block, or None."""
    deadline = time.time() + timeout_s
    fed = upload is None
    while time.time() < deadline:
        if not fed:
            fed = _feed_upload(page, upload)
        text = _outputs_text(page)
        block = _extract_block(text, marker)
        if block is not None:
            return block
        remaining = int(deadline - time.time())
        _log("running... (%ds left, %d chars of output)" % (remaining, len(text)))
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
        # NEVER let Playwright LAUNCH Chrome -- that adds --enable-automation, which trips Chrome's
        # 'unsupported command-line flag' bar AND Google's 'this browser may not be secure' login block.
        # Instead launch a plain chrome.exe with a debug port ourselves and ATTACH over CDP (attaching
        # adds no automation flag, so Google lets you sign in). A debug Chrome left open is reused.
        if not args.attach and not _port_open(args.port):
            _launch_chrome(_chrome_path(args.chrome_path), args.port, args.profile, url)
            for _ in range(60):
                if _port_open(args.port):
                    break
                time.sleep(0.5)
        if not _port_open(args.port):
            raise SystemExit(
                "no Chrome debug port on %d (launch failed; or start Chrome yourself and use --attach)" % args.port
            )
        _log("attaching over CDP on port %d" % args.port)
        browser = p.chromium.connect_over_cdp("http://localhost:%d" % args.port)
        page = _find_colab_page(browser, url)
        if page is None:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

        open_notebook(page, url)
        cells = 0
        try:
            cells = page.evaluate("document.querySelectorAll('.cell').length")
        except Exception:
            pass
        _log("notebook loaded (%s cells detected)" % cells)

        if args.dry_run:
            signed_in = _signed_in(page)
            print("DRY RUN ok: Chrome up + notebook loaded (%s cells). Google signed-in: %s." % (cells, signed_in))
            if not signed_in:
                print(
                    "  -> log into Google ONCE in the open window; the profile %s persists for later runs."
                    % args.profile
                )
            print("Re-run with --run to execute (corpus auto-fed via --upload; result printed here).")
            if args.keep_open:
                _log("keeping the window open %ds for you to sign in..." % args.keep_open)
                page.wait_for_timeout(args.keep_open * 1000)
            return 0

        # one-time Google login: hold the open window, wait for the human to sign in, then persist+proceed
        if not args.attach and not _signed_in(page):
            print("\n>>> A Chrome window is open. Sign into your Google (paid-Colab) account in it.")
            print(">>> ONE-TIME login -- it persists in %s; future runs won't ask.\n" % args.profile)
            page.goto("https://colab.research.google.com/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            _click_text(page, ["Sign in", "Sign In"])  # open Google's login flow for you
            if not wait_for_login(page, args.login_timeout):
                print("Not signed in after %ds; the window is still open -- sign in and re-run." % args.login_timeout)
                return 3
            _log("signed in -- reloading the notebook and running")
            open_notebook(page, url)

        _log("triggering Run all (Ctrl+F9)...")
        run_all(page)
        block = wait_for_marker(page, args.done_marker, args.timeout, upload=args.upload)
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
    ap.add_argument(
        "--attach",
        action="store_true",
        help="attach to a Chrome you started with --remote-debugging-port (vs the default: launch our own)",
    )
    ap.add_argument(
        "--port", type=int, default=9222, help="Chrome debug port (launched for you, or your own with --attach)"
    )
    ap.add_argument(
        "--profile",
        default=os.path.expanduser("~/.colab-cdp-profile"),
        help="persistent Chrome profile dir (login persists here)",
    )
    ap.add_argument("--chrome-path", default=None, help="path to chrome.exe (auto-detected if omitted)")
    ap.add_argument(
        "--upload", default=None, help="local corpus file fed to the notebook's files.upload() cell during the run"
    )
    ap.add_argument(
        "--done-marker", default=DEFAULT_MARKER, help="text that signals the run finished (default: 'NET LIFT')"
    )
    ap.add_argument("--timeout", type=int, default=5400, help="max seconds to wait for the marker (default 90 min)")
    ap.add_argument("--login-timeout", type=int, default=600, help="seconds to wait for a one-time Google sign-in")
    ap.add_argument(
        "--keep-open", type=int, default=0, help="with --dry-run: hold the window open N seconds (to sign in)"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="launch + load the notebook, but do NOT run (verify setup / sign in)"
    )
    ap.add_argument("--run", action="store_true", help="run all cells and wait for the result")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if not (a.run or a.dry_run):
        ap.error("pass --dry-run (verify setup) or --run (execute)")
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
