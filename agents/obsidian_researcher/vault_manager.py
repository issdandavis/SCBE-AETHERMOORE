"""Manage writing notes to the Obsidian vault filesystem.

Handles folder routing (by content keywords and source type), duplicate
detection, filename sanitisation, and atomic writes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from .source_adapter import SourceType, IngestionResult
from .cross_reference_engine import WikiLink


class VaultManager:
    """Read/write interface for an Obsidian vault directory tree."""

    # ------------------------------------------------------------------
    # Keyword -> subfolder routing
    # ------------------------------------------------------------------

    KEYWORD_ROUTING: Dict[str, str] = {
        "sacred_tongue": "Tongues/",
        "tongue": "Tongues/",
        "lexicon": "Tongues/",
        "architecture": "Architecture/",
        "14-layer": "Architecture/",
        "layer": "Architecture/",
        "cddm": "CDDM/",
        "morphism": "CDDM/",
        "domain": "CDDM/",
        "functor": "CDDM/",
        "patent": "Growth Log/",
        "growth": "Growth Log/",
        "milestone": "Growth Log/",
    }

    SOURCE_TYPE_ROUTING: Dict[SourceType, str] = {
        SourceType.ARXIV: "References/",
        SourceType.WEB_PAGE: "References/",
        SourceType.REDDIT: "Growth Log/",
        SourceType.BRAINSTORM: "Growth Log/",
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, vault_root: str) -> None:
        self.vault_root = Path(vault_root)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_note(self, result: IngestionResult, links: List[WikiLink]) -> str:
        """Determine the subfolder for a note.

        Strategy:
        1. Scan the title, summary, and link targets for keyword matches.
        2. Fall back to source-type routing.
        3. Default to ``"Inbox/"`` if nothing matches.
        """
        # Build a single searchable blob (lowercase)
        parts: List[str] = [result.title, result.summary, result.raw_content]
        for link in links:
            parts.append(getattr(link, "target_page", ""))
        blob = " ".join(parts).lower()

        # Check keywords (order: longest match first for specificity)
        for keyword in sorted(self.KEYWORD_ROUTING, key=len, reverse=True):
            if keyword in blob:
                return self.KEYWORD_ROUTING[keyword]

        # Fall back to source type
        return self.SOURCE_TYPE_ROUTING.get(result.source_type, "Inbox/")

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def check_duplicate(self, title: str) -> bool:
        """Return ``True`` if a ``.md`` file with *title* already exists."""
        safe_name = self.sanitize_filename(title)
        # Walk vault looking for a match
        for md_file in self.vault_root.rglob("*.md"):
            if md_file.stem == safe_name:
                return True
        return False

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def write_note(self, markdown: str, folder: str, title: str) -> Path:
        """Write *markdown* to ``vault_root / folder / title.md``.

        Creates intermediate directories as needed and returns the final
        ``Path`` object.
        """
        safe_name = self.sanitize_filename(title)
        target_dir = self.vault_root / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / f"{safe_name}.md"
        target_path.write_text(markdown, encoding="utf-8")
        return target_path

    # ------------------------------------------------------------------
    # Filename helpers
    # ------------------------------------------------------------------

    @staticmethod
    def sanitize_filename(title: str) -> str:
        """Replace filesystem-invalid characters with hyphens.

        The result is stripped, collapsed (no double hyphens), and limited
        to 100 characters.
        """
        # Replace characters that are invalid on Windows / macOS / Linux
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title)
        # Collapse runs of hyphens / whitespace
        safe = re.sub(r"[\s\-]+", "-", safe).strip("-")
        return safe[:100]

    # ------------------------------------------------------------------
    # Vault queries
    # ------------------------------------------------------------------

    def list_all_pages(self) -> List[str]:
        """Return every ``.md`` filename (without extension) under the vault."""
        return sorted(
            md_file.stem
            for md_file in self.vault_root.rglob("*.md")
        )
