"""browser_grid: the real-time AI-ingestion VIEWER -- a per-site coordinate grid over the page.

Issac's design: screenshot the site, grid it out, and give every button a sudoku-style coordinate (the
login button is `C4`), so the model's VISION lines up with the data feed -- it can reason spatially and
still resolve back to a concrete element. Two halves, both built on ai_browser's feed (which now carries
each element's on-screen box):

  * grid_map(feed): DATA, fast. Lays an R x C coordinate grid over the viewport and assigns every element
    to its cell by box-center. Returns by_ref {r5: 'C4'}, by_cell {'C4': ['r5']}, and a legend
    {'C4': ['Log in']}. Per-site: the grid adapts to wherever the buttons actually are.
  * render_grid(browser, page): PIXELS, behind the data. Injects an SVG overlay (grid lines + cell labels
    + highlighted occupied cells) INTO the page, screenshots it, then removes the overlay -- a gridded
    screenshot the AI can look at, aligned cell-for-cell with grid_map.

So `C4` means the same thing in the data feed and in the picture. The grid is the bridge between the
structured surface (refs/moves) and vision (pixels).

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.browser_grid import grid_map, render_grid
    with AIBrowser(headless=True) as br:
        page = br.open(url)
        g = grid_map(br.read(page))                 # data: which cell each button is in
        shot = render_grid(br, page, "grid.png")     # pixels: the gridded screenshot (behind the data)
"""

from __future__ import annotations

from typing import Any, Dict, List

_DEFAULT_VP = {"w": 1280, "h": 800}


def cell_label(col: int, row: int) -> str:
    """Spreadsheet/sudoku coordinate: column letters (A, B, ... Z, AA, ...) + 1-based row number."""
    s, c = "", col
    while True:
        s = chr(65 + c % 26) + s
        c = c // 26 - 1
        if c < 0:
            break
    return "%s%d" % (s, row + 1)


def _cell_of(e: Dict[str, Any], vw: int, vh: int, cols: int, rows: int):
    cx = e.get("x", 0) + e.get("w", 0) / 2.0
    cy = e.get("y", 0) + e.get("h", 0) / 2.0
    if cx < 0 or cy < 0 or cx > vw or cy > vh:
        return None  # off the current viewport (scrolled out of view)
    col = min(cols - 1, max(0, int(cx / vw * cols)))
    row = min(rows - 1, max(0, int(cy / vh * rows)))
    return col, row


def grid_map(feed: Dict[str, Any], cols: int = 9, rows: int = 9) -> Dict[str, Any]:
    """Lay a cols x rows coordinate grid over the viewport; assign every element to a cell by its box
    center. DATA-first: derived from the feed, no screenshot needed. Elements scrolled off-screen map to
    'off'."""
    vp = feed.get("viewport") or _DEFAULT_VP
    vw, vh = max(1, int(vp.get("w", 1280))), max(1, int(vp.get("h", 800)))
    by_ref: Dict[str, str] = {}
    by_cell: Dict[str, List[str]] = {}
    legend: Dict[str, List[str]] = {}
    for e in feed.get("elements", []):
        rc = _cell_of(e, vw, vh, cols, rows)
        cell = "off" if rc is None else cell_label(rc[0], rc[1])
        by_ref[e["ref"]] = cell
        by_cell.setdefault(cell, []).append(e["ref"])
        legend.setdefault(cell, []).append(e.get("name") or e.get("tag", ""))
    return {
        "cols": cols,
        "rows": rows,
        "viewport": {"w": vw, "h": vh},
        "by_ref": by_ref,
        "by_cell": by_cell,
        "legend": legend,
    }


# SVG overlay drawn INTO the page just before the screenshot, then removed. Pixels behind the data.
_OVERLAY_JS = r"""
(cfg) => {
  const { cols, rows, vw, vh, occ } = cfg;
  const NS = 'http://www.w3.org/2000/svg';
  const old = document.getElementById('aibgrid'); if (old) old.remove();
  const svg = document.createElementNS(NS, 'svg');
  svg.id = 'aibgrid';
  svg.setAttribute('width', vw); svg.setAttribute('height', vh);
  svg.setAttribute('viewBox', '0 0 ' + vw + ' ' + vh);
  svg.setAttribute('style',
    'position:fixed;left:0;top:0;width:' + vw + 'px;height:' + vh + 'px;z-index:2147483647;pointer-events:none;');
  const cw = vw / cols, ch = vh / rows;
  const LINE = 'rgba(220,0,0,0.35)';
  const mk = (n, a) => {
    const el = document.createElementNS(NS, n);
    for (const k in a) el.setAttribute(k, a[k]);
    return el;
  };
  occ.forEach(o => svg.appendChild(mk('rect', {
    x: o.col * cw, y: o.row * ch, width: cw, height: ch,
    fill: 'rgba(0,170,255,0.22)', stroke: 'rgba(0,120,255,0.9)'
  })));
  for (let i = 0; i <= cols; i++) {
    svg.appendChild(mk('line', { x1: i * cw, y1: 0, x2: i * cw, y2: vh, stroke: LINE }));
  }
  for (let j = 0; j <= rows; j++) {
    svg.appendChild(mk('line', { x1: 0, y1: j * ch, x2: vw, y2: j * ch, stroke: LINE }));
  }
  for (let c = 0; c < cols; c++) for (let r = 0; r < rows; r++) {
    const t = mk('text', {
      x: c * cw + 2, y: r * ch + 12, 'font-size': 10,
      fill: 'rgba(220,0,0,0.65)', 'font-family': 'monospace'
    });
    t.textContent = String.fromCharCode(65 + c) + (r + 1);
    svg.appendChild(t);
  }
  document.body.appendChild(svg);
  return true;
}
"""


def render_grid(browser, page, path: str, cols: int = 9, rows: int = 9) -> Dict[str, Any]:
    """Inject the grid overlay, screenshot it (the gridded vision), then remove the overlay. Returns the
    screenshot path + the grid_map so cell labels match the picture exactly. PIXELS behind the data."""
    feed = browser.read(page)
    g = grid_map(feed, cols=cols, rows=rows)
    vw, vh = g["viewport"]["w"], g["viewport"]["h"]
    occ = []
    for e in feed.get("elements", []):
        rc = _cell_of(e, vw, vh, cols, rows)
        if rc is not None:
            occ.append({"col": rc[0], "row": rc[1]})
    page.evaluate(_OVERLAY_JS, {"cols": cols, "rows": rows, "vw": vw, "vh": vh, "occ": occ})
    browser.snapshot(page, path)
    page.evaluate("() => { const e = document.getElementById('aibgrid'); if (e) e.remove(); }")
    return {"path": path, "grid": g, "occupied_cells": sorted(c for c in g["by_cell"] if c != "off")}
