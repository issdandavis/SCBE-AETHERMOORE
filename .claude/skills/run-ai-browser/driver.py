#!/usr/bin/env python3
"""driver.py -- launch + drive the SCBE AI browser end-to-end, as a user would.

The AI browser (python/scbe/ai_browser.py + browser_{controller,grid,map,camera,autodrive}.py) turns a
website into a bounded, observable, steerable surface. This driver exercises the WHOLE stack against a real
site headlessly and produces a screenshot on disk, so a future agent can confirm it actually works without
reading the code:

  1. launch an isolated headless Chrome (AIBrowser)
  2. OBSERVE  -- the SC2-style document observation (PageMinimap + 3-state fog + available_actions)
  3. VIEW     -- render the per-site coordinate-grid screenshot to --out (this is the screenshot artifact)
  4. DRIVE    -- the autonomous on_step loop: given intents, find the search box, type, submit, verify
  5. CAMERA   -- on the (tall) result page, move_camera an off-screen element into view

Run from the repo root:
    PYTHONPATH=. python .claude/skills/run-ai-browser/driver.py
    PYTHONPATH=. python .claude/skills/run-ai-browser/driver.py --url https://en.wikipedia.org/wiki/Main_Page \
        --task "Hyperbolic geometry" --out artifacts/ai_browser_view.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow running from anywhere: add the repo root (4 levels up) so python.scbe.* imports resolve
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from python.scbe.ai_browser import AIBrowser  # noqa: E402
from python.scbe.browser_autodrive import AutoDriver, assert_url, fill, submit  # noqa: E402
from python.scbe.browser_camera import Camera  # noqa: E402
from python.scbe.browser_grid import render_grid  # noqa: E402
from python.scbe.browser_map import MapView  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run-ai-browser", description="drive the SCBE AI browser end-to-end")
    ap.add_argument("--url", default="https://en.wikipedia.org/wiki/Main_Page")
    ap.add_argument("--task", default="Hyperbolic geometry", help="search query to autonomously run")
    ap.add_argument("--out", default="artifacts/ai_browser_view.png", help="gridded screenshot path")
    ap.add_argument("--headed", action="store_true", help="show the browser window (default headless)")
    a = ap.parse_args(argv)

    out = (ROOT / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with AIBrowser(headless=not a.headed) as br:
        page = br.open(a.url)
        page.set_viewport_size({"width": 1280, "height": 800})
        feed = br.read(page)
        print("[1] LAUNCH    %s" % a.url)
        print("    page: %r | interactive elements: %d" % (feed["title"][:50], len(feed["elements"])))

        # [2] OBSERVE -- the document camera (whole-page minimap + 3-state fog + legal actions)
        cam = Camera(br, page)
        obs = cam.observe()
        mv = MapView(feed)
        print("[2] OBSERVE   document %dx%d px | viewport rect %s" % (
            obs["minimap"]["doc"]["w"], obs["minimap"]["doc"]["h"], obs["viewport_rect"][:4]))
        print("    fog: %s | available_actions: %d (%d move_camera) | map cells: %d" % (
            obs["fog"], len(obs["available_actions"]),
            sum(1 for x in obs["available_actions"] if x.startswith("move_camera")),
            len(mv.observe()["minimap"]["occupied"])))

        # [3] VIEW -- the per-site coordinate-grid screenshot (the artifact)
        shot = render_grid(br, page, str(out))
        print("[3] VIEW      gridded screenshot -> %s (%d bytes) | occupied cells: %s ..." % (
            shot["path"], out.stat().st_size, shot["occupied_cells"][:6]))

        # [4] DRIVE -- the autonomous on_step loop, by intent
        drv = AutoDriver(br, page)
        # assert on the first word, alphanumerics only -- URLs percent-encode apostrophes/spaces
        first = "".join(ch for ch in a.task.split()[0] if ch.isalnum())
        res = drv.run([fill("search", a.task), submit(), assert_url(first)])
        print("[4] DRIVE     task=%r" % a.task)
        for s in res["trace"]:
            print("      [%s] %-34s %s" % (s["status"].upper(), s["intent"], (s["detail"] or "")[:36]))
        print("    success: %s | landed: %s" % (res["success"], res["final_url"]))

        # [5] CAMERA -- scroll the camera to the furthest-down occupied doc-cell on the (tall) result page
        cam2 = Camera(br, page)
        if cam2.minimap.by_cell:
            target = max(cam2.minimap.by_cell, key=lambda c: c[1])  # max row = furthest down the document
            label = cam2.minimap.label(target)
            y0 = cam2.observe()["scroll"]["y"]
            cam2.move_camera(label)  # scrollTo a doc-cell -> reliably scrolls
            print("[5] CAMERA    move_camera(%s): scroll y %d -> %d (camera panned down the document)" % (
                label, y0, cam2.observe()["scroll"]["y"]))

        ok = res["success"] and out.exists() and out.stat().st_size > 0
        print("\n%s  screenshot: %s" % ("END-TO-END OK" if ok else "END-TO-END FAILED", out))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
