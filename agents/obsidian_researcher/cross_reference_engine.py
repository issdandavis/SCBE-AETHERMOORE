"""Cross-reference engine for Obsidian vault wikilink discovery.

Takes an IngestionResult and finds which existing vault pages should be
linked via [[wikilinks]] using four complementary strategies:

1. **Keyword scan** -- direct keyword overlap between ingested text and
   vault page keyword lists.
2. **CDDM morphism scan** -- detects domain vocabulary in the text, then
   follows cross-domain morphisms to discover vault pages in *related*
   domains that the author might not have linked manually.
3. **Citation scan** -- extracts arXiv IDs and DOIs from the text and
   checks every vault page for matching identifiers.
4. **Semantic scan** -- placeholder for future embedding-based similarity.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import re

from .source_adapter import IngestionResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "has", "have", "having", "he", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "if", "in",
    "into", "is", "it", "its", "itself", "just", "me", "might", "more",
    "most", "must", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "re", "same", "shall", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "us", "very", "was", "we", "were",
    "what", "when", "where", "which", "while", "who", "whom", "why", "will",
    "with", "would", "you", "your", "yours", "yourself", "yourselves",
}

# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------


class LinkType(str, Enum):
    """Classification of how a wikilink was discovered."""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    CDDM_MORPHISM = "cddm_morphism"
    CITATION = "citation"
    MANUAL = "manual"


@dataclass
class WikiLink:
    """A proposed [[wikilink]] to an existing vault page."""
    target_page: str
    link_type: LinkType
    confidence: float          # 0.0 -- 1.0
    reason: str
    cddm_morphism: Optional[str] = None


# ---------------------------------------------------------------------------
# Domain vocabulary for CDDM scan
# ---------------------------------------------------------------------------

_DOMAIN_VOCAB: Dict[str, List[str]] = {
    "Energy": [
        "energy", "force", "power", "joule", "kinetic", "potential", "watt",
        "encryption", "key",
    ],
    "Authority": [
        "authority", "control", "command", "governance", "permission", "admin",
    ],
    "Entropy": [
        "entropy", "chaos", "disorder", "randomness", "noise", "drift",
    ],
    "PlotChaos": [
        "plot", "narrative", "story", "drama", "conflict", "tension",
    ],
    "PolicyBreakdown": [
        "policy", "rule", "regulation", "compliance", "violation", "breakdown",
    ],
    "Complexity": [
        "complexity", "computation", "algorithm", "flop", "processing",
        "optimize",
    ],
    "Intrigue": [
        "intrigue", "mystery", "puzzle", "deception", "subtlety",
    ],
    "Risk": [
        "risk", "threat", "vulnerability", "attack", "exploit", "danger",
        "security",
    ],
    "Danger": [
        "danger", "hazard", "harm", "critical", "emergency", "severe",
    ],
    "Structure": [
        "structure", "schema", "pattern", "topology", "graph", "lattice",
    ],
    "Momentum": [
        "momentum", "flow", "velocity", "inertia", "transport", "network",
    ],
    "Communication": [
        "communication", "signal", "message", "protocol", "channel",
    ],
    "DataFlow": [
        "data", "bandwidth", "throughput", "latency", "streaming",
    ],
}

# Simplified cross-domain morphism map.  Each entry maps
# source_domain -> list of (target_domain, morphism_name) pairs.
_MORPHISMS: Dict[str, List[Tuple[str, str]]] = {
    "Energy": [
        ("Authority", "energy_to_authority"),
        ("Momentum", "energy_to_momentum"),
    ],
    "Entropy": [
        ("PlotChaos", "entropy_to_chaos"),
        ("PolicyBreakdown", "entropy_to_breakdown"),
    ],
    "Risk": [
        ("Danger", "risk_to_danger"),
        ("Authority", "risk_to_authority"),
    ],
    "Authority": [
        ("Danger", "authority_to_danger"),
    ],
    "PlotChaos": [
        ("Intrigue", "chaos_to_intrigue"),
    ],
    "Complexity": [
        ("Intrigue", "complexity_to_intrigue"),
    ],
    "Structure": [
        ("Communication", "structure_to_communication"),
    ],
}

# Regex patterns for citation extraction
_ARXIV_RE = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
_DOI_RE = re.compile(r"\b(10\.\d{4,}/\S+)")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class CrossReferenceEngine:
    """Discover [[wikilinks]] between an ingested result and existing vault pages.

    Parameters
    ----------
    vault_page_titles:
        All page titles currently in the vault.
    vault_page_keywords:
        Mapping of page title -> list of keywords extracted from that page.
    vault_page_contents:
        Mapping of page title -> full raw text (used for citation scanning).
    """

    def __init__(
        self,
        vault_page_titles: List[str],
        vault_page_keywords: Dict[str, List[str]],
        vault_page_contents: Dict[str, str],
    ) -> None:
        self.vault_page_titles = vault_page_titles
        self.vault_page_keywords = vault_page_keywords
        self.vault_page_contents = vault_page_contents

        # Pre-compute lowercase keyword sets per page for fast lookup.
        self._kw_sets: Dict[str, Set[str]] = {
            title: {kw.lower() for kw in kws}
            for title, kws in vault_page_keywords.items()
        }

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def find_links(
        self,
        result: IngestionResult,
        min_confidence: float = 0.5,
    ) -> List[WikiLink]:
        """Run all strategies and return merged, filtered, sorted links.

        For each *target_page* seen across strategies the link with the
        highest confidence is kept.  Links below *min_confidence* are
        dropped.  The final list is sorted by confidence descending.
        """
        text = f"{result.title}\n{result.raw_content}\n{result.summary}"

        all_links: List[WikiLink] = []
        all_links.extend(self.keyword_scan(text))
        all_links.extend(self.cddm_scan(text))
        all_links.extend(self.citation_scan(result.identifiers, text))
        # Semantic scan is a placeholder -- returns empty today.

        # Merge: keep highest-confidence link per target page.
        best: Dict[str, WikiLink] = {}
        for link in all_links:
            existing = best.get(link.target_page)
            if existing is None or link.confidence > existing.confidence:
                best[link.target_page] = link

        merged = [
            lnk for lnk in best.values()
            if lnk.confidence >= min_confidence
        ]
        merged.sort(key=lambda lnk: lnk.confidence, reverse=True)
        return merged

    # ------------------------------------------------------------------ #
    # Strategy 1 -- Keyword scan                                          #
    # ------------------------------------------------------------------ #

    def keyword_scan(self, text: str) -> List[WikiLink]:
        """Direct keyword overlap between *text* and vault page keywords.

        For each vault page, check if any of its keywords appear
        (case-insensitive) in *text*.  Base confidence is 0.7, with a
        +0.3 bonus when the matched keyword is longer than 10 characters
        (longer keywords are less likely to be coincidental).

        At most one :class:`WikiLink` is emitted per page.
        """
        text_lower = text.lower()
        links: List[WikiLink] = []

        for title in self.vault_page_titles:
            kw_set = self._kw_sets.get(title)
            if not kw_set:
                continue

            best_kw: Optional[str] = None
            best_conf: float = 0.0

            for kw in kw_set:
                if kw in text_lower:
                    conf = 0.7 + (0.3 if len(kw) > 10 else 0.0)
                    if conf > best_conf:
                        best_conf = conf
                        best_kw = kw

            if best_kw is not None:
                links.append(WikiLink(
                    target_page=title,
                    link_type=LinkType.KEYWORD,
                    confidence=best_conf,
                    reason=f"keyword match: '{best_kw}'",
                ))

        return links

    # ------------------------------------------------------------------ #
    # Strategy 2 -- CDDM morphism scan                                   #
    # ------------------------------------------------------------------ #

    def cddm_scan(self, text: str) -> List[WikiLink]:
        """Find vault links via cross-domain morphisms.

        1. Detect which CDDM domains the *text* touches (keyword overlap
           with domain vocabulary).
        2. For each active domain, follow morphism edges to reachable
           target domains.
        3. For each reachable target domain, check whether any vault page
           keywords overlap with that domain's vocabulary.

        Emitted links carry the morphism name so downstream renderers can
        annotate the link with the conceptual bridge.
        """
        text_lower = text.lower()

        # Step 1 -- detect active domains.
        active_domains: Set[str] = set()
        for domain, vocab in _DOMAIN_VOCAB.items():
            for word in vocab:
                if word in text_lower:
                    active_domains.add(domain)
                    break

        if not active_domains:
            return []

        # Step 2 -- collect reachable (target_domain, morphism_name) pairs.
        reachable: List[Tuple[str, str]] = []
        for src in active_domains:
            for target_domain, morphism_name in _MORPHISMS.get(src, []):
                if target_domain not in active_domains:
                    reachable.append((target_domain, morphism_name))

        if not reachable:
            return []

        # Step 3 -- match vault page keywords against target domain vocab.
        links: List[WikiLink] = []
        seen_pages: Set[str] = set()

        for target_domain, morphism_name in reachable:
            target_vocab = set(_DOMAIN_VOCAB.get(target_domain, []))
            if not target_vocab:
                continue

            for title in self.vault_page_titles:
                if title in seen_pages:
                    continue
                page_kws = self._kw_sets.get(title, set())
                overlap = page_kws & target_vocab
                if overlap:
                    seen_pages.add(title)
                    links.append(WikiLink(
                        target_page=title,
                        link_type=LinkType.CDDM_MORPHISM,
                        confidence=0.65,
                        reason=(
                            f"CDDM morphism '{morphism_name}' bridges "
                            f"to domain '{target_domain}' via keyword "
                            f"overlap: {sorted(overlap)}"
                        ),
                        cddm_morphism=morphism_name,
                    ))

        return links

    # ------------------------------------------------------------------ #
    # Strategy 3 -- Citation scan                                         #
    # ------------------------------------------------------------------ #

    def citation_scan(
        self,
        identifiers: Dict[str, str],
        text: str,
    ) -> List[WikiLink]:
        """Find vault pages that share arXiv IDs or DOIs with the text.

        Extracts identifiers from both the *text* and the explicit
        *identifiers* dict, then scans every vault page's content for
        matches.  Confidence is 0.95 for identifier-dict matches and
        0.90 for regex-extracted matches.
        """
        # Gather candidate identifiers from identifiers dict.
        explicit_ids: Set[str] = set()
        for _key, val in identifiers.items():
            explicit_ids.add(val)

        # Gather candidate identifiers by regex from text.
        regex_ids: Set[str] = set()
        for m in _ARXIV_RE.finditer(text):
            regex_ids.add(m.group(1))
        for m in _DOI_RE.finditer(text):
            regex_ids.add(m.group(1))

        all_ids = explicit_ids | regex_ids
        if not all_ids:
            return []

        links: List[WikiLink] = []
        seen_pages: Set[str] = set()

        for title in self.vault_page_titles:
            if title in seen_pages:
                continue
            page_text = self.vault_page_contents.get(title, "")
            if not page_text:
                continue

            for cid in all_ids:
                if cid in page_text:
                    conf = 0.95 if cid in explicit_ids else 0.90
                    seen_pages.add(title)
                    links.append(WikiLink(
                        target_page=title,
                        link_type=LinkType.CITATION,
                        confidence=conf,
                        reason=f"shared identifier: '{cid}'",
                    ))
                    break  # one link per page

        return links

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _extract_keywords(self, text: str) -> List[str]:
        """Split text into lowercase keyword tokens.

        Strips non-alphanumeric characters, removes English stop words
        and any token shorter than 3 characters.  Uses the same stop
        word list referenced by vault_source.py.
        """
        tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
        return [
            tok for tok in tokens
            if len(tok) >= 3 and tok not in _STOP_WORDS
        ]
