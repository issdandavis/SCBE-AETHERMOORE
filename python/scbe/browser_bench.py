"""browser_bench: a real-task benchmark for the AI browser + a data-extraction work function.

Two things, both against LIVE sites (not fixtures):
  * run_bench() -- a suite of diverse browser tasks (search->land, multi-hop click, off-screen scroll, lead
    extraction) each with a verifiable outcome; returns the pass rate. This is the number that proves the
    stack works end-to-end, not just in unit tests.
  * gather_summaries(topics) -- USES the browser to do real work: for each topic, search Wikipedia, land on
    the article, and extract the lead paragraph; returns a dataset you can write to disk.

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_bench import run_bench, gather_summaries
    with AIBrowser(headless=True) as br:
        rep = run_bench(br)                       # {'passed': n, 'total': m, 'results': [...]}
        data = gather_summaries(br, ['Hyperbolic geometry', 'Reinforcement learning'])
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .ai_browser import AIBrowser, Move
from .browser_autodrive import AutoDriver, assert_url, click, fill, submit
from .browser_camera import Camera

WIKI = "https://en.wikipedia.org/wiki/Main_Page"


def _alnum(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum())


def _lead_paragraph(page) -> str:
    """The first substantial paragraph of a Wikipedia article (the 'real work' extraction)."""
    return page.evaluate(
        "() => { for (const p of document.querySelectorAll('#mw-content-text p, p')) {"
        "  const t = (p.innerText || '').trim(); if (t.length > 80) return t; } return ''; }"
    )


# ---- benchmark tasks: each returns (passed: bool, detail: str) given a fresh AIBrowser ----


def _task_search(query: str, expect: str) -> Callable[[AIBrowser], Any]:
    def run(br: AIBrowser):
        drv = AutoDriver(br, br.open(WIKI))
        res = drv.run([fill("search", query), submit(), assert_url(_alnum(expect))])
        return res["success"], res["final_url"]

    return run


def _task_multihop(br: AIBrowser):
    """Search to an article, then CLICK an in-article link to a second article (two hops)."""
    drv = AutoDriver(br, br.open(WIKI))
    res = drv.run([fill("search", "StarCraft"), submit(), assert_url("StarCraft"),
                   click("Warcraft"), assert_url("Warcraft")])
    return res["success"], res["final_url"]


def _task_extract(br: AIBrowser):
    """Land on an article and EXTRACT a non-empty lead paragraph that mentions the topic."""
    drv = AutoDriver(br, br.open(WIKI))
    res = drv.run([fill("search", "Hyperbolic geometry"), submit(), assert_url("Hyperbolic")])
    if not res["success"]:
        return False, "did not land"
    lead = _lead_paragraph(drv.page)
    ok = len(lead) > 80 and "geometr" in lead.lower()
    return ok, (lead[:70] + "...") if lead else "(empty lead)"


def _task_scroll_camera(br: AIBrowser):
    """On a tall article, move_camera to the furthest-down occupied cell and confirm the page scrolled."""
    page = br.open("https://en.wikipedia.org/wiki/StarCraft")
    page.set_viewport_size({"width": 1280, "height": 800})
    cam = Camera(br, page)
    if not cam.minimap.by_cell:
        return False, "no elements"
    target = max(cam.minimap.by_cell, key=lambda c: c[1])
    y0 = cam.observe()["scroll"]["y"]
    cam.move_camera(cam.minimap.label(target))
    y1 = cam.observe()["scroll"]["y"]
    return y1 > y0, "scroll %d -> %d" % (y0, y1)


def _task_honest_fail(br: AIBrowser):
    """A nonexistent target MUST fail honestly (the trust property): success=False, not a faked pass."""
    drv = AutoDriver(br, br.open(WIKI))
    res = drv.run([click("this-control-does-not-exist-zzz")])
    # this task 'passes' iff the driver correctly REPORTED failure
    return (res["success"] is False), "reported success=%s (want False)" % res["success"]


def tasks() -> List[Dict[str, Any]]:
    return [
        {"name": "search:Hyperbolic geometry", "fn": _task_search("Hyperbolic geometry", "Hyperbolic")},
        {"name": "search:Rubik's Cube", "fn": _task_search("Rubik's Cube", "Rubik")},
        {"name": "search:StarCraft", "fn": _task_search("StarCraft", "StarCraft")},
        {"name": "search:Reinforcement learning", "fn": _task_search("Reinforcement learning", "Reinforcement")},
        {"name": "search:Poincare disk model", "fn": _task_search("Poincare disk model", "Poincar")},
        {"name": "multihop:StarCraft->Warcraft", "fn": _task_multihop},
        {"name": "extract:lead paragraph", "fn": _task_extract},
        {"name": "camera:scroll to bottom", "fn": _task_scroll_camera},
        {"name": "honesty:nonexistent target fails", "fn": _task_honest_fail},
    ]


def run_bench(br: AIBrowser) -> Dict[str, Any]:
    results = []
    for t in tasks():
        try:
            ok, detail = t["fn"](br)
        except Exception as exc:
            ok, detail = False, "%s: %s" % (type(exc).__name__, str(exc)[:60])
        results.append({"task": t["name"], "passed": bool(ok), "detail": detail})
    passed = sum(1 for r in results if r["passed"])
    return {"passed": passed, "total": len(results), "results": results}


def gather_summaries(br: AIBrowser, topics: List[str]) -> List[Dict[str, str]]:
    """REAL WORK: drive the browser to collect each topic's Wikipedia lead paragraph + url."""
    out = []
    for topic in topics:
        drv = AutoDriver(br, br.open(WIKI))
        res = drv.run([fill("search", topic), submit(), assert_url(_alnum(topic.split()[0]))])
        lead = _lead_paragraph(drv.page) if res["success"] else ""
        out.append({"topic": topic, "url": res["final_url"], "summary": lead})
    return out
