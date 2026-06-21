---
name: run-ai-browser
description: Build, run, screenshot, and drive the SCBE AI browser (python/scbe/ai_browser.py + browser_{controller,grid,map,camera,autodrive}.py). Use when asked to run/launch/drive/screenshot the AI browser, browse a site headlessly, observe a page as data, or autonomously fill+submit+navigate a website.
---

# Run the SCBE AI browser

The AI browser turns a website into a bounded, observable, steerable surface: a **data feed** (`read`),
a **bounded move set** (`act`), a per-site **sudoku coordinate grid**, a StarCraft-style **document map**
(whole-page minimap + 3-state fog + `move_camera`), and an **autonomous on_step driver** (`AutoDriver`)
that runs high-level intents and returns an honest trace. It drives an **isolated headless Chrome** via
Playwright — it never touches your real browser.

The agent path is **one driver script** that exercises the whole stack against a real site and writes a
screenshot. Paths below are relative to the repo root (the worktree dir, e.g. `slice-wt/`).

## Prerequisites

Python ≥ 3.11, Google Chrome installed, and Playwright (the Python package only — the driver launches the
system Chrome via `channel='chrome'`, so no `playwright install` browser download is needed):

```bash
pip install playwright
```

Verify Chrome is launchable headless (this is the exact check I ran):

```bash
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True, channel='chrome'); print('chrome OK', b.version); b.close(); p.stop()"
```

## Run (agent path) — the driver

Drive the full stack end-to-end (launch → observe → screenshot → autonomously search+navigate → camera),
from the repo root:

```bash
PYTHONPATH=. python .claude/skills/run-ai-browser/driver.py
```

It prints 5 stages and writes a gridded screenshot to `artifacts/ai_browser_view.png`. Real output from
this container:

```
[1] LAUNCH    https://en.wikipedia.org/wiki/Main_Page
    page: 'Wikipedia, the free encyclopedia' | interactive elements: 262
[2] OBSERVE   document 1280x3792 px | viewport rect ['A1', 'A2', 'A3', 'B1']
    fog: {'hidden': 59, 'seen': 0, 'visible': 26} | available_actions: 144 (59 move_camera) | map cells: 42
[3] VIEW      gridded screenshot -> .../artifacts/ai_browser_view.png (270188 bytes) | occupied cells: ['A1', 'A2', 'A5', ...]
[4] DRIVE     task='Hyperbolic geometry'
      [OK] fill 'search' <- 'Hyperbolic geometry' Search Wikipedia
      [OK] submit
      [OK] assert_url <- 'Hyperbolic'         https://en.wikipedia.org/wiki/Hyperb
    success: True | landed: https://en.wikipedia.org/wiki/Hyperbolic_geometry
[5] CAMERA    move_camera(C12): scroll y 0 -> 18985 (camera panned down the document)

END-TO-END OK  screenshot: .../artifacts/ai_browser_view.png
```

The screenshot is the live page with the coordinate grid overlaid (red grid lines, blue cells on every
interactive element) — open `artifacts/ai_browser_view.png` to view it.

Drive a different site / task:

```bash
PYTHONPATH=. python .claude/skills/run-ai-browser/driver.py --url https://en.wikipedia.org/wiki/Main_Page --task "Rubik's Cube" --out artifacts/rubik.png
```

## Direct invocation (drive it from code)

Most PRs touch the modules directly. Import and drive without the full demo:

```bash
PYTHONPATH=. python -c "
from python.scbe.ai_browser import AIBrowser
from python.scbe.browser_autodrive import AutoDriver, fill, submit, assert_url
with AIBrowser(headless=True) as br:
    drv = AutoDriver(br, br.open('https://en.wikipedia.org/wiki/Main_Page'))
    res = drv.run([fill('search','Hyperbolic geometry'), submit(), assert_url('Hyperbolic')])
    print(res['success'], res['final_url'])
"
```

Key entry points (all in `python/scbe/`): `AIBrowser.read/act/park/snapshot`, `browser_grid.grid_map` +
`render_grid`, `browser_map.MapView.observe`, `browser_camera.Camera.observe`/`move_camera`,
`browser_autodrive.AutoDriver.run`.

## Test

The execution-verified suite (32 tests; most run a real headless Chrome, all skip cleanly if none):

```bash
PYTHONPATH=. python -m pytest tests/test_ai_browser.py tests/test_browser_controller.py tests/test_browser_grid.py tests/test_browser_map.py tests/test_browser_camera.py tests/test_browser_autodrive.py -q
```

## Gotchas (battle scars from driving real sites)

- **Refs go stale on re-render.** Real sites swap elements out after you type (Wikipedia replaces its
  search input), detaching the `data-aibref` element. Never cache a ref across an action — re-`read()`
  each step (`AutoDriver` does). For submit, use `Move('submit')` (presses Enter on whatever is **focused**),
  not Enter on a ref — the ref may already be gone.
- **URLs percent-encode.** `Rubik's` becomes `Rubik%27s` and spaces become `%20`, so a naive
  `assert_url("Rubik's")` fails on a page it actually reached. Assert on alphanumeric tokens (`Rubik`).
- **`scrollIntoView` doesn't move sticky/fixed elements.** Some "off-screen" elements are in a sticky
  header/footer; scrolling to them by ref does nothing. To guarantee a pan, `move_camera` by **doc-cell
  label** (`"C12"` → `window.scrollTo`), not by element ref.
- **System Chrome, not a download.** `channel='chrome'` launches the installed Google Chrome, so you skip
  the ~150 MB `playwright install chromium`. The profile is **isolated** (a fresh temp profile) — it cannot
  see or disturb your real browser's tabs/login.
- **Headless by default.** `--headed` needs a real display; in a headless container stay headless.
- **Do NOT point this at Colab/Google login.** The isolated profile isn't signed in and Google blocks
  automated credential entry — that's a separate, fragile path (`tools/colab/`), not this driver.

## Troubleshooting

- `ModuleNotFoundError: No module named 'python'` → run from the **repo root** with `PYTHONPATH=.`.
- `playwright ... has no attribute` / import error → `pip install playwright`.
- Chrome won't launch (`channel='chrome'` not found) → install Google Chrome, or `playwright install
  chromium` and change `channel='chrome'` to `channel='chromium'` in `AIBrowser.__enter__`.
- Tests all **skip** with "no launchable browser" → Chrome isn't installed; install it (the logic is
  intentional so CI without a browser doesn't hang).
