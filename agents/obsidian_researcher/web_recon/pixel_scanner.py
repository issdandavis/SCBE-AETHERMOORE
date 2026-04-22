"""4x8 Minimap Viewport -- compress a SemanticSkeleton into an ANSI-coloured
text grid for quick visual triage.

Each cell in the grid is rendered as a glyph character coloured by its
Sacred Tongue assignment, giving the researcher a "thermal view" of a
page's structure at a glance.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

from typing import List

from .recon_goggles import SemanticNode, SemanticSkeleton


# ------------------------------------------------------------------
# Colour & glyph constants
# ------------------------------------------------------------------

TONGUE_ANSI = {
    "KO": "\033[38;5;196m",   # red     -- navigation
    "AV": "\033[38;5;208m",   # orange  -- media
    "RU": "\033[38;5;46m",    # green   -- text / content
    "CA": "\033[38;5;33m",    # blue    -- interactive
    "UM": "\033[38;5;129m",   # purple  -- forms
    "DR": "\033[38;5;250m",   # grey    -- metadata
}

GLYPH_MAP = {
    "heading": "H",
    "link": ">",
    "form": "[",
    "table": "#",
    "media": "~",
    "text": ".",
    "button": "*",
    "meta": "^",
}

_RESET = "\033[0m"
_EMPTY_GLYPH = " "


# ------------------------------------------------------------------
# PixelScanner
# ------------------------------------------------------------------

class PixelScanner:
    """Render a :class:`SemanticSkeleton` as a compact ANSI minimap.

    Parameters
    ----------
    rows : int
        Number of grid rows (default 4).
    cols : int
        Number of grid columns (default 8).
    """

    def __init__(self, rows: int = 4, cols: int = 8) -> None:
        self._rows = max(1, rows)
        self._cols = max(1, cols)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_minimap(self, skeleton: SemanticSkeleton) -> str:
        """Compress *skeleton* into a ``rows x cols`` ANSI grid string.

        Nodes are distributed across cells in document order.  Each cell
        shows the glyph of its dominant element type, coloured by the
        corresponding tongue.  The grid is bordered for readability.
        """
        cells = self._rows * self._cols
        grid = self._fill_grid(skeleton.nodes, cells)
        return self._render_grid(grid)

    def scan_region(
        self,
        skeleton: SemanticSkeleton,
        start_frac: float,
        end_frac: float,
    ) -> str:
        """Render a minimap of the *skeleton* slice between two fractions.

        Parameters
        ----------
        start_frac : float
            Start position as a fraction of total nodes (0.0 -- 1.0).
        end_frac : float
            End position as a fraction of total nodes (0.0 -- 1.0).
        """
        start_frac = max(0.0, min(1.0, start_frac))
        end_frac = max(start_frac, min(1.0, end_frac))

        n = len(skeleton.nodes)
        start_idx = int(n * start_frac)
        end_idx = int(n * end_frac)
        sliced = skeleton.nodes[start_idx:end_idx]

        cells = self._rows * self._cols
        grid = self._fill_grid(sliced, cells)
        return self._render_grid(grid)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fill_grid(
        self,
        nodes: List[SemanticNode],
        cells: int,
    ) -> List[SemanticNode | None]:
        """Distribute *nodes* across *cells*, picking one representative per cell."""
        grid: List[SemanticNode | None] = [None] * cells

        if not nodes:
            return grid

        n = len(nodes)
        for i in range(cells):
            # Map cell index to a node index (even distribution)
            node_idx = int(i * n / cells)
            if node_idx < n:
                grid[i] = nodes[node_idx]

        return grid

    def _render_grid(self, grid: List[SemanticNode | None]) -> str:
        """Convert a flat grid list into a bordered ANSI string."""
        lines: List[str] = []

        # Top border
        border_top = "+" + "-" * (self._cols * 2 + 1) + "+"
        lines.append(border_top)

        for row in range(self._rows):
            row_chars: List[str] = []
            for col in range(self._cols):
                idx = row * self._cols + col
                node = grid[idx] if idx < len(grid) else None

                if node is None:
                    row_chars.append(f" {_EMPTY_GLYPH}")
                else:
                    glyph = GLYPH_MAP.get(node.element_type, "?")
                    colour = TONGUE_ANSI.get(node.tongue, "")
                    row_chars.append(f" {colour}{glyph}{_RESET}")

            lines.append("|" + "".join(row_chars) + " |")

        # Bottom border
        lines.append(border_top)

        # Legend
        lines.append(self._render_legend())

        return "\n".join(lines)

    @staticmethod
    def _render_legend() -> str:
        """Return a one-line tongue colour legend."""
        parts: List[str] = []
        tongue_labels = {
            "KO": "nav", "AV": "media", "RU": "text",
            "CA": "interact", "UM": "form", "DR": "meta",
        }
        for tongue, label in tongue_labels.items():
            colour = TONGUE_ANSI.get(tongue, "")
            parts.append(f"{colour}{tongue}{_RESET}={label}")
        return "  ".join(parts)
