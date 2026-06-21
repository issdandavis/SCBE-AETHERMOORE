"""Peek at the live Colab page over CDP: detect a blocking files.upload widget, running cells, and dump
the tail of the visible output so we can SEE whether the run is training or stuck."""
import sys

from playwright.sync_api import sync_playwright

WANT = sys.argv[1] if len(sys.argv) > 1 else "colab.research.google.com"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://localhost:9222")
    pages = [pg for ctx in b.contexts for pg in ctx.pages]
    page = next((pg for pg in pages if WANT in (pg.url or "")), None)
    if not page:
        print("page not found; tabs:")
        for pg in pages:
            print("  ", (pg.url or "")[:90])
        raise SystemExit(1)

    file_inputs = page.evaluate("() => document.querySelectorAll('input[type=file]').length")
    # Colab marks an executing cell with .code-has-output + a spinner; count visible spinners
    spinners = page.evaluate("() => document.querySelectorAll('paper-spinner-lite[active], .running, mwc-circular-progress').length")
    txt = page.evaluate(
        "() => Array.from(document.querySelectorAll('.output, .outputview, .output-content, .stream'))"
        ".map(e => e.innerText).join(String.fromCharCode(10))"
    )
    txt = txt or ""
    err = "Traceback" in txt or "Error" in txt
    print("file_upload_inputs:", file_inputs, "| spinners:", spinners, "| has_error_text:", err, "| out_len:", len(txt))
    print("---- OUTPUT TAIL ----")
    print(txt[-2200:])
