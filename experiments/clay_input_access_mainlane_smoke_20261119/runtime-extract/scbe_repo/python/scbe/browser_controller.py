"""browser_controller: a fixed-geometry CONTROLLER over the ai_browser control surface.

ai_browser.moves() gives a page-shaped LIST of legal moves -- it changes length and order with every site,
which is exactly the unstable "movement dynamics" that makes a browser hard to steer. This wraps it in a
CONTROLLER: a small, FIXED set of buttons plus a cursor that walks the page's interactive elements. The
button vocabulary never changes -- a 3-button page and a 50-button page are both driven with the same
prev/next/activate/type/scroll/back/read/navigate. One stable steering surface for any website.

The geometry is pluggable -- the same nine logical buttons skin onto a gamepad, a Rubik's CUBE (face
turns), a SPHERE (directions), or a steering WHEEL. So "map a site to a cube / sphere / controller / wheel"
is just `layout=`; the driving logic is identical underneath.

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_controller import BrowserController
    with AIBrowser(headless=True) as br:
        ctl = BrowserController(br, br.open(url), layout='cube')
        ctl.press('next'); ctl.press('type', 'hello'); ctl.press('prev'); ctl.press('activate')
        print(ctl.frame())   # the AI's stable view: focused element + button legend + feed digest
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ai_browser import AIBrowser, Move

# the canonical logical buttons -- the steering vocabulary, identical for every page
BUTTONS: List[str] = [
    "prev",  # move the cursor to the previous interactive element
    "next",  # move the cursor to the next interactive element
    "activate",  # click / activate the focused element
    "type",  # type a value into the focused editable element
    "scroll_up",
    "scroll_down",
    "back",  # browser back
    "read",  # re-read the page feed (refresh the surface)
    "navigate",  # go to a url (value)
]

# pluggable geometries: each maps the nine logical buttons onto a control-surface skin. The driving logic
# is identical; only the rendering/identity of each button changes. This is the cube/sphere/wheel mapping.
LAYOUTS: Dict[str, Dict[str, str]] = {
    "gamepad": {
        "prev": "DPAD_UP",
        "next": "DPAD_DOWN",
        "activate": "A",
        "type": "X",
        "scroll_up": "LT",
        "scroll_down": "RT",
        "back": "B",
        "read": "Y",
        "navigate": "START",
    },
    "cube": {  # Rubik's face turns -- each button is a stable face move
        "prev": "U",
        "next": "U'",
        "activate": "F",
        "type": "R",
        "scroll_up": "L",
        "scroll_down": "L'",
        "back": "F'",
        "read": "D",
        "navigate": "R'",
    },
    "sphere": {
        "prev": "north",
        "next": "south",
        "activate": "tap",
        "type": "equator",
        "scroll_up": "zenith",
        "scroll_down": "nadir",
        "back": "west",
        "read": "east",
        "navigate": "pole",
    },
    "wheel": {
        "prev": "turn_left",
        "next": "turn_right",
        "activate": "accelerate",
        "type": "signal",
        "scroll_up": "lean_back",
        "scroll_down": "lean_forward",
        "back": "brake",
        "read": "mirror",
        "navigate": "gps",
    },
}


class BrowserController:
    """One stable steering surface for any website: a cursor over the page's elements + fixed buttons."""

    def __init__(self, browser: AIBrowser, page: Any, layout: str = "gamepad"):
        if layout not in LAYOUTS:
            raise ValueError("unknown layout %r (have %s)" % (layout, ", ".join(LAYOUTS)))
        self.br = browser
        self.page = page
        self.layout = layout
        self.cursor = 0
        self.feed = self.br.read(page)

    @property
    def elements(self) -> List[Dict[str, Any]]:
        return self.feed.get("elements", [])

    def focused(self) -> Optional[Dict[str, Any]]:
        els = self.elements
        return els[self.cursor] if els else None

    def _refresh(self) -> None:
        self.feed = self.br.read(self.page)
        if self.cursor >= len(self.elements):
            self.cursor = 0

    def press(self, button: str, value: Optional[str] = None) -> Dict[str, Any]:
        """Issue one controller input. Returns the new controller frame (stable view for the next decision)."""
        if button not in BUTTONS:
            raise ValueError("unknown button %r (have %s)" % (button, ", ".join(BUTTONS)))
        n = len(self.elements)
        if button == "prev":
            self.cursor = (self.cursor - 1) % n if n else 0
        elif button == "next":
            self.cursor = (self.cursor + 1) % n if n else 0
        elif button == "activate":
            f = self.focused()
            if f:
                self.br.act(self.page, Move("click", ref=f["ref"], label=f.get("name", "")))
                self._refresh()
        elif button == "type":
            f = self.focused()
            if f and f.get("editable"):
                self.br.act(self.page, Move("type", ref=f["ref"], value=value or "", label=f.get("name", "")))
                self._refresh()
            else:
                return {**self.frame(), "rejected": "focused element is not editable"}
        elif button == "scroll_down":
            self.br.act(self.page, Move("scroll", value="800"))
        elif button == "scroll_up":
            self.br.act(self.page, Move("scroll", value="-800"))
        elif button == "back":
            self.br.act(self.page, Move("back"))
            self._refresh()
        elif button == "read":
            self._refresh()
        elif button == "navigate":
            self.br.act(self.page, Move("navigate", value=value))
            self._refresh()
        return self.frame()

    def button_map(self) -> Dict[str, str]:
        """The current geometry's label for each logical button (the cube/wheel/gamepad skin)."""
        return dict(LAYOUTS[self.layout])

    def frame(self) -> Dict[str, Any]:
        """The AI's stable per-step view: where the cursor is, what's focused, the button legend, a digest.
        Fixed shape regardless of the site -- this is what replaces the variable raw-move list."""
        f = self.focused()
        return {
            "layout": self.layout,
            "url": self.feed.get("url"),
            "title": self.feed.get("title"),
            "cursor": self.cursor,
            "n_elements": len(self.elements),
            "focused": ("%s:%s" % (f["ref"], f.get("name", "")) if f else None),
            "focused_editable": bool(f and f.get("editable")),
            "buttons": self.button_map(),
            "headings": self.feed.get("headings", [])[:5],
        }
