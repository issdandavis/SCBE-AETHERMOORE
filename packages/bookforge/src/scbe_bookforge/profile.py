"""Book profile schema, defaults, and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


KDP_TRIM_SIZES = {
    "5x8":     (5.00, 8.00),
    "5.25x8":  (5.25, 8.00),
    "5.5x8.5": (5.50, 8.50),
    "6x9":     (6.00, 9.00),
}

KDP_HARDCOVER_TRIM_SIZES = {
    "5.5x8.5": (5.50, 8.50),
    "6x9":     (6.00, 9.00),
    "6.14x9.21": (6.14, 9.21),
}

# KDP spine-thickness multipliers (inches per page)
SPINE_PER_PAGE = {
    "bw_white":      0.002252,
    "bw_cream":      0.0025,
    "color_standard":0.002347,
    "color_premium": 0.002347,
}


@dataclass
class Profile:
    """Resolved book-build profile. All paths are absolute."""

    # Source
    source_md: Path
    output_dir: Path

    # Metadata
    title: str
    subtitle: str = ""
    author: str = ""
    edition: str = "First edition"
    copyright_year: int = 2026
    publisher: str = ""
    isbn: str = ""
    edition_statement: str = "First edition"
    creative_nonfiction_notice: str = ""
    dedication: str = ""
    epigraph_enabled: bool = False
    epigraph_text: str = ""
    epigraph_attribution: str = ""

    # Format
    binding: str = "paperback"  # paperback | hardcover
    trim_in: tuple[float, float] = (5.5, 8.5)
    paper: str = "cream"        # cream | white
    ink: str = "bw"             # bw | color_standard | color_premium
    bleed: bool = False
    cover_finish: str = "matte"
    page_count: Optional[int] = None  # required for cover wrap

    # Typography
    body_font: str = "Georgia"
    body_size_pt: float = 10.75
    leading_pt: float = 14.0
    first_line_indent_in: float = 0.22
    chapter_title_size_pt: float = 17.0
    part_title_size_pt: float = 18.0
    header_size_pt: float = 8.5

    # Margins
    top_in: float = 0.62
    bottom_in: float = 0.68
    inside_in: float = 0.75
    outside_in: float = 0.5
    hardcover_inside_bonus_in: float = 0.125  # extra inner margin for thicker binding

    # Engine preference
    interior_engine: str = "auto"  # auto | xelatex | reportlab

    # Raw profile (for callers that need anything we didn't normalize)
    raw: dict = field(default_factory=dict)

    @property
    def trim_w_in(self) -> float:
        return self.trim_in[0]

    @property
    def trim_h_in(self) -> float:
        return self.trim_in[1]

    @property
    def effective_inside_in(self) -> float:
        if self.binding == "hardcover":
            return self.inside_in + self.hardcover_inside_bonus_in
        return self.inside_in

    def spine_per_page(self) -> float:
        key = "bw_cream" if (self.ink == "bw" and self.paper == "cream") else \
              "bw_white" if (self.ink == "bw" and self.paper == "white") else \
              self.ink
        return SPINE_PER_PAGE.get(key, SPINE_PER_PAGE["bw_cream"])

    def spine_width_in(self) -> float:
        if self.page_count is None:
            raise ValueError("page_count must be set on the profile to compute spine width")
        return self.page_count * self.spine_per_page()


def _trim_from_value(value: Any) -> tuple[float, float]:
    if isinstance(value, dict):
        return float(value["width_in"]), float(value["height_in"])
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    if isinstance(value, str):
        key = value.strip().lower().replace(" ", "")
        if key in KDP_TRIM_SIZES:
            return KDP_TRIM_SIZES[key]
        if key in KDP_HARDCOVER_TRIM_SIZES:
            return KDP_HARDCOVER_TRIM_SIZES[key]
    raise ValueError(f"unrecognized trim value: {value!r}")


def load_profile(path: Path, *, base_dir: Optional[Path] = None) -> Profile:
    """Load a JSON profile and return a normalized Profile."""
    path = Path(path).resolve()
    base = (base_dir or path.parent).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))

    source_md = (base / raw["source"]).resolve()
    output_dir = (base / raw.get("output_dir", "build")).resolve()

    trim = _trim_from_value(raw.get("trim", "5.5x8.5"))
    typography = raw.get("typography", {})
    margins = raw.get("margins", {})
    epigraph = raw.get("epigraph") or {}
    print_block = raw.get("print", {})

    return Profile(
        source_md=source_md,
        output_dir=output_dir,
        title=raw["title"],
        subtitle=raw.get("subtitle", ""),
        author=raw.get("author", ""),
        edition=raw.get("edition", "First edition"),
        copyright_year=int(raw.get("copyright_year", 2026)),
        publisher=raw.get("publisher", raw.get("author", "")),
        isbn=raw.get("isbn", ""),
        edition_statement=raw.get("edition_statement", "First edition"),
        creative_nonfiction_notice=raw.get("creative_nonfiction_notice", ""),
        dedication=raw.get("dedication", ""),
        epigraph_enabled=bool(epigraph.get("enabled")),
        epigraph_text=str(epigraph.get("text", "")),
        epigraph_attribution=str(epigraph.get("attribution", "")),
        binding=raw.get("binding", "paperback"),
        trim_in=trim,
        paper=print_block.get("paper", raw.get("paper", "cream")),
        ink=_normalize_ink(print_block.get("ink", raw.get("ink", "bw"))),
        bleed=bool(print_block.get("bleed_in", 0) or print_block.get("bleed", False)),
        cover_finish=print_block.get("cover_finish", "matte"),
        page_count=raw.get("page_count"),
        body_font=typography.get("body_font", "Georgia"),
        body_size_pt=float(typography.get("body_size_pt", 10.75)),
        leading_pt=float(typography.get("leading_pt", 14.0)),
        first_line_indent_in=float(typography.get("first_line_indent_in", 0.22)),
        chapter_title_size_pt=float(typography.get("chapter_title_size_pt", 17.0)),
        part_title_size_pt=float(typography.get("part_title_size_pt", 18.0)),
        header_size_pt=float(typography.get("header_size_pt", 8.5)),
        top_in=float(margins.get("top_in", 0.62)),
        bottom_in=float(margins.get("bottom_in", 0.68)),
        inside_in=float(margins.get("inside_in", 0.75)),
        outside_in=float(margins.get("outside_in", 0.5)),
        hardcover_inside_bonus_in=float(margins.get("hardcover_inside_bonus_in", 0.125)),
        interior_engine=str(raw.get("interior_engine", "auto")).lower(),
        raw=raw,
    )


def _normalize_ink(value: str) -> str:
    v = (value or "").strip().lower().replace(" ", "_")
    if v in {"bw", "black", "black_and_white", "black_white", "b&w", "b_w"}:
        return "bw"
    if v in {"color", "color_standard", "standard_color"}:
        return "color_standard"
    if v in {"premium_color", "color_premium"}:
        return "color_premium"
    return v or "bw"
