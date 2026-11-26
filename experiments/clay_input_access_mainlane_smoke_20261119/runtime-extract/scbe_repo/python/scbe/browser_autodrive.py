"""browser_autodrive: the autonomous on_step loop -- macro intents resolved against the live observation.

The pieces (ai_browser feed, controller, map, camera) let a model SEE and ACT; this closes the loop the
StarCraft way (BotAI.on_step + macro->micro). You give high-level INTENTS -- fill('search', 'X'),
click('Log in'), submit(), assert_url('X') -- the MACRO. Each step the driver RE-OBSERVES the live page
(refs go stale on real sites, so never trust a cached ref), RESOLVES the intent to a concrete element by
NAME (the micro), scrolls it into view first if it's off-screen (move_camera, SC2's viewable-region rule),
acts, and throttles (an action budget, like AlphaStar's APM cap). It stops on success, a missing target, or
the budget -- and returns a full trace, so every step is auditable.

This is policy-pluggable: the intent list can come from a human, a script, or a model reading observe().

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_autodrive import AutoDriver, fill, submit, assert_url
    with AIBrowser(headless=True) as br:
        drv = AutoDriver(br, br.open('https://en.wikipedia.org/wiki/Main_Page'))
        res = drv.run([fill('search', 'Hyperbolic geometry'), submit(), assert_url('Hyperbolic')])
        # res['success'], res['final_url'], res['trace'] (one entry per step)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .ai_browser import AIBrowser, Move
from .browser_camera import Camera


@dataclass
class Intent:
    """One macro step. hint = an element-name substring to resolve against the live page; text = the value
    (typed text / url / the substring to assert)."""

    kind: str  # fill | click | submit | scroll_to | goto | assert_url | assert_title
    hint: str = ""
    text: str = ""

    def __str__(self) -> str:
        a = " %r" % self.hint if self.hint else ""
        b = " <- %r" % self.text if self.text else ""
        return "%s%s%s" % (self.kind, a, b)


def fill(hint: str, text: str) -> Intent:
    return Intent("fill", hint=hint, text=text)


def click(hint: str) -> Intent:
    return Intent("click", hint=hint)


def submit() -> Intent:
    return Intent("submit")


def scroll_to(hint: str) -> Intent:
    return Intent("scroll_to", hint=hint)


def goto(url: str) -> Intent:
    return Intent("goto", text=url)


def assert_url(substr: str) -> Intent:
    return Intent("assert_url", text=substr)


def assert_title(substr: str) -> Intent:
    return Intent("assert_title", text=substr)


@dataclass
class Step:
    intent: str
    status: str  # ok | fail
    detail: str = ""


@dataclass
class AutoDriver:
    """Autonomous macro->micro driver with re-observe-every-step + camera + an action budget."""

    browser: AIBrowser
    page: Any
    max_steps: int = 40
    settle_ms: int = 1200
    trace: List[Step] = field(default_factory=list)

    def _find(self, feed: Dict[str, Any], hint: str, editable: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        h = hint.lower()
        cands = [
            e
            for e in feed.get("elements", [])
            if h in (e.get("name", "") or "").lower() and (editable is None or bool(e.get("editable")) == editable)
        ]
        return cands[0] if cands else None

    def _settle(self) -> None:
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        self.page.wait_for_timeout(self.settle_ms)

    def _resolve_and_focus(self, hint: str, editable: Optional[bool]) -> Optional[Dict[str, Any]]:
        """Re-read, find the element by name, and move_camera it into view if it's off-screen. Returns the
        (fresh) element or None."""
        feed = self.browser.read(self.page)
        e = self._find(feed, hint, editable=editable)
        if not e:
            return None
        cam = Camera(self.browser, self.page)
        if not cam.in_viewport(e["ref"]):
            self.browser.act(self.page, Move("move_camera", ref=e["ref"]))
            feed = self.browser.read(self.page)  # refs change after a scroll/re-render
            e = self._find(feed, hint, editable=editable)
        return e

    def run(self, intents: List[Intent]) -> Dict[str, Any]:
        self.trace = []
        for intent in intents:
            if len(self.trace) >= self.max_steps:
                self.trace.append(Step(str(intent), "fail", "action budget exhausted"))
                break
            try:
                ok, detail = self._step(intent)
            except Exception as exc:
                ok, detail = False, "%s: %s" % (type(exc).__name__, str(exc)[:80])
            self.trace.append(Step(str(intent), "ok" if ok else "fail", detail))
            if not ok:
                break
        final = self.browser.read(self.page)
        return {
            "success": bool(self.trace) and all(s.status == "ok" for s in self.trace),
            "steps": len(self.trace),
            "final_url": final.get("url"),
            "final_title": final.get("title"),
            "trace": [{"intent": s.intent, "status": s.status, "detail": s.detail} for s in self.trace],
        }

    def _step(self, intent: Intent):
        if intent.kind in ("fill", "click", "scroll_to"):
            e = self._resolve_and_focus(intent.hint, editable=(True if intent.kind == "fill" else None))
            if not e:
                return False, "no element matching %r" % intent.hint
            if intent.kind == "fill":
                self.browser.act(self.page, Move("type", ref=e["ref"], value=intent.text))
            elif intent.kind == "click":
                self.browser.act(self.page, Move("click", ref=e["ref"]))
                self._settle()
            else:  # scroll_to
                self.browser.act(self.page, Move("move_camera", ref=e["ref"]))
            return True, e.get("name", "")
        if intent.kind == "submit":
            self.browser.act(self.page, Move("submit"))
            self._settle()
            return True, ""
        if intent.kind == "goto":
            self.browser.act(self.page, Move("navigate", value=intent.text))
            self._settle()
            return True, intent.text
        if intent.kind == "assert_url":
            url = self.browser.read(self.page).get("url", "")
            return (intent.text.lower() in url.lower()), url
        if intent.kind == "assert_title":
            title = self.browser.read(self.page).get("title", "")
            return (intent.text.lower() in title.lower()), title
        return False, "unknown intent kind %r" % intent.kind
