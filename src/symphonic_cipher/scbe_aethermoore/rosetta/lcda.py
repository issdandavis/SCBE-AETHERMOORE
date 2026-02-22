"""LCDA — Linguistic Context Dimensional Analysis.

Custom embedding dimensions for SCBE governance properties.
Uses seed-based difference vectors with TF-IDF bag-of-words projection
(no GPU needed for Phase 1).

Each LCDA dimension is defined by positive/negative seed phrases that
anchor the direction. Context text is projected onto these axes to produce
governance-relevant scores.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LCDADimension:
    """A single governance dimension defined by seed anchors."""

    name: str                       # "boundary_risk", "agent_authority"
    positive_seeds: list[str]       # Phrases for high-scoring direction
    negative_seeds: list[str]       # Phrases for low-scoring direction
    scbe_layer: Optional[int]       # Which SCBE layer this maps to (None = general)
    weight: float = 1.0             # Dimension importance weight


# ── Pre-defined SCBE governance dimensions ─────────────────

DEFAULT_DIMENSIONS: list[LCDADimension] = [
    LCDADimension(
        name="boundary_risk",
        positive_seeds=[
            "bypass security", "ignore rules", "override policy",
            "escalate privilege", "disable firewall", "skip validation",
            "jailbreak", "prompt injection", "circumvent",
        ],
        negative_seeds=[
            "respect policy", "follow rules", "deny access",
            "enforce boundary", "validate input", "check permissions",
            "maintain security", "comply with guidelines",
        ],
        scbe_layer=13,
    ),
    LCDADimension(
        name="agent_authority",
        positive_seeds=[
            "admin access", "root permission", "full control",
            "unrestricted", "sudo", "superuser", "elevated privileges",
            "system administrator", "override controls",
        ],
        negative_seeds=[
            "read only", "limited scope", "sandboxed",
            "restricted", "viewer access", "guest mode",
            "no permission", "locked down", "minimal access",
        ],
        scbe_layer=7,
    ),
    LCDADimension(
        name="data_sensitivity",
        positive_seeds=[
            "secret key", "password", "PII", "classified",
            "private data", "credentials", "social security",
            "credit card", "medical records", "encryption key",
        ],
        negative_seeds=[
            "public data", "open source", "documentation",
            "readme", "published paper", "press release",
            "marketing material", "open access",
        ],
        scbe_layer=4,
    ),
    LCDADimension(
        name="jurisdictional_scope",
        positive_seeds=[
            "cross-system", "galactic", "multi-federation",
            "external", "inter-agency", "global", "worldwide",
            "cross-border", "multi-tenant",
        ],
        negative_seeds=[
            "local only", "single system", "internal",
            "sandboxed", "isolated", "self-contained",
            "same-origin", "same-tenant",
        ],
        scbe_layer=12,
    ),
    LCDADimension(
        name="temporal_urgency",
        positive_seeds=[
            "emergency", "critical now", "immediate",
            "time-sensitive", "urgent", "asap", "deadline",
            "zero-day", "active threat", "real-time",
        ],
        negative_seeds=[
            "routine", "scheduled", "low priority",
            "whenever", "background task", "no rush",
            "deferred", "next sprint", "backlog",
        ],
        scbe_layer=None,  # Maps to tau dimension
    ),
]


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'[a-zA-Z]+', text.lower())


def _build_vocab(seed_phrases: list[str]) -> Counter:
    """Build a term frequency counter from seed phrases."""
    counts: Counter = Counter()
    for phrase in seed_phrases:
        tokens = _tokenize(phrase)
        counts.update(tokens)
    return counts


def _idf_weight(token: str, all_docs: list[list[str]]) -> float:
    """Inverse document frequency weight."""
    doc_count = sum(1 for doc in all_docs if token in doc)
    if doc_count == 0:
        return 0.0
    return math.log(len(all_docs) / doc_count) + 1.0


class LCDAProjector:
    """Projects context text onto custom SCBE governance dimensions.

    Uses TF-IDF bag-of-words with seed-based difference vectors.
    No external ML models needed — pure Python computation.
    """

    def __init__(
        self,
        dimensions: Optional[list[LCDADimension]] = None,
    ) -> None:
        self.dimensions = dimensions or DEFAULT_DIMENSIONS
        self._positive_vocabs: list[Counter] = []
        self._negative_vocabs: list[Counter] = []
        self._all_seed_docs: list[list[str]] = []
        self._build_projectors()

    def _build_projectors(self) -> None:
        """Pre-compute TF vectors for each dimension's seed sets."""
        all_docs: list[list[str]] = []

        for dim in self.dimensions:
            pos_vocab = _build_vocab(dim.positive_seeds)
            neg_vocab = _build_vocab(dim.negative_seeds)
            self._positive_vocabs.append(pos_vocab)
            self._negative_vocabs.append(neg_vocab)

            # Collect all seed phrases as documents for IDF
            for phrase in dim.positive_seeds + dim.negative_seeds:
                all_docs.append(_tokenize(phrase))

        self._all_seed_docs = all_docs

    def _score_against_seeds(
        self, tokens: list[str], pos_vocab: Counter, neg_vocab: Counter
    ) -> float:
        """Score a token list against positive/negative seed vocabularies.

        Returns a value in [-1, 1]:
          +1 = perfectly matches positive seeds
          -1 = perfectly matches negative seeds
           0 = no overlap with either
        """
        if not tokens:
            return 0.0

        input_counts = Counter(tokens)

        pos_score = 0.0
        neg_score = 0.0

        for token, count in input_counts.items():
            idf = _idf_weight(token, self._all_seed_docs)
            tf = count / len(tokens)
            weighted = tf * idf

            if token in pos_vocab:
                pos_score += weighted * pos_vocab[token]
            if token in neg_vocab:
                neg_score += weighted * neg_vocab[token]

        total = pos_score + neg_score
        if total == 0:
            return 0.0

        # Normalize to [-1, 1]
        raw = (pos_score - neg_score) / total
        return max(-1.0, min(1.0, raw))

    def project(self, context_text: str) -> dict[str, float]:
        """Project context text onto all SCBE dimensions.

        Returns dict mapping dimension name to score in [0, 1]
        (0 = safe/low, 1 = high risk/authority/sensitivity/scope/urgency).
        """
        tokens = _tokenize(context_text)
        scores: dict[str, float] = {}

        for i, dim in enumerate(self.dimensions):
            raw = self._score_against_seeds(
                tokens, self._positive_vocabs[i], self._negative_vocabs[i]
            )
            # Map from [-1, 1] to [0, 1]
            normalized = (raw + 1.0) / 2.0
            scores[dim.name] = round(normalized, 4)

        return scores

    def score_vector(self, context_text: str) -> list[float]:
        """Return ordered score vector for all dimensions."""
        scores = self.project(context_text)
        return [scores[dim.name] for dim in self.dimensions]

    def score_with_layers(self, context_text: str) -> dict[str, dict]:
        """Project with SCBE layer annotations."""
        scores = self.project(context_text)
        result = {}
        for dim in self.dimensions:
            result[dim.name] = {
                "score": scores[dim.name],
                "scbe_layer": dim.scbe_layer,
                "weight": dim.weight,
            }
        return result

    def top_dimensions(self, context_text: str, n: int = 3) -> list[tuple[str, float]]:
        """Return the top-N highest scoring dimensions."""
        scores = self.project(context_text)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:n]

    def composite_risk(self, context_text: str) -> float:
        """Compute a single composite risk score (weighted average of all dimensions)."""
        scores = self.project(context_text)
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        weighted = sum(scores[d.name] * d.weight for d in self.dimensions)
        return round(weighted / total_weight, 4)

    def add_dimension(self, dim: LCDADimension) -> None:
        """Add a custom dimension at runtime."""
        self.dimensions.append(dim)
        self._positive_vocabs.append(_build_vocab(dim.positive_seeds))
        self._negative_vocabs.append(_build_vocab(dim.negative_seeds))
        for phrase in dim.positive_seeds + dim.negative_seeds:
            self._all_seed_docs.append(_tokenize(phrase))

    def export_sft(self, context_text: str) -> dict:
        """Export a projection as an SFT training record."""
        scores = self.project(context_text)
        return {
            "id": "lcda-projection-001",
            "category": "lcda-dimension",
            "instruction": f"Project the following context onto SCBE governance dimensions: '{context_text[:200]}'",
            "response": str(scores),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "4.0.0",
                "type": "lcda_projection",
                "dimensions": [d.name for d in self.dimensions],
            },
        }
