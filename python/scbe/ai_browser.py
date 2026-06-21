"""ai_browser: an abstraction-based, AI-steerable browser core.

The idea (Issac's): the AI should not drive a browser by raw CSS selectors. It should see each page as a
small, bounded CONTROL SURFACE -- the legal moves only, the same cube/board "legal moves = governance"
shape used elsewhere in SCBE -- and steer with abstract moves that map onto whatever the site actually is.
Three load-bearing pieces, all here and all execution-verified:

  1. DATA-FIRST FEED ("vision as data"): read(page) returns a compact, structured snapshot optimized for
     AI ingestion -- url/title, the interactive elements (each given a stable `ref`), headings, and a text
     digest -- FAST. A screenshot is a SEPARATE, slower call (`snapshot`) that loads "behind" the data, so
     the model can act on structure immediately and reconcile pixels later.

  2. MOVE ABSTRACTION (the control surface): moves(feed) turns the feed into a bounded list of Moves
     (click/type/scroll/navigate/back/read). The model picks a move by `ref`, never a selector; act(page,
     move) resolves it. A page with 3 buttons is a 3-face surface, not an open DOM -- legal moves only.

  3. EPHEMERAL LOCAL DATA: a feed can be parked to a local buffer and `consume()`d exactly once -- reading
     it deletes the on-disk copy, so nothing over-caches. Vision data lives only until the AI ingests it.

Headed or headless, launch-its-own (channel='chrome', isolated profile -- never touches your real browser)
or attach to an existing debug Chrome over CDP. No raw-selector surface leaks to the caller.

    from python.scbe.ai_browser import AIBrowser
    with AIBrowser(headless=True) as br:
        page = br.open("https://example.org")
        feed = br.read(page)            # data first
        for mv in br.moves(feed): ...   # the legal control surface
        br.act(page, mv)                # steer by ref
        br.snapshot(page, "shot.png")   # pixels load behind the data
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# JS that assigns each interactive element a stable ref and returns the AI-ingestion feed. Kept as one
# evaluate() so the snapshot is atomic and fast (data-first). Refs are written back onto the DOM as
# data-aibref so act() can resolve a move without the caller ever seeing a CSS selector.
_READ_JS = r"""
() => {
  const vis = (e) => {
    const r = e.getBoundingClientRect();
    const s = window.getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const name = (e) => (
    e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.getAttribute('name') ||
    e.getAttribute('value') || (e.innerText || '').trim() || e.getAttribute('title') || ''
  ).replace(/\s+/g, ' ').slice(0, 80);
  const sel = 'a,button,input,textarea,select,[role=button],[role=link],[onclick],[contenteditable=true]';
  const els = [...document.querySelectorAll(sel)].filter(vis);
  const elements = [];
  els.forEach((e, i) => {
    const ref = 'r' + i;
    e.setAttribute('data-aibref', ref);
    const tag = e.tagName.toLowerCase();
    const typ = (e.getAttribute('type') || '').toLowerCase();
    const editable = tag === 'textarea' || tag === 'select' ||
      (tag === 'input' && !['button', 'submit', 'checkbox', 'radio', 'hidden'].includes(typ)) ||
      e.getAttribute('contenteditable') === 'true';
    elements.push({ ref, tag, role: e.getAttribute('role') || (editable ? 'input' : tag), name: name(e), editable });
  });
  const headings = [...document.querySelectorAll('h1,h2,h3')].filter(vis)
    .map(h => (h.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 12);
  const text = (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').trim().slice(0, 1200);
  return { url: location.href, title: document.title, elements, headings, text };
}
"""


@dataclass
class Move:
    """One legal move on the page's control surface. The model selects by `ref`/`kind`, never a selector."""

    kind: str  # click | type | scroll | navigate | back | read
    ref: Optional[str] = None
    label: str = ""
    value: Optional[str] = None

    def __str__(self) -> str:
        v = " <- %r" % self.value if self.value is not None else ""
        tgt = " %s" % self.ref if self.ref else ""
        return "%s%s (%s)%s" % (self.kind, tgt, self.label, v)


@dataclass
class EphemeralFeed:
    """A feed parked on disk that can be consumed exactly once. consume() returns the data and DELETES the
    local copy -- AI-ingestion data never over-caches."""

    path: str
    _spent: bool = field(default=False, repr=False)

    def consume(self) -> Dict[str, Any]:
        if self._spent:
            raise RuntimeError("ephemeral feed already consumed (and deleted)")
        data = json.loads(open(self.path, encoding="utf-8").read())
        os.remove(self.path)  # ingested -> gone; no over-cache
        self._spent = True
        return data

    @property
    def cached(self) -> bool:
        return (not self._spent) and os.path.exists(self.path)


class AIBrowser:
    """A bounded, abstraction-first browser the AI steers by moves, not selectors."""

    def __init__(self, headless: bool = True, channel: str = "chrome", cdp: Optional[str] = None):
        self.headless = headless
        self.channel = channel
        self.cdp = cdp  # e.g. "http://127.0.0.1:9222" to attach instead of launching
        self._pw = None
        self._browser = None

    def __enter__(self) -> "AIBrowser":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        if self.cdp:
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp)
        else:
            # launch our OWN isolated Chrome (fresh profile) -- never touches the user's real browser
            self._browser = self._pw.chromium.launch(headless=self.headless, channel=self.channel)
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._browser and not self.cdp:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _ctx(self):
        if self._browser.contexts:
            return self._browser.contexts[0]
        return self._browser.new_context()

    def open(self, url: str):
        page = self._ctx().new_page()
        # fail-safe dialog policy: auto-dismiss native dialogs so an alert()/beforeunload can't wedge the run
        page.on("dialog", lambda d: d.dismiss())
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        return page

    def read(self, page) -> Dict[str, Any]:
        """The AI-ingestion data feed -- structured, compact, FAST (data first; pixels come later)."""
        return page.evaluate(_READ_JS)

    def moves(self, feed: Dict[str, Any]) -> List[Move]:
        """The control surface: the bounded set of legal moves for this page (cube faces, not raw DOM)."""
        mv: List[Move] = [
            Move("read", label="re-read the page feed"),
            Move("scroll", label="scroll down"),
            Move("back", label="go back"),
        ]
        for e in feed.get("elements", []):
            if e.get("editable"):
                mv.append(Move("type", ref=e["ref"], label=e.get("name") or e["tag"], value=""))
            else:
                mv.append(Move("click", ref=e["ref"], label=e.get("name") or e["tag"]))
        return mv

    def act(self, page, move: Move) -> Dict[str, Any]:
        """Resolve an abstract move against the live page. Returns a small status dict."""
        if move.kind == "click":
            page.click("[data-aibref='%s']" % move.ref, timeout=8000)
        elif move.kind == "type":
            page.fill("[data-aibref='%s']" % move.ref, move.value or "", timeout=8000)
        elif move.kind == "scroll":
            page.mouse.wheel(0, 800)
        elif move.kind == "back":
            page.go_back(wait_until="domcontentloaded")
        elif move.kind == "navigate":
            page.goto(move.value, wait_until="domcontentloaded", timeout=45000)
        elif move.kind == "read":
            pass
        else:
            raise ValueError("unknown move kind: %s" % move.kind)
        return {"did": move.kind, "ref": move.ref}

    def park(self, feed: Dict[str, Any]) -> EphemeralFeed:
        """Write the feed to a local buffer that self-deletes on consume() (ephemeral, no over-cache)."""
        fd, path = tempfile.mkstemp(prefix="aibrowser_feed_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(feed, ensure_ascii=False))
        return EphemeralFeed(path)

    def snapshot(self, page, path: str) -> str:
        """Pixels -- the slower vision channel that loads BEHIND the data feed. Separate on purpose."""
        page.screenshot(path=path)
        return path
