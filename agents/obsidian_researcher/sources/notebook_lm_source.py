"""NotebookLM-style source adapter for the Obsidian researcher agent.

Ingests AI-generated analysis content -- the kind of structured output
produced by NotebookLM, Claude, Grok, or similar tools -- and converts
it into ``IngestionResult`` records for cross-referencing in the vault.

Handles five content flavours:

* **Structured analysis** -- numbered sections with markdown headings.
* **Mathematical specifications** -- LaTeX notation (``$...$``,
  ``\\frac``, ``\\sum``).
* **Conversation transcripts** -- Q&A or speaker-labelled dialogue.
* **Executive summaries** -- short, high-level briefs.
* **Podcast transcripts** -- ``Speaker N:`` formatted dialogue.

Pure-stdlib implementation.  No external dependencies.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TITLE_MAX_LEN = 80

# Section splitting: markdown headings (## or #) or numbered headers (1. 2.)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+)", re.MULTILINE)

# Format detection patterns
_TRANSCRIPT_RE = re.compile(
    r"^(?:Speaker\s*\d+|Q|A|Host|Guest|Interviewer|Interviewee)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
_MATH_RE = re.compile(r"\\[a-zA-Z]+|\\frac|\\sum|\$[^$]+\$")
_CODE_RE = re.compile(r"```|^def\s|^class\s|^import\s", re.MULTILINE)
_EXECUTIVE_KEYWORDS = re.compile(
    r"\b(?:executive\s+summary|key\s+takeaway|bottom\s+line|tldr|tl;dr|overview)\b",
    re.IGNORECASE,
)


class NotebookLMSource(SourceAdapter):
    """Ingest AI-generated analysis content (NotebookLM, Claude, Grok dumps).

    Handles:

    - Structured analysis with numbered sections
    - Mathematical specifications with LaTeX
    - Conversation transcripts (Q&A format)
    - Executive summaries and briefs
    - Podcast transcript format

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``encoding`` -- file encoding (default ``utf-8``).
        * ``default_ai_source`` -- default AI source label when none
          is provided (default ``"unknown"``).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        # Uses BRAINSTORM source type since no dedicated NOTEBOOK_LM type
        super().__init__(source_type=SourceType.BRAINSTORM, config=config or {})
        self._encoding: str = self.config.get("encoding", "utf-8")
        self._default_ai_source: str = self.config.get(
            "default_ai_source", "unknown"
        )

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Ingest *query* as raw AI analysis text.

        *query* is the full analysis text.  Returns a single-element list
        containing the structured ``IngestionResult``, or an empty list
        if the input is blank.

        Keyword arguments
        -----------------
        title : str
            Override the auto-detected title.
        ai_source : str
            Label for the originating AI (``"notebooklm"``,
            ``"claude"``, ``"grok"``, etc.).
        """
        text = query.strip()
        if not text:
            return []

        sections = self._parse_sections(text)
        title = kwargs.get("title") or self._extract_title(text)
        ai_source = kwargs.get("ai_source", self._default_ai_source)
        detected_format = self._detect_format(text)

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        return [
            IngestionResult(
                source_type=SourceType.BRAINSTORM,
                raw_content=text,
                title=title,
                authors=[],
                url=None,
                timestamp=timestamp,
                identifiers={"notebook_hash": content_hash},
                tags=["ai-analysis", f"source:{ai_source}"],
                metadata={
                    "sections": sections,
                    "ai_source": ai_source,
                    "section_count": len(sections),
                    "has_math": bool(_MATH_RE.search(text)),
                    "has_code": bool(_CODE_RE.search(text)),
                    "format": detected_format,
                    "char_count": len(text),
                    "line_count": len(text.splitlines()),
                },
                summary=text[:500],
            )
        ]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Read analysis content from a file at *identifier* (a file path).

        Returns ``None`` if the file cannot be read.
        """
        path = Path(identifier.strip())
        if not path.is_file():
            logger.warning("NotebookLM file not found: %s", path)
            return None

        try:
            text = path.read_text(encoding=self._encoding, errors="replace")
        except OSError:
            logger.exception("Could not read NotebookLM file: %s", path)
            return None

        if not text.strip():
            return None

        results = self.fetch(text, title=path.stem)
        return results[0] if results else None

    def health_check(self) -> bool:
        """Return ``True`` -- no external dependency."""
        return True

    # ------------------------------------------------------------------
    # Section parsing
    # ------------------------------------------------------------------

    def _parse_sections(self, text: str) -> List[Dict[str, str]]:
        """Split *text* into sections by markdown headings or numbered headers.

        Returns a list of dicts, each with ``"heading"`` and ``"body"``
        keys.  If no headings are found the entire text is returned as a
        single section with heading ``"(untitled)"``.
        """
        # Collect heading positions
        markers: List[tuple[int, str, int]] = []  # (pos, heading_text, level)

        for m in _HEADING_RE.finditer(text):
            level = len(m.group(1))
            markers.append((m.start(), m.group(2).strip(), level))

        # If no markdown headings, try numbered headers
        if not markers:
            for m in _NUMBERED_RE.finditer(text):
                markers.append((m.start(), m.group(2).strip(), 2))

        if not markers:
            return [{"heading": "(untitled)", "body": text.strip()}]

        # Sort by position (should already be, but be safe)
        markers.sort(key=lambda t: t[0])

        sections: List[Dict[str, str]] = []

        # Preamble before first heading
        preamble = text[: markers[0][0]].strip()
        if preamble:
            sections.append({"heading": "(preamble)", "body": preamble})

        for i, (pos, heading, _level) in enumerate(markers):
            # Body runs from end of this heading line to start of next marker
            # Find end of the heading line
            line_end = text.find("\n", pos)
            if line_end == -1:
                line_end = len(text)

            if i + 1 < len(markers):
                body = text[line_end:markers[i + 1][0]].strip()
            else:
                body = text[line_end:].strip()

            sections.append({"heading": heading, "body": body})

        return sections

    # ------------------------------------------------------------------
    # Title extraction
    # ------------------------------------------------------------------

    def _extract_title(self, text: str) -> str:
        """Get title from first markdown heading or first non-empty line.

        Falls back to ``"Untitled AI Analysis"`` if nothing suitable is
        found.
        """
        # Try first markdown heading
        m = _HEADING_RE.search(text)
        if m:
            title = m.group(2).strip()
            if len(title) <= _TITLE_MAX_LEN:
                return title
            # Truncate at word boundary
            truncated = title[:_TITLE_MAX_LEN]
            last_space = truncated.rfind(" ")
            if last_space > _TITLE_MAX_LEN // 2:
                truncated = truncated[:last_space]
            return truncated + "..."

        # Fall back to first non-empty line
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                if len(stripped) <= _TITLE_MAX_LEN:
                    return stripped
                truncated = stripped[:_TITLE_MAX_LEN]
                last_space = truncated.rfind(" ")
                if last_space > _TITLE_MAX_LEN // 2:
                    truncated = truncated[:last_space]
                return truncated + "..."

        return "Untitled AI Analysis"

    # ------------------------------------------------------------------
    # Format detection
    # ------------------------------------------------------------------

    def _detect_format(self, text: str) -> str:
        """Classify the overall format of the text.

        Returns one of:

        * ``"transcript"`` -- dialogue / Q&A / podcast format
        * ``"specification"`` -- heavy math or code content
        * ``"executive_brief"`` -- short summary with executive keywords
        * ``"analysis"`` -- structured sections with moderate length
        * ``"mixed"`` -- multiple strong signals present
        """
        signals: Dict[str, float] = {}

        # Transcript signal: speaker labels
        transcript_matches = len(_TRANSCRIPT_RE.findall(text))
        if transcript_matches >= 3:
            signals["transcript"] = 0.9
        elif transcript_matches >= 1:
            signals["transcript"] = 0.4

        # Specification signal: math + code density
        math_count = len(_MATH_RE.findall(text))
        code_count = len(_CODE_RE.findall(text))
        if math_count >= 3 or code_count >= 3:
            signals["specification"] = 0.8
        elif math_count >= 1 or code_count >= 1:
            signals["specification"] = 0.3

        # Executive brief signal: keywords + short length
        has_exec_kw = bool(_EXECUTIVE_KEYWORDS.search(text))
        is_short = len(text) < 2000
        if has_exec_kw and is_short:
            signals["executive_brief"] = 0.9
        elif has_exec_kw:
            signals["executive_brief"] = 0.5
        elif is_short:
            signals["executive_brief"] = 0.3

        # Analysis signal: headings present, moderate-to-long
        heading_count = len(_HEADING_RE.findall(text))
        if heading_count >= 2 and len(text) > 500:
            signals["analysis"] = 0.7
        elif heading_count >= 1:
            signals["analysis"] = 0.4

        if not signals:
            return "mixed"

        # Check for mixed: multiple strong signals
        strong = [k for k, v in signals.items() if v >= 0.7]
        if len(strong) > 1:
            return "mixed"

        # Return the strongest signal
        best = max(signals, key=signals.get)  # type: ignore[arg-type]
        return best
