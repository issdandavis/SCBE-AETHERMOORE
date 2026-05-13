# KDP browser automation — guidance letter to future-you

If you're about to publish another book through KDP, read `kdp_automation_primitives.py` first. It's both the module and the letter — every gotcha that cost real time on the *Miracle Was The Memory* run is at the top of that file.

## The shape of a KDP publish run

1. Build artifacts via bookforge: `python -m scbe_bookforge.cli build bookforge.json`
2. Launch isolated CDP Chrome — never touch the user's main browser
3. Sign in to KDP once in that window; cookies persist for re-launches
4. For an eBook that mirrors a paperback: open the bookshelf, click **+ Create Kindle eBook** on the paperback row → metadata pre-fills
5. Pick 3 category placements (Religion → Religious Fiction → Christian → leaf, etc.)
6. Upload EPUB + cover JPG; wait for `"<filename>" uploaded successfully!` text in body
7. AI questionnaire: set Yes, fill tools, click the MDN confirmation checkbox
8. Save & Continue
9. Pricing: All territories, KDP Select, 70% royalty, USD price via character-by-character typing
10. Click Publish — catch the "execution context destroyed" exception; the URL ending in `?publishedId=<asin>` is success

## Hardest-won lessons

- **CDP attach > driving the user's Chrome.** The user's running Chrome can't have CDP enabled retroactively. Launch a second Chrome with `--remote-debugging-port=9222 --user-data-dir=<isolated>`. Cookies persist in the isolated dir across CDP-Chrome restarts.
- **React-AUI selects** need the native HTMLSelectElement prototype setter PLUS dispatched input+change events. `select_option`, JS `.value=`, JS `.click()` all silently fail to update React state.
- **Category modal** uses cascading `react-aui-1/3/5/7...` selects with JSON-encoded option values (`{"level":N,"key":"...","nodeId":"..."}`). Pick the top level, the next level appears.
- **MDN-style checkboxes** (`role="checkbox"`, `aria-labelledby="mdn-checkbox-label-:rN:"`) need real `.click()` on the element. They're not real `<input type="checkbox">`.
- **Price field** needs character-by-character typing with per-char delay. `fill("5.99")` sets the DOM but React's onInput never fires, the royalty grid stays at $0.00, Publish gets rejected with a generic "highlighted error" banner pointing at nothing.
- **Publish click destroys the execution context** — that exception is the success signal. The Playwright `evaluate` after will throw; catch it, check the URL.
- **EPUB chapter page breaks** need explicit CSS — pandoc's default doesn't insert visual breaks even with `--split-level=1`. The fix lives in `packages/bookforge/src/scbe_bookforge/ebook.py`.

## When KDP shows a generic error

The save-error banner reads "Please fix the highlighted error(s) to continue" with nothing visibly highlighted. Don't trust it. Check:

1. Side nav status — the failing step says "Not Started..." instead of "Complete"
2. `div[id$="-field-error"]` containers — look for ones WITHOUT `jele-invisible` class
3. React state for the form values — if your DOM has the price but the React state doesn't, the price-grid display will show $0.00 instead of the royalty amount. That's the tell.

## What KDP needs

A CLI. Until they ship one, this directory exists.
