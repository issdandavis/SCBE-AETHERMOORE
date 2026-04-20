"""Brainstorm source adapter for the Obsidian researcher agent.

Captures user ideas from raw text strings or local files and
structures them into ``IngestionResult`` records.  Pure-stdlib
implementation with zero external dependencies.

This adapter is intentionally simple: it turns free-form notes,
research hunches, and problem statements into the same normalised
format used by every other source so they can be cross-referenced
against arXiv papers, Reddit threads, and vault pages.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TITLE_MAX_LEN = 60
_DEFAULT_ENCODING = "utf-8"


class BrainstormSource(SourceAdapter):
    """Adapter that ingests user brainstorms -- raw text or files --
    and emits :class:`IngestionResult` records.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``encoding`` -- file encoding when reading from disk
          (default ``utf-8``).
        * ``author`` -- default author name attached to brainstorms.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.BRAINSTORM, config=config or {})

        self._encoding: str = self.config.get("encoding", _DEFAULT_ENCODING)
        self._author: str = self.config.get("author", "")

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Ingest *query* as raw brainstorm text.

        Returns a single-element list containing the structured idea,
        or an empty list if the input is blank.
        """
        text = query.strip()
        if not text:
            return []

        title = kwargs.get("title") or self._auto_title(text)
        author = kwargs.get("author", self._author)
        result = self._text_to_result(text, title, author)
        return [result]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Read a brainstorm from a file at *identifier* (a file path).

        Returns ``None`` if the file cannot be read.
        """
        file_path = Path(identifier.strip())
        if not file_path.is_file():
            logger.warning("Brainstorm file not found: %s", file_path)
            return None

        try:
            text = file_path.read_text(encoding=self._encoding, errors="replace")
        except OSError:
            logger.exception("Could not read brainstorm file: %s", file_path)
            return None

        if not text.strip():
            return None

        title = self._auto_title(text)
        return self._text_to_result(
            text.strip(),
            title,
            self._author,
            file_path=str(file_path.resolve()),
        )

    def health_check(self) -> bool:
        """Return ``True`` -- brainstorms have no external dependency."""
        return True

    # ------------------------------------------------------------------
    # Idea structuring
    # ------------------------------------------------------------------

    @staticmethod
    def _structure_idea(text: str) -> Dict[str, Any]:
        """Extract structured sections from free-form brainstorm text.

        Recognised markers:

        * **Problem statement** -- lines starting with ``Problem:``
          (case-insensitive).
        * **Direction / approach** -- everything that is not a problem
          statement or open question.
        * **Open questions** -- lines starting with ``?`` or
          ``Question:`` (case-insensitive).

        Returns a dict with keys ``problem_statements``,
        ``directions``, and ``open_questions`` (each a list of strings).
        """
        problem_statements: List[str] = []
        open_questions: List[str] = []
        directions: List[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            lower = line.lower()

            # Problem statement
            if lower.startswith("problem:"):
                problem_statements.append(line[len("problem:"):].strip())
            # Open questions
            elif lower.startswith("question:"):
                open_questions.append(line[len("question:"):].strip())
            elif line.startswith("?"):
                question_text = line[1:].strip()
                if question_text:
                    open_questions.append(question_text)
            else:
                directions.append(line)

        return {
            "problem_statements": problem_statements,
            "directions": directions,
            "open_questions": open_questions,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _text_to_result(
        self,
        text: str,
        title: str,
        author: str,
        *,
        file_path: Optional[str] = None,
    ) -> IngestionResult:
        """Convert raw brainstorm text to an ``IngestionResult``."""
        structured = self._structure_idea(text)
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        # Deterministic ID from content hash
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

        identifiers: Dict[str, str] = {"brainstorm_hash": content_hash}
        if file_path:
            identifiers["file_path"] = file_path

        # Auto-generate tags from problem statements and questions
        tags: List[str] = ["brainstorm"]
        if structured["problem_statements"]:
            tags.append("has-problem")
        if structured["open_questions"]:
            tags.append("has-questions")

        return IngestionResult(
            source_type=SourceType.BRAINSTORM,
            raw_content=text,
            title=title,
            authors=[author] if author else [],
            url=None,
            timestamp=timestamp,
            identifiers=identifiers,
            tags=tags,
            metadata={
                "structured": structured,
                "problem_count": len(structured["problem_statements"]),
                "question_count": len(structured["open_questions"]),
                "direction_count": len(structured["directions"]),
                "char_count": len(text),
                "line_count": len(text.splitlines()),
            },
            summary=text[:500],
        )

    @staticmethod
    def _auto_title(text: str) -> str:
        """Generate a title from the first line of text, truncated to
        :data:`_TITLE_MAX_LEN` characters.

        If the first line is longer than the limit, it is truncated
        and an ellipsis is appended.
        """
        first_line = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break

        if not first_line:
            return "Untitled brainstorm"

        # Strip leading markdown heading markers
        if first_line.startswith("#"):
            first_line = first_line.lstrip("#").strip()

        if len(first_line) <= _TITLE_MAX_LEN:
            return first_line

        # Truncate at word boundary
        truncated = first_line[:_TITLE_MAX_LEN]
        last_space = truncated.rfind(" ")
        if last_space > _TITLE_MAX_LEN // 2:
            truncated = truncated[:last_space]
        return truncated + "..."
