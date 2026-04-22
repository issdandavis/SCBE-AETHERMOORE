"""Obsidian vault source adapter for the researcher agent.

Reads ``.md`` files from an existing Obsidian vault and converts them
into ``IngestionResult`` records.  Pure-stdlib implementation (uses
:mod:`pathlib` for filesystem access and :mod:`re` for wikilink extraction).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
"""Match ``[[target]]`` and ``[[target|alias]]``, capturing *target*."""

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
"""Match YAML front-matter delimited by ``---`` at file start."""

STOP_WORDS: frozenset[str] = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for with on "
    "at by from as into through during before after above below between "
    "and but or not no nor so yet both either neither each every all any "
    "few more most other some such only own than too very just about also "
    "then up out if it its".split()
)


class VaultSource(SourceAdapter):
    """Reads Markdown files from an Obsidian vault on the local filesystem.

    Parameters
    ----------
    config : dict
        Required keys:

        * ``vault_root`` -- absolute or relative path to the Obsidian vault
          root directory.  All ``.md`` files under this tree are indexed.

        Optional keys:

        * ``encoding`` -- text encoding for ``.md`` files (default ``utf-8``).
        * ``exclude_dirs`` -- list of directory names to skip (e.g.
          ``[".obsidian", ".trash"]``).  Defaults to
          ``[".obsidian", ".trash", ".git"]``.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.VAULT, config=config or {})

        vault_root = self.config.get("vault_root")
        if not vault_root:
            raise ValueError("config must include 'vault_root'")

        self._vault_root = Path(vault_root).resolve()
        if not self._vault_root.is_dir():
            raise FileNotFoundError(
                f"vault_root does not exist or is not a directory: {self._vault_root}"
            )

        self._encoding: str = self.config.get("encoding", "utf-8")
        self._exclude_dirs: set[str] = set(
            self.config.get("exclude_dirs", [".obsidian", ".trash", ".git"])
        )

    # ------------------------------------------------------------------
    # SourceAdapter interface
    # ------------------------------------------------------------------

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Return vault pages whose title or content matches *query* keywords.

        Matching is case-insensitive.  A page is included if **all** query
        keywords (after stop-word removal) appear in either the stem-title
        or the file body.
        """
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return []

        results: List[IngestionResult] = []
        for md_path in self._iter_md_files():
            title = md_path.stem
            title_lower = title.lower()

            try:
                text = md_path.read_text(encoding=self._encoding, errors="replace")
            except OSError:
                logger.debug("Could not read %s", md_path, exc_info=True)
                continue

            searchable = title_lower + " " + text.lower()

            if all(kw in searchable for kw in query_keywords):
                results.append(self._file_to_result(md_path, title, text))

        return results

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a single vault page by its title (stem name, no extension).

        The lookup is case-insensitive.  Returns ``None`` when no match is
        found.
        """
        target = identifier.strip()
        if not target:
            return None

        target_lower = target.lower()
        for md_path in self._iter_md_files():
            if md_path.stem.lower() == target_lower:
                try:
                    text = md_path.read_text(
                        encoding=self._encoding, errors="replace"
                    )
                except OSError:
                    logger.debug("Could not read %s", md_path, exc_info=True)
                    return None
                return self._file_to_result(md_path, md_path.stem, text)

        return None

    def health_check(self) -> bool:
        """Return ``True`` if the vault root exists and contains ``.md`` files."""
        try:
            return self._vault_root.is_dir() and any(self._iter_md_files())
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Public helper methods
    # ------------------------------------------------------------------

    def get_all_page_titles(self) -> List[str]:
        """Return the stem titles of every ``.md`` file in the vault."""
        return [p.stem for p in self._iter_md_files()]

    def get_all_wikilinks(self) -> Dict[str, List[str]]:
        """Return a mapping of ``{page_title: [link_targets, ...]}``
        for every page in the vault."""
        result: Dict[str, List[str]] = {}
        for md_path in self._iter_md_files():
            try:
                text = md_path.read_text(encoding=self._encoding, errors="replace")
            except OSError:
                continue
            links = self._extract_wikilinks(text)
            result[md_path.stem] = links
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_md_files(self):
        """Yield every ``.md`` ``Path`` under the vault root, honouring
        ``exclude_dirs``."""
        for md_path in self._vault_root.rglob("*.md"):
            # Skip excluded directory subtrees
            if self._exclude_dirs and any(
                part in self._exclude_dirs for part in md_path.relative_to(self._vault_root).parts
            ):
                continue
            yield md_path

    def _file_to_result(
        self, md_path: Path, title: str, text: str
    ) -> IngestionResult:
        """Convert a vault Markdown file to an ``IngestionResult``."""
        frontmatter = self._extract_frontmatter(text)
        wikilinks = self._extract_wikilinks(text)
        keywords = self._extract_keywords(text)

        # Derive tags from front-matter "tags" field if present
        fm_tags: List[str] = []
        raw_tags = frontmatter.get("tags")
        if isinstance(raw_tags, list):
            fm_tags = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str):
            fm_tags = [t.strip() for t in raw_tags.replace(",", " ").split() if t.strip()]

        rel_path = md_path.relative_to(self._vault_root)

        return IngestionResult(
            source_type=SourceType.VAULT,
            raw_content=text,
            title=title,
            authors=_listify(frontmatter.get("author") or frontmatter.get("authors")),
            url=None,
            timestamp=str(frontmatter.get("date", "")),
            identifiers={"vault_path": str(rel_path)},
            tags=fm_tags,
            metadata={
                "frontmatter": frontmatter,
                "wikilinks": wikilinks,
                "keywords": keywords[:50],  # cap for sanity
            },
            summary=text[:500],
        )

    # ------------------------------------------------------------------
    # Static / class-level extraction utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_frontmatter(text: str) -> Dict[str, Any]:
        """Parse YAML front-matter between ``---`` delimiters.

        Uses a minimal key-value parser (no PyYAML dependency) that
        handles scalar values, bare lists (``- item``), and inline
        lists (``[a, b, c]``).
        """
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return {}

        block = match.group(1)
        result: Dict[str, Any] = {}
        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # List continuation:  "  - value"
            if stripped.startswith("- ") and current_key is not None:
                if current_list is None:
                    current_list = []
                current_list.append(stripped[2:].strip().strip("\"'"))
                result[current_key] = current_list
                continue

            # New key-value pair
            if ":" in stripped:
                if current_list is not None:
                    current_list = None

                key, _, raw_value = stripped.partition(":")
                key = key.strip()
                raw_value = raw_value.strip()

                current_key = key

                if not raw_value:
                    # value may be a list on following lines
                    result[key] = ""
                    current_list = None
                    continue

                # Inline list: [a, b, c]
                if raw_value.startswith("[") and raw_value.endswith("]"):
                    items = [
                        v.strip().strip("\"'")
                        for v in raw_value[1:-1].split(",")
                        if v.strip()
                    ]
                    result[key] = items
                    current_list = None
                else:
                    result[key] = raw_value.strip("\"'")
                    current_list = None

        return result

    @staticmethod
    def _extract_wikilinks(text: str) -> List[str]:
        """Return deduplicated ``[[target]]`` link targets in order of
        first appearance."""
        seen: set[str] = set()
        targets: List[str] = []
        for match in _WIKILINK_RE.finditer(text):
            target = match.group(1).strip()
            if target and target not in seen:
                seen.add(target)
                targets.append(target)
        return targets

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Split *text* into lowercase tokens, strip non-alpha characters,
        remove stop words and short tokens, and return the unique keywords
        in order of first appearance."""
        seen: set[str] = set()
        keywords: List[str] = []
        for raw_token in text.split():
            token = re.sub(r"[^a-z0-9]", "", raw_token.lower())
            if len(token) < 3:
                continue
            if token in STOP_WORDS:
                continue
            if token not in seen:
                seen.add(token)
                keywords.append(token)
        return keywords


# ---------------------------------------------------------------------------
# Module-private utilities
# ---------------------------------------------------------------------------

def _listify(value: Any) -> List[str]:
    """Coerce a front-matter author value to ``List[str]``."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value)]
