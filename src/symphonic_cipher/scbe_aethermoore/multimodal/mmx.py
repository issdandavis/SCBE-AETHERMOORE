"""
@file mmx.py
@module multimodal/mmx
@layer Layer 9.5 — Cross-Modal Coherence Tensor
@component Multimodality Matrix (MMX)
@version 1.0.0

Multimodality Matrix (MMX)
==========================

Computes a cross-modal alignment tensor from K modality feature vectors,
then derives three governance-facing scalars:

  coherence  — mean pairwise cosine similarity         ∈ [0, 1]
  conflict   — fraction of pairs below agreement floor  ∈ [0, 1]
  drift      — max absolute delta vs previous snapshot  ∈ [0, ∞)

Integration:
  • Pipeline inserts MMX between L10 (spin coherence) and L12 (harmonic scaling).
  • Governance rules at L13:
      conflict > 0.35                 → override to QUARANTINE
      conflict > 0.60 or min(w) < 0.10 → override to DENY
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# =============================================================================
# TYPES
# =============================================================================

@dataclass(frozen=True)
class MMXResult:
    """Output of compute_mmx()."""
    alignment: List[List[float]]     # K×K cosine-similarity matrix
    weights: List[float]             # per-modality reliability weights
    coherence: float                 # mean pairwise cosine similarity
    conflict: float                  # fraction of pairs below agreement floor
    drift: float                     # max delta vs previous snapshot
    modality_labels: List[str]       # names of each modality


# =============================================================================
# HELPERS
# =============================================================================

def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 on degenerate input."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _reliability_weight(vec: Sequence[float], *, eps: float = 1e-8) -> float:
    """
    Reliability weight for a single modality feature vector.

    w = 1 - 1/(1 + ||v||)

    Maps: zero-vector → 0, large-norm → ~1.
    """
    norm = math.sqrt(sum(v * v for v in vec))
    return 1.0 - 1.0 / (1.0 + norm + eps)


# =============================================================================
# CORE
# =============================================================================

def compute_mmx(
    features: Dict[str, Sequence[float]],
    *,
    agreement_floor: float = 0.5,
    prev_alignment: Optional[List[List[float]]] = None,
) -> MMXResult:
    """
    Compute the Multimodality Matrix for a set of modality feature vectors.

    Parameters
    ----------
    features : dict[str, Sequence[float]]
        Mapping from modality label to its feature vector.
        All vectors must have the same dimensionality.
        At least 2 modalities required.
    agreement_floor : float
        Cosine similarity threshold below which a pair is in "conflict".
    prev_alignment : list[list[float]] | None
        Previous alignment matrix for drift computation.

    Returns
    -------
    MMXResult
        alignment  — K×K cosine similarity matrix
        weights    — per-modality reliability weights
        coherence  — mean pairwise cosine similarity ∈ [0,1]
        conflict   — fraction of conflicting pairs ∈ [0,1]
        drift      — max |delta| vs previous alignment ∈ [0,∞)
        modality_labels — ordered list of modality names

    Raises
    ------
    ValueError
        If fewer than 2 modalities, or vectors have mismatched lengths.
    """
    labels = sorted(features.keys())
    K = len(labels)

    if K < 2:
        raise ValueError(f"MMX requires ≥2 modalities, got {K}")

    vecs = [list(features[lbl]) for lbl in labels]

    # Validate dimension parity
    dim = len(vecs[0])
    for i, v in enumerate(vecs):
        if len(v) != dim:
            raise ValueError(
                f"Dimension mismatch: modality '{labels[0]}' has dim={dim}, "
                f"but '{labels[i]}' has dim={len(v)}"
            )

    # ---- Alignment matrix (K×K) ----
    alignment = [[0.0] * K for _ in range(K)]
    for i in range(K):
        alignment[i][i] = 1.0
        for j in range(i + 1, K):
            sim = _cosine_similarity(vecs[i], vecs[j])
            alignment[i][j] = sim
            alignment[j][i] = sim

    # ---- Reliability weights ----
    weights = [_reliability_weight(v) for v in vecs]

    # ---- Governance scalars ----
    pair_sims: List[float] = []
    conflict_count = 0
    for i in range(K):
        for j in range(i + 1, K):
            sim = alignment[i][j]
            pair_sims.append(sim)
            if sim < agreement_floor:
                conflict_count += 1

    n_pairs = len(pair_sims)
    coherence = sum(pair_sims) / n_pairs if n_pairs > 0 else 1.0
    coherence = max(0.0, min(1.0, coherence))

    conflict = conflict_count / n_pairs if n_pairs > 0 else 0.0

    # ---- Drift ----
    drift = 0.0
    if prev_alignment is not None and len(prev_alignment) == K:
        for i in range(K):
            for j in range(K):
                if j < len(prev_alignment[i]):
                    delta = abs(alignment[i][j] - prev_alignment[i][j])
                    drift = max(drift, delta)

    return MMXResult(
        alignment=alignment,
        weights=weights,
        coherence=coherence,
        conflict=conflict,
        drift=drift,
        modality_labels=labels,
    )
