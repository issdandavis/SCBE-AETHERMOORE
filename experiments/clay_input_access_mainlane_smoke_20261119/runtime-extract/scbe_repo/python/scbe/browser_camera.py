"""browser_camera: the DOCUMENT-level camera over a scrollable page.

browser_map fogs a single VIEWPORT. Real pages scroll -- the document is bigger than the camera -- so the
research (pysc2/AlphaStar) flagged three things this adds, in DOCUMENT coordinates:

  * PageMinimap -- a grid over the WHOLE document (doc coords = element viewport coords + scroll), with the
    current viewport drawn as a RECTANGLE. The persistent overview of the entire page, not just on-screen.
  * ThreeStateFog -- pysc2's HIDDEN / SEEN / VISIBLE. VISIBLE = in the viewport now; SEEN = scrolled past
    (a last-seen snapshot is kept, possibly stale); HIDDEN = never scrolled into view.
  * Camera.move_camera(target) -- scroll a doc-cell or element into view (the costed camera action). To act
    on an OFF-SCREEN element you must move_camera to it first; off-screen, that is the only legal move
    toward it -- exactly SC2's "actions are restricted to the viewable region."

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_camera import Camera
    with AIBrowser(headless=True) as br:
        cam = Camera(br, br.open(url))
        obs = cam.observe()                 # doc minimap + viewport rect + fog + legal actions
        cam.move_camera("D9")               # scroll that doc-cell into view -> it becomes VISIBLE
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .ai_browser import AIBrowser, Move
from .browser_grid import cell_label

HIDDEN, SEEN, VISIBLE = 0, 1, 2
_STATE_NAME = {HIDDEN: "hidden", SEEN: "seen", VISIBLE: "visible"}


class ThreeStateFog:
    """pysc2 visibility: HIDDEN (never seen) / SEEN (explored, stale snapshot kept) / VISIBLE (live)."""

    def __init__(self) -> None:
        self.state: Dict[str, int] = {}
        self.snapshot: Dict[str, Any] = {}

    def update(self, visible: Set[str], cell_data: Dict[str, Any]) -> None:
        for cell, st in list(self.state.items()):
            if st == VISIBLE and cell not in visible:
                self.state[cell] = SEEN  # scrolled out of view -> remembered but now stale
        for cell in visible:
            self.state[cell] = VISIBLE
            self.snapshot[cell] = cell_data.get(cell)  # refresh the last-seen snapshot

    def of(self, cell: str) -> int:
        return self.state.get(cell, HIDDEN)

    def name(self, cell: str) -> str:
        return _STATE_NAME[self.of(cell)]

    def seen_snapshot(self, cell: str) -> Any:
        """The last-seen data for a SEEN (stale) cell -- remembered, not currently confirmed."""
        return self.snapshot.get(cell)

    def counts(self) -> Dict[str, int]:
        out = {"hidden": 0, "seen": 0, "visible": 0}
        for st in self.state.values():
            out[_STATE_NAME[st]] += 1
        return out


class PageMinimap:
    """A grid over the WHOLE document; elements placed by doc coords; the viewport is a rectangle of cells."""

    def __init__(self, feed: Dict[str, Any], cols: int = 12, rows: int = 12):
        doc = feed.get("document") or feed.get("viewport") or {"w": 1280, "h": 800}
        self.dw, self.dh = max(1, int(doc.get("w", 1280))), max(1, int(doc.get("h", 800)))
        self.cols, self.rows = cols, rows
        self.cw, self.ch = self.dw / cols, self.dh / rows
        sc = feed.get("scroll") or {"x": 0, "y": 0}
        self.sx, self.sy = int(sc.get("x", 0)), int(sc.get("y", 0))
        vp = feed.get("viewport") or {"w": 1280, "h": 800}
        self.vw, self.vh = int(vp.get("w", 1280)), int(vp.get("h", 800))
        self.by_cell: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for e in feed.get("elements", []):
            dx = e.get("x", 0) + self.sx + e.get("w", 0) / 2.0
            dy = e.get("y", 0) + self.sy + e.get("h", 0) / 2.0
            cell = (min(cols - 1, max(0, int(dx / self.dw * cols))), min(rows - 1, max(0, int(dy / self.dh * rows))))
            self.by_cell.setdefault(cell, []).append(e)

    def label(self, cell: Tuple[int, int]) -> str:
        return cell_label(cell[0], cell[1])

    def viewport_cells(self) -> Set[Tuple[int, int]]:
        c0 = max(0, int(self.sx / self.dw * self.cols))
        r0 = max(0, int(self.sy / self.dh * self.rows))
        c1 = min(self.cols - 1, int((self.sx + self.vw) / self.dw * self.cols))
        r1 = min(self.rows - 1, int((self.sy + self.vh) / self.dh * self.rows))
        return {(c, r) for c in range(c0, c1 + 1) for r in range(r0, r1 + 1)}

    def overview(self, fog: ThreeStateFog) -> Dict[str, Any]:
        cells = {}
        for cell, els in self.by_cell.items():
            lab = self.label(cell)
            cells[lab] = {"n": len(els), "fog": fog.name(lab)}
        return {"cols": self.cols, "rows": self.rows, "doc": {"w": self.dw, "h": self.dh}, "cells": cells}


class Camera:
    """The document-level camera: a doc minimap + 3-state fog + move_camera, over a scrollable page."""

    def __init__(self, browser: AIBrowser, page: Any, cols: int = 12, rows: int = 12):
        self.br, self.page, self.cols, self.rows = browser, page, cols, rows
        self.fog = ThreeStateFog()
        self.refresh()

    def refresh(self) -> Dict[str, Any]:
        self.feed = self.br.read(self.page)
        self.minimap = PageMinimap(self.feed, self.cols, self.rows)
        vis = {self.minimap.label(c) for c in self.minimap.viewport_cells()}
        cell_data = {self.minimap.label(c): [e["ref"] for e in els] for c, els in self.minimap.by_cell.items()}
        self.fog.update(vis, cell_data)
        return self.observe()

    def _cell_of_ref(self, ref: str) -> Optional[Tuple[int, int]]:
        for cell, els in self.minimap.by_cell.items():
            if any(e["ref"] == ref for e in els):
                return cell
        return None

    def in_viewport(self, ref: str) -> bool:
        cell = self._cell_of_ref(ref)
        return cell is not None and cell in self.minimap.viewport_cells()

    def available_actions(self) -> List[str]:
        """In-viewport elements can be acted on directly; OFF-screen occupied cells offer only move_camera
        (you must scroll a target into view before acting on it -- SC2's viewable-region restriction)."""
        acts = ["read"]
        vp_cells = self.minimap.viewport_cells()
        for cell, els in self.minimap.by_cell.items():
            lab = self.minimap.label(cell)
            if cell in vp_cells:
                for e in els:
                    acts.append(("type:%s" if e.get("editable") else "activate:%s") % e["ref"])
            else:
                acts.append("move_camera:%s" % lab)  # off-screen -> reach it with the camera first
        return acts

    def observe(self) -> Dict[str, Any]:
        """Doc minimap (overview, fog-stated) + the viewport rectangle + 3-state fog counts + legal actions.
        Fog is counted over the OCCUPIED doc-cells (never-scrolled-to occupied cells read as hidden)."""
        occ_fog = {"hidden": 0, "seen": 0, "visible": 0}
        for cell in self.minimap.by_cell:
            occ_fog[self.fog.name(self.minimap.label(cell))] += 1
        return {
            "minimap": self.minimap.overview(self.fog),
            "viewport_rect": sorted(self.minimap.label(c) for c in self.minimap.viewport_cells()),
            "scroll": {"x": self.minimap.sx, "y": self.minimap.sy},
            "fog": occ_fog,
            "available_actions": self.available_actions(),
        }

    def move_camera(self, target: str) -> Dict[str, Any]:
        """Scroll a target into view (a doc-cell LABEL like 'D9', or an element ref like 'r5'), then refresh
        -- the target's cell transitions toward VISIBLE."""
        ref_cell = self._cell_of_ref(target)
        if ref_cell is not None:
            self.br.act(self.page, Move("move_camera", ref=target))
        else:
            cell = self._cell_from_label(target)
            if cell is None:
                raise ValueError("move_camera target %r is neither a known ref nor a doc-cell label" % target)
            x = int((cell[0] + 0.5) * self.minimap.cw - self.minimap.vw / 2)
            y = int((cell[1] + 0.5) * self.minimap.ch - self.minimap.vh / 2)
            self.br.act(self.page, Move("move_camera", value="%d,%d" % (max(0, x), max(0, y))))
        return self.refresh()

    def _cell_from_label(self, label: str) -> Optional[Tuple[int, int]]:
        for c in range(self.cols):
            for r in range(self.rows):
                if cell_label(c, r) == label:
                    return (c, r)
        return None
