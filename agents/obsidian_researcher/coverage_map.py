"""Track which SCBE concepts have academic backing.

Maintains a per-concept coverage record and produces an Obsidian markdown
dashboard showing coverage scores, gaps, and research priorities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

# ------------------------------------------------------------------
# Canonical SCBE concept list (30 items)
# ------------------------------------------------------------------

SCBE_CONCEPTS: List[str] = [
    "Binary Encoding",
    "Sacred Tongue Tokenization",
    "Cross-Tokenization",
    "Geometric Embedding",
    "Hyperbolic Distance",
    "Path Planning",
    "Decision Trees",
    "PID Control",
    "Spectral Coherence",
    "Harmonic Analysis",
    "PHDM",
    "Entropic Defense",
    "Hive Integration",
    "PQC Envelope",
    "Energy-Authority Mapping",
    "Entropy-Chaos Mapping",
    "Risk-Threat Mapping",
    "Category Theory Foundations",
    "Domain Graph Isomorphism",
    "Bijective Encoding",
    "Evolving Lexicons",
    "Tongue Cross-Translation",
    "GeoSeal",
    "Concentric Ring Policy",
    "Governance Function",
    "Harmonic Wall",
    "Dual Lattice Consensus",
    "Federated Learning",
    "Post-Quantum Cryptography",
    "Fail-to-Noise",
]


# ------------------------------------------------------------------
# Per-concept coverage record
# ------------------------------------------------------------------

@dataclass
class ConceptCoverage:
    """Coverage statistics for a single SCBE concept."""
    concept: str
    academic_refs: int = 0
    internal_refs: int = 0
    source_types: Set[str] = field(default_factory=set)
    last_updated: str = ""
    confidence: float = 0.0


# ------------------------------------------------------------------
# Coverage map
# ------------------------------------------------------------------

class CoverageMap:
    """Aggregate coverage tracker across all SCBE concepts.

    Parameters
    ----------
    concepts : list[str] | None
        Override the default :data:`SCBE_CONCEPTS` list.
    """

    def __init__(self, concepts: Optional[List[str]] = None) -> None:
        concept_list = concepts if concepts is not None else SCBE_CONCEPTS
        self._coverage: Dict[str, ConceptCoverage] = {
            c: ConceptCoverage(concept=c) for c in concept_list
        }

    # ------------------------------------------------------------------
    # Update from ingestion
    # ------------------------------------------------------------------

    def update(self, result: "IngestionResult", links: List["WikiLink"]) -> None:
        """Increment coverage counters for concepts found in *links*.

        Each link whose ``target`` matches a tracked concept is counted.
        Academic sources (arXiv, web_page) increment ``academic_refs``;
        everything else increments ``internal_refs``.
        """
        now = datetime.now(timezone.utc).isoformat()
        source_type_str = str(result.source_type.value) if hasattr(result.source_type, "value") else str(result.source_type)
        is_academic = source_type_str in ("arxiv", "web_page")

        for link in links:
            target = getattr(link, "target_page", str(link))
            # Check for exact match or case-insensitive containment
            matched_concept = self._match_concept(target)
            if matched_concept is None:
                continue

            cc = self._coverage[matched_concept]
            if is_academic:
                cc.academic_refs += 1
            else:
                cc.internal_refs += 1
            cc.source_types.add(source_type_str)
            cc.last_updated = now
            cc.confidence = self.compute_confidence(matched_concept)

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    def compute_confidence(self, concept: str) -> float:
        """Compute a 0-1 confidence score for *concept*.

        Formula::

            confidence = min(1.0,
                0.3 * min(1, acad / 3)
              + 0.2 * min(1, internal / 2)
              + 0.2 * min(1, len(sources) / 3)
              + 0.3 * (1.0 if acad > 0 else 0.0)
            )

        Weights prioritise external academic backing (60% total) while
        still rewarding internal references and source diversity.
        """
        cc = self._coverage.get(concept)
        if cc is None:
            return 0.0

        acad = cc.academic_refs
        internal = cc.internal_refs
        sources = cc.source_types

        score = (
            0.3 * min(1.0, acad / 3)
            + 0.2 * min(1.0, internal / 2)
            + 0.2 * min(1.0, len(sources) / 3)
            + 0.3 * (1.0 if acad > 0 else 0.0)
        )
        return min(1.0, score)

    # ------------------------------------------------------------------
    # Gap analysis
    # ------------------------------------------------------------------

    def get_gaps(self) -> List[str]:
        """Return concepts whose confidence is below 0.4."""
        return [
            c for c, cc in self._coverage.items()
            if cc.confidence < 0.4
        ]

    # ------------------------------------------------------------------
    # Obsidian dashboard rendering
    # ------------------------------------------------------------------

    def render_map(self) -> str:
        """Produce an Obsidian markdown note summarising coverage.

        Sections: Summary stats, Coverage table, Research gaps.
        """
        total = len(self._coverage)
        gaps = self.get_gaps()
        covered = total - len(gaps)
        avg_confidence = (
            sum(cc.confidence for cc in self._coverage.values()) / total
            if total > 0 else 0.0
        )

        lines: List[str] = [
            "---",
            "title: SCBE Concept Coverage Map",
            f"date: {datetime.now(timezone.utc).isoformat()}",
            "type: dashboard",
            "---\n",
            "# SCBE Concept Coverage Map\n",
            "## Summary\n",
            f"- **Total concepts:** {total}",
            f"- **Covered (>= 0.4 confidence):** {covered}",
            f"- **Gaps (< 0.4 confidence):** {len(gaps)}",
            f"- **Average confidence:** {avg_confidence:.2f}\n",
            "## Coverage Table\n",
            "| Concept | Academic | Internal | Sources | Confidence | Status |",
            "|---------|----------|----------|---------|------------|--------|",
        ]

        # Sort by confidence descending
        for concept in sorted(self._coverage, key=lambda c: self._coverage[c].confidence, reverse=True):
            cc = self._coverage[concept]
            status = self._status_emoji(cc.confidence)
            sources_str = ", ".join(sorted(cc.source_types)) if cc.source_types else "-"
            lines.append(
                f"| {concept} | {cc.academic_refs} | {cc.internal_refs} "
                f"| {sources_str} | {cc.confidence:.2f} | {status} |"
            )

        lines.append("")

        # Research gaps section
        lines.append("## Research Gaps\n")
        if gaps:
            lines.append("The following concepts need additional research coverage:\n")
            for concept in sorted(gaps):
                cc = self._coverage[concept]
                lines.append(
                    f"- [ ] **{concept}** (confidence: {cc.confidence:.2f}) "
                    f"\u2014 {self._gap_recommendation(cc)}"
                )
        else:
            lines.append("_All concepts have adequate coverage._")

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_concept(self, target: str) -> Optional[str]:
        """Find the tracked concept that *target* refers to, or ``None``.

        Performs exact match first, then case-insensitive containment.
        """
        # Exact
        if target in self._coverage:
            return target

        # Case-insensitive
        target_lower = target.lower()
        for concept in self._coverage:
            if concept.lower() == target_lower:
                return concept
            if concept.lower() in target_lower or target_lower in concept.lower():
                return concept

        return None

    @staticmethod
    def _status_emoji(confidence: float) -> str:
        """Return a text status indicator for confidence level."""
        if confidence >= 0.8:
            return "STRONG"
        if confidence >= 0.4:
            return "PARTIAL"
        if confidence > 0.0:
            return "WEAK"
        return "NONE"

    @staticmethod
    def _gap_recommendation(cc: ConceptCoverage) -> str:
        """Return a short recommendation string for a coverage gap."""
        if cc.academic_refs == 0 and cc.internal_refs == 0:
            return "No references found. Search arXiv and internal vault."
        if cc.academic_refs == 0:
            return "Has internal refs but no academic backing. Search arXiv."
        if cc.internal_refs == 0:
            return "Has academic refs but no internal documentation. Write vault note."
        return "Needs broader source diversity."
