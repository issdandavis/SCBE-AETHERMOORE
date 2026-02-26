"""Semantic Page Vision -- classify HTML elements into Sacred Tongue categories.

Uses regex-based HTML parsing (no lxml or BeautifulSoup) to build a
:class:`SemanticSkeleton` that maps every significant element to one of the
six Sacred Tongues:

    KO = navigation    AV = media    RU = text
    CA = interactive   UM = forms    DR = metadata

The skeleton enables downstream analysis (minimap rendering, change
detection, archetype classification) without retaining raw HTML.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class SemanticNode:
    """A single classified element from the page."""

    tongue: str          # KO, AV, RU, CA, UM, DR
    element_type: str    # heading, link, media, form, table, text, button, meta
    text_preview: str    # first 80 characters of text content
    depth: int           # nesting level (approximate)


@dataclass
class SemanticSkeleton:
    """Reduced semantic representation of an entire page."""

    nodes: List[SemanticNode] = field(default_factory=list)
    tongue_counts: Dict[str, int] = field(default_factory=dict)
    headings: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    forms: int = 0
    tables: int = 0
    media: int = 0
    structure_hash: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tongue_distribution(self) -> Dict[str, float]:
        """Return tongue percentages (0-1)."""
        total = sum(self.tongue_counts.values())
        if total == 0:
            return {t: 0.0 for t in ("KO", "AV", "RU", "CA", "UM", "DR")}
        return {t: self.tongue_counts.get(t, 0) / total for t in ("KO", "AV", "RU", "CA", "UM", "DR")}

    @property
    def page_archetype(self) -> str:
        """Classify the page into a high-level archetype.

        Returns one of: navigation, media, content, interactive, form,
        structured.
        """
        dist = self.tongue_distribution
        dominant = max(dist, key=dist.get)  # type: ignore[arg-type]
        archetype_map = {
            "KO": "navigation",
            "AV": "media",
            "RU": "content",
            "CA": "interactive",
            "UM": "form",
            "DR": "structured",
        }
        return archetype_map.get(dominant, "content")

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def diff(self, other: "SemanticSkeleton") -> Dict[str, Any]:
        """Compare this skeleton to *other* and return a change summary."""
        changes: Dict[str, Any] = {}

        if self.structure_hash != other.structure_hash:
            changes["structure_changed"] = True

        # Tongue count deltas
        tongue_deltas: Dict[str, int] = {}
        all_tongues = set(self.tongue_counts) | set(other.tongue_counts)
        for t in all_tongues:
            delta = other.tongue_counts.get(t, 0) - self.tongue_counts.get(t, 0)
            if delta != 0:
                tongue_deltas[t] = delta
        if tongue_deltas:
            changes["tongue_deltas"] = tongue_deltas

        # Heading changes
        added_headings = [h for h in other.headings if h not in self.headings]
        removed_headings = [h for h in self.headings if h not in other.headings]
        if added_headings:
            changes["added_headings"] = added_headings
        if removed_headings:
            changes["removed_headings"] = removed_headings

        # Link changes
        added_links = [lk for lk in other.links if lk not in self.links]
        removed_links = [lk for lk in self.links if lk not in other.links]
        if added_links:
            changes["added_links"] = added_links
        if removed_links:
            changes["removed_links"] = removed_links

        # Scalar changes
        if self.forms != other.forms:
            changes["forms_delta"] = other.forms - self.forms
        if self.tables != other.tables:
            changes["tables_delta"] = other.tables - self.tables
        if self.media != other.media:
            changes["media_delta"] = other.media - self.media

        return changes


# ------------------------------------------------------------------
# Tongue mapping
# ------------------------------------------------------------------

# Element tag -> tongue assignment
_TONGUE_MAP: Dict[str, str] = {
    # KO -- navigation
    "nav": "KO", "a": "KO", "menu": "KO",
    # AV -- media
    "img": "AV", "video": "AV", "audio": "AV", "svg": "AV",
    "picture": "AV", "canvas": "AV",
    # RU -- text / content
    "p": "RU", "article": "RU", "section": "RU", "blockquote": "RU",
    "span": "RU", "div": "RU", "li": "RU", "dd": "RU", "dt": "RU",
    # CA -- interactive
    "button": "CA", "select": "CA", "details": "CA", "dialog": "CA",
    # UM -- forms
    "form": "UM", "input": "UM", "textarea": "UM", "label": "UM",
    "fieldset": "UM",
    # DR -- metadata / structural
    "meta": "DR", "head": "DR", "script": "DR", "style": "DR",
    "link": "DR", "title": "DR", "base": "DR",
}

# Tag -> semantic element_type
_ELEMENT_TYPE_MAP: Dict[str, str] = {
    "h1": "heading", "h2": "heading", "h3": "heading",
    "h4": "heading", "h5": "heading", "h6": "heading",
    "a": "link", "nav": "link", "menu": "link",
    "img": "media", "video": "media", "audio": "media",
    "svg": "media", "picture": "media", "canvas": "media",
    "form": "form", "input": "form", "textarea": "form",
    "label": "form", "fieldset": "form",
    "table": "table", "thead": "table", "tbody": "table",
    "button": "button", "select": "button",
    "details": "button", "dialog": "button",
    "meta": "meta", "head": "meta", "script": "meta",
    "style": "meta", "link": "meta", "title": "meta", "base": "meta",
}

# ------------------------------------------------------------------
# Regex patterns for HTML extraction
# ------------------------------------------------------------------

_TAG_RE = re.compile(
    r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>",
    re.DOTALL,
)
_HEADING_RE = re.compile(
    r"<h([1-6])[^>]*>(.*?)</h\1>",
    re.IGNORECASE | re.DOTALL,
)
_LINK_RE = re.compile(
    r'<a\s[^>]*href\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_FORM_RE = re.compile(r"<form\b", re.IGNORECASE)
_TABLE_RE = re.compile(r"<table\b", re.IGNORECASE)
_MEDIA_RE = re.compile(
    r"<(?:img|video|audio|svg|picture|canvas)\b",
    re.IGNORECASE,
)
_INPUT_BUTTON_RE = re.compile(
    r'<input\s[^>]*type\s*=\s*["\'](?:button|submit|reset)["\']',
    re.IGNORECASE,
)
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")


def _strip_tags(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return _STRIP_TAGS_RE.sub(" ", html).strip()


# ------------------------------------------------------------------
# ReconGoggles
# ------------------------------------------------------------------

class ReconGoggles:
    """Analyse raw HTML and produce a :class:`SemanticSkeleton`.

    Uses regex-based extraction -- intentionally avoids lxml / BS4.
    """

    TONGUE_MAP = _TONGUE_MAP

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, html: str, url: str = "") -> SemanticSkeleton:
        """Parse *html* and return a classified :class:`SemanticSkeleton`."""
        skeleton = SemanticSkeleton()
        tongue_counts: Dict[str, int] = {t: 0 for t in ("KO", "AV", "RU", "CA", "UM", "DR")}

        # --- headings ---
        for m in _HEADING_RE.finditer(html):
            text = _strip_tags(m.group(2))[:80]
            if text:
                skeleton.headings.append(text)
                skeleton.nodes.append(SemanticNode(
                    tongue="RU", element_type="heading",
                    text_preview=text, depth=int(m.group(1)),
                ))
                tongue_counts["RU"] += 1

        # --- links ---
        for m in _LINK_RE.finditer(html):
            href = m.group(1).strip()
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                skeleton.links.append(href)
                skeleton.nodes.append(SemanticNode(
                    tongue="KO", element_type="link",
                    text_preview=href[:80], depth=0,
                ))
                tongue_counts["KO"] += 1

        # --- forms ---
        form_count = len(_FORM_RE.findall(html))
        skeleton.forms = form_count
        for _ in range(form_count):
            skeleton.nodes.append(SemanticNode(
                tongue="UM", element_type="form",
                text_preview="<form>", depth=0,
            ))
            tongue_counts["UM"] += 1

        # --- tables ---
        table_count = len(_TABLE_RE.findall(html))
        skeleton.tables = table_count
        for _ in range(table_count):
            skeleton.nodes.append(SemanticNode(
                tongue="RU", element_type="table",
                text_preview="<table>", depth=0,
            ))
            tongue_counts["RU"] += 1

        # --- media ---
        media_count = len(_MEDIA_RE.findall(html))
        skeleton.media = media_count
        for _ in range(media_count):
            skeleton.nodes.append(SemanticNode(
                tongue="AV", element_type="media",
                text_preview="<media>", depth=0,
            ))
            tongue_counts["AV"] += 1

        # --- buttons (input[type=button/submit/reset]) ---
        for _ in _INPUT_BUTTON_RE.finditer(html):
            skeleton.nodes.append(SemanticNode(
                tongue="CA", element_type="button",
                text_preview="<button>", depth=0,
            ))
            tongue_counts["CA"] += 1

        # --- metadata (script/style/meta tags) ---
        meta_count = len(re.findall(r"<(?:script|style|meta)\b", html, re.IGNORECASE))
        for _ in range(meta_count):
            skeleton.nodes.append(SemanticNode(
                tongue="DR", element_type="meta",
                text_preview="<meta>", depth=0,
            ))
            tongue_counts["DR"] += 1

        # --- text blocks (paragraphs) ---
        for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL):
            text = _strip_tags(m.group(1))[:80]
            if text and len(text) > 5:
                skeleton.nodes.append(SemanticNode(
                    tongue="RU", element_type="text",
                    text_preview=text, depth=0,
                ))
                tongue_counts["RU"] += 1

        skeleton.tongue_counts = tongue_counts

        # Structure hash for change detection
        type_seq = "|".join(n.element_type for n in skeleton.nodes)
        skeleton.structure_hash = hashlib.sha256(type_seq.encode()).hexdigest()[:16]

        return skeleton
