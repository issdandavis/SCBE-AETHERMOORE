"""browser_map: a StarCraft-style LAYERED map viewer over a website.

browser_grid was one flat layer of boxes. Real pages aren't perfect boxes, so this lays TWO overlapping
layers (Issac's "layers of grids / stars that brick into triangles and squares and overlap"):

  * SQUARE layer  -- the cell you ARE in. This is the IMAGE cell: the focused region, looked at as pixels.
  * DIAMOND layer -- offset by half a cell so each diamond sits on a square CORNER and reaches, with four
    triangular points, into the four squares meeting at that corner. A point therefore belongs to ONE
    square (its image) AND one diamond whose triangles "intersect with the cells next to it" -- those
    neighbors are read as TEXT. So you SEE the cell you're in and READ the triangle-reaches around it.

Over that sits a FOG OF WAR: every cell the cursor visits is revealed and STAYS revealed -- a persistent
render assembled from where the cursor has travelled, exactly like a StarCraft minimap. The MapCursor pans
cell-to-cell (separate from page scroll) and can HOVER the focused element (hover, not click).

All the geometry/fog/cursor logic is pure (operates on ai_browser's feed: element boxes + viewport), so it
verifies instantly with no browser. hover() is the one browser-backed call.

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_map import MapView
    with AIBrowser(headless=True) as br:
        page = br.open(url)
        mv = MapView(br.read(page))     # the map of the site
        look = mv.pan("E")              # move the cursor east, reveal that cell
        # look['focus'] = image cell + its elements; look['context'] = neighbor cells as text
        mv.hover(br, page)              # hover the focused element (no click, no scroll)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .ai_browser import AIBrowser, Move
from .browser_grid import cell_label

_DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


class MapTiling:
    """The two-layer geometry: square cells (image) + a half-offset diamond layer (the star/triangle reach)."""

    def __init__(self, vw: int, vh: int, cols: int = 9, rows: int = 9):
        self.vw, self.vh, self.cols, self.rows = max(1, vw), max(1, vh), cols, rows
        self.cw, self.ch = self.vw / cols, self.vh / rows

    def square(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        if x < 0 or y < 0 or x > self.vw or y > self.vh:
            return None
        return (min(self.cols - 1, int(x / self.vw * self.cols)), min(self.rows - 1, int(y / self.vh * self.rows)))

    def label(self, cell: Tuple[int, int]) -> str:
        return cell_label(cell[0], cell[1])

    def neighbors(self, cell: Tuple[int, int]) -> Dict[str, Tuple[int, int]]:
        """The four squares the diamond's triangle-points reach into (clamped to the board)."""
        out = {}
        for d, (dx, dy) in _DIRS.items():
            c, r = cell[0] + dx, cell[1] + dy
            if 0 <= c < self.cols and 0 <= r < self.rows:
                out[d] = (c, r)
        return out

    def locate(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        """A point's layered position: its square (image), the diamond corner it sits on, and which of the
        four corner-squares it falls in (the triangle quadrant). Off-viewport -> None."""
        sq = self.square(x, y)
        if sq is None:
            return None
        corner = (round(x / self.cw), round(y / self.ch))  # nearest lattice corner -> the diamond center
        quad = ("E" if x >= corner[0] * self.cw else "W") + ("S" if y >= corner[1] * self.ch else "N")
        return {"square": sq, "label": self.label(sq), "diamond": corner, "triangle": quad}


class FogOfWar:
    """Persistent reveal: cells stay seen once the cursor visits them (StarCraft minimap)."""

    def __init__(self) -> None:
        self.revealed: set = set()

    def reveal(self, cell: Tuple[int, int]) -> None:
        self.revealed.add(cell)

    def visible(self, cell: Tuple[int, int]) -> bool:
        return cell in self.revealed

    def panorama(self) -> List[str]:
        return sorted(cell_label(c, r) for (c, r) in self.revealed)


class MapView:
    """The website as a map: layered tiling + fog + a panning, hovering cursor."""

    def __init__(self, feed: Dict[str, Any], cols: int = 9, rows: int = 9, start: Optional[Tuple[int, int]] = None):
        self.feed = feed
        vp = feed.get("viewport") or {"w": 1280, "h": 800}
        self.tiling = MapTiling(int(vp.get("w", 1280)), int(vp.get("h", 800)), cols, rows)
        self.fog = FogOfWar()
        # index elements by their square cell
        self.by_cell: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for e in feed.get("elements", []):
            loc = self.tiling.locate(e.get("x", 0) + e.get("w", 0) / 2.0, e.get("y", 0) + e.get("h", 0) / 2.0)
            if loc:
                self.by_cell.setdefault(loc["square"], []).append(e)
        self.cursor: Tuple[int, int] = start or self._first_cell()
        self.fog.reveal(self.cursor)

    def _first_cell(self) -> Tuple[int, int]:
        return sorted(self.by_cell)[0] if self.by_cell else (0, 0)

    def elements_in(self, cell: Tuple[int, int]) -> List[Dict[str, Any]]:
        return self.by_cell.get(cell, [])

    def pan(self, direction: str) -> Dict[str, Any]:
        """Move the cursor one cell (N/S/E/W), reveal it (fog persists), return the hybrid view."""
        if direction not in _DIRS:
            raise ValueError("direction must be one of %s" % ", ".join(_DIRS))
        dx, dy = _DIRS[direction]
        c, r = self.cursor[0] + dx, self.cursor[1] + dy
        if 0 <= c < self.tiling.cols and 0 <= r < self.tiling.rows:
            self.cursor = (c, r)
            self.fog.reveal(self.cursor)
        return self.look()

    def look(self) -> Dict[str, Any]:
        """Hybrid view at the cursor: the focus cell as an IMAGE region + its elements; the neighbor cells
        (the triangle reaches) as TEXT; plus the fog-revealed panorama so far."""
        focus_els = self.elements_in(self.cursor)
        region = self._region(self.cursor)
        context = {}
        for d, ncell in self.tiling.neighbors(self.cursor).items():
            names = [e.get("name") or e.get("tag", "") for e in self.elements_in(ncell)]
            context[d] = {"cell": self.tiling.label(ncell), "text": names}
        return {
            "cursor": self.tiling.label(self.cursor),
            "focus": {  # the cell you are IN -- looked at as an image region
                "cell": self.tiling.label(self.cursor),
                "image_region": region,  # bbox in page px to crop for the vision channel
                "elements": [
                    {"ref": e["ref"], "name": e.get("name"), "editable": e.get("editable")} for e in focus_els
                ],
            },
            "context": context,  # the triangle-reaches into neighbors, as text
            "revealed": self.fog.panorama(),  # persistent render from where the cursor has been
        }

    def _region(self, cell: Tuple[int, int]) -> Dict[str, int]:
        col, row = cell
        return {
            "x": int(col * self.tiling.cw),
            "y": int(row * self.tiling.ch),
            "w": int(self.tiling.cw),
            "h": int(self.tiling.ch),
        }

    def minimap(self) -> Dict[str, Any]:
        """The MINIMAP channel: a low-detail whole-page overview -- per-occupied-cell counts + element
        kinds + fog state + the cursor. Sparse and cheap (the persistent overview, like SC2's minimap),
        NOT the detail. Pairs with screen() the way feature_minimap pairs with feature_screen."""
        cells = {}
        for cell, els in self.by_cell.items():
            cells[self.tiling.label(cell)] = {
                "n": len(els),
                "seen": self.fog.visible(cell),
                "kinds": sorted({(e.get("role") or e.get("tag") or "") for e in els}),
            }
        return {
            "cols": self.tiling.cols,
            "rows": self.tiling.rows,
            "cursor": self.tiling.label(self.cursor),
            "occupied": cells,
            "revealed": self.fog.panorama(),
        }

    def screen(self) -> Dict[str, Any]:
        """The SCREEN channel: the high-detail local view at the cursor -- the focus image cell + its
        elements + the neighbor triangle-reaches as text (what look() returns, named as the screen)."""
        v = self.look()
        return {"cursor": v["cursor"], "focus": v["focus"], "context": v["context"]}

    def available_actions(self) -> List[str]:
        """SC2's available_actions: the legal actions THIS frame. Only on-board pans; hover/activate/type
        only when the focus cell actually has a (editable) element. Legal-moves-only governance."""
        acts = ["read"]
        for d, (dx, dy) in _DIRS.items():
            c, r = self.cursor[0] + dx, self.cursor[1] + dy
            if 0 <= c < self.tiling.cols and 0 <= r < self.tiling.rows:
                acts.append("pan:" + d)
        els = self.elements_in(self.cursor)
        if els:
            acts += ["hover", "activate"]
            if any(e.get("editable") for e in els):
                acts.append("type")
        return acts

    def observe(self) -> Dict[str, Any]:
        """The SC2-style observation: minimap (overview) + screen (detail) + available_actions (legal now).
        One call gives the model both channels and exactly the moves it may make this frame."""
        return {
            "minimap": self.minimap(),
            "screen": self.screen(),
            "available_actions": self.available_actions(),
        }

    def hover(self, browser: AIBrowser, page: Any) -> Dict[str, Any]:
        """Hover the focused element -- hover, NOT click, and independent of scroll (StarCraft cursor)."""
        els = self.elements_in(self.cursor)
        if not els:
            return {"hovered": None, "reason": "no element in focus cell"}
        ref = els[0]["ref"]
        page.hover("[data-aibref='%s']" % ref, timeout=8000)
        return {"hovered": ref, "cell": self.tiling.label(self.cursor)}


def _activate_via_browser(browser: AIBrowser, page: Any, ref: str) -> None:
    browser.act(page, Move("click", ref=ref))
