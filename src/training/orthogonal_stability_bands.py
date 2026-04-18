"""
Orthogonal Stability Bands (OSB) — Dynamic In-Built RAG Training
================================================================

Fixed reference anchors in the Poincaré ball, orthogonal to the main
training gradient. The model learns:

  1. Band Proximity Detection  — "something is here" (geometry-triggered)
  2. Query Formulation         — "what do I need from this?" (learned)
  3. Retrieval Integration     — "how does this change my state?" (trained)

Core paradox: "have to query to know, but have to see to query."
The visibility threshold ε_see is learned; the content is fetched live.

This makes RAG a trained behavior, not a bolted-on inference-time tool.
The spiral training loop (see: iterative_residual_trainer.py) naturally
tightens around correct query-trigger thresholds each epoch.

@layer L3 (Weighted Transform), L11 (Triadic Temporal), L12 (Harmonic Wall)
@axiom A2 Locality  — bands have bounded spatial influence (radius ε_k)
@axiom A4 Symmetry  — d_H(x, r_k) is gauge-invariant in B^n
@axiom A5 Composition — OSB pipeline composes with coupling operator A_6D

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

# Six Sacred Tongue phi-weights (KO … DR)
TONGUE_WEIGHTS = np.array([1.0, PHI, PHI**2, PHI**3, PHI**4, PHI**5])
TONGUE_LABELS = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Ball dimension (Sacred Tongues = 6D)
BALL_DIM = 6

# Default visibility and query thresholds
DEFAULT_EPSILON_SEE = 1.5  # d_H distance at which band becomes "visible"
DEFAULT_EPSILON_QUERY = 0.8  # d_H distance at which query fires


# ---------------------------------------------------------------------------
# Poincaré Ball Metric (canonical, matches Layer 5)
# ---------------------------------------------------------------------------


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    """
    d_H(u, v) = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

    A4: Symmetry — d_H(u,v) = d_H(v,u).
    Numerically stable for u,v near boundary.
    """
    uu = np.dot(u, u)
    vv = np.dot(v, v)
    uv_sq = np.dot(u - v, u - v)
    denom = (1.0 - uu) * (1.0 - vv)
    denom = max(denom, eps)
    arg = 1.0 + 2.0 * uv_sq / denom
    arg = max(arg, 1.0 + eps)  # arccosh domain guard
    return math.acosh(arg)


def poincare_project(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Project x into open Poincaré ball (||x|| < 1)."""
    norm = np.linalg.norm(x)
    if norm >= 1.0:
        x = x / (norm + eps) * (1.0 - eps)
    return x


# ---------------------------------------------------------------------------
# Non-Fixed Poincaré Sampler (prerequisite for OSB training)
# ---------------------------------------------------------------------------


def sample_poincare_point(
    dim: int = BALL_DIM,
    radial_alpha: float = 2.0,
    radial_beta: float = 5.0,
    max_radius: float = 0.95,
) -> np.ndarray:
    """
    Sample a point in B^dim with Beta-distributed radius.

    Beta(2,5) weights toward center but covers full ball.
    For adversarial-regime coverage, use Beta(5,2) (weights toward boundary).

    This is the non-fixed initialization required for correct d_H learning:
    training only at origin collapses d_H to a monotonic transform of ||v||.
    """
    r = np.random.beta(radial_alpha, radial_beta) * max_radius
    direction = np.random.randn(dim)
    direction /= np.linalg.norm(direction) + 1e-12
    return poincare_project(r * direction)


def sample_training_pair(
    dim: int = BALL_DIM,
    perturbation_scale: float = 0.3,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Sample (u, v, d_H_true) triple with non-fixed u.

    Returns:
        u:         starting position (non-fixed, sampled from B^dim)
        v:         perturbed endpoint
        d_H_true:  ground-truth hyperbolic distance (label for training)
    """
    u = sample_poincare_point(dim)
    # Perturb in Euclidean space, then project back
    delta = np.random.randn(dim) * perturbation_scale
    v = poincare_project(u + delta)
    d_H_true = hyperbolic_distance(u, v)
    return u, v, d_H_true


# ---------------------------------------------------------------------------
# Orthogonal Stability Band
# ---------------------------------------------------------------------------


@dataclass
class OrthogonalStabilityBand:
    """
    A fixed reference anchor in B^n with learned visibility/query thresholds.

    Attributes:
        anchor      : r_k ∈ B^n — fixed position of this reference
        label       : human-readable name (e.g. "Ratcliffe2006", "SPEC.md")
        tongue      : Sacred Tongue this band is classified under
        epsilon_see : visibility radius — model "sees" band when d_H(x,r_k) < ε_see
        epsilon_query: query-fire radius — query fires when d_H(x,r_k) < ε_query
        retriever   : callable(query: str) -> str — fetches actual content
        content_hash: fingerprint of last retrieved content (for cache check)
    """

    anchor: np.ndarray
    label: str
    tongue: str = "DR"  # DR = highest governance weight
    epsilon_see: float = DEFAULT_EPSILON_SEE
    epsilon_query: float = DEFAULT_EPSILON_QUERY
    retriever: Optional[Callable[[str], str]] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure anchor is inside the ball
        self.anchor = poincare_project(np.asarray(self.anchor, dtype=float))

    def distance_from(self, x: np.ndarray) -> float:
        """d_H(x, anchor) — how far current state is from this reference."""
        return hyperbolic_distance(x, self.anchor)

    def is_visible(self, x: np.ndarray) -> bool:
        """True if x is within visibility radius — model can 'see' this band."""
        return self.distance_from(x) < self.epsilon_see

    def should_query(self, x: np.ndarray) -> bool:
        """True if x is within query-fire radius — retrieval should trigger."""
        return self.distance_from(x) < self.epsilon_query

    def retrieve(self, query: str) -> Optional[str]:
        """Execute retrieval. Returns None if no retriever configured."""
        if self.retriever is None:
            return None
        return self.retriever(query)

    def tongue_weight(self) -> float:
        """Phi-weight of this band's governing tongue."""
        idx = TONGUE_LABELS.index(self.tongue) if self.tongue in TONGUE_LABELS else 5
        return TONGUE_WEIGHTS[idx]


# ---------------------------------------------------------------------------
# Band Proximity Detector
# ---------------------------------------------------------------------------


class BandProximityDetector:
    """
    Scans all registered OSBs for a given state x.

    Returns:
        visible bands  — model "feels" their presence, no content yet
        query bands    — retrieval should fire for these
    """

    def __init__(self, bands: List[OrthogonalStabilityBand]):
        self.bands = bands

    def scan(self, x: np.ndarray) -> Dict[str, List[OrthogonalStabilityBand]]:
        """
        Scan all bands for state x.

        Returns dict with keys:
            'visible'  — bands within ε_see (model detects them)
            'query'    — bands within ε_query (retrieval should fire)
        """
        visible, query = [], []
        for band in self.bands:
            d = band.distance_from(x)
            if d < band.epsilon_see:
                visible.append(band)
            if d < band.epsilon_query:
                query.append(band)
        # Sort by distance (closest first = highest priority)
        visible.sort(key=lambda b: b.distance_from(x))
        query.sort(key=lambda b: b.distance_from(x))
        return {"visible": visible, "query": query}

    def proximity_vector(self, x: np.ndarray) -> np.ndarray:
        """
        Returns a vector of d_H distances to each band.
        Useful as a feature vector for the query formulator.
        Shape: (len(bands),)
        """
        return np.array([b.distance_from(x) for b in self.bands])


# ---------------------------------------------------------------------------
# Query Formulator
# ---------------------------------------------------------------------------


class QueryFormulator:
    """
    Maps (current_state, band_signature) → query string.

    The key insight: the model learns WHAT to ask based on WHERE it is,
    not from memorized content. The band's label and tongue act as a
    "signature" — enough to know THAT something is there and formulate
    a targeted question.

    Training pairs format:
        input:  (x_near_band, band.label, band.tongue, d_H_to_band)
        output: query_string
    """

    def __init__(self, formulate_fn: Optional[Callable] = None):
        """
        formulate_fn: callable(state, band) -> str
        If None, uses geometric default (tongue-weighted directional query).
        """
        self._formulate = formulate_fn or self._geometric_default

    def formulate(self, x: np.ndarray, band: OrthogonalStabilityBand) -> str:
        return self._formulate(x, band)

    def _geometric_default(self, x: np.ndarray, band: OrthogonalStabilityBand) -> str:
        """
        Geometric default: query based on direction from x toward anchor.
        Direction in B^n indicates which aspect of the reference is relevant.
        """
        d = band.distance_from(x)
        direction = band.anchor - x
        norm = np.linalg.norm(direction)
        if norm > 1e-8:
            direction /= norm

        # Tongue-weighted dominant axis
        weighted = direction * TONGUE_WEIGHTS[: len(direction)]
        dominant_idx = int(np.argmax(np.abs(weighted)))
        dominant_tongue = TONGUE_LABELS[dominant_idx] if dominant_idx < 6 else "DR"

        return (
            f"[OSB:{band.label}] [{band.tongue}→{dominant_tongue}] "
            f"d_H={d:.3f} | "
            f"What is the {dominant_tongue}-axis content of {band.label}?"
        )


# ---------------------------------------------------------------------------
# Retrieval Integration Operator
# ---------------------------------------------------------------------------


def integrate_retrieval(
    x: np.ndarray,
    retrieved_content: str,
    band: OrthogonalStabilityBand,
    z_gov: np.ndarray,
    integration_strength: float = 0.3,
) -> np.ndarray:
    """
    Integrate retrieved content into current state x.

    Uses the same coupling pattern as A_6D (flight/governance operator):
        x_new = x * (1 - α) + α * content_projection * z_gov_modulation

    The content is projected into B^n via a tongue-weighted hash encoding.
    This keeps integration inside the Poincaré ball (A1: Unitarity).

    integration_strength α: how much the retrieval shifts current state.
    High α = strong update (near-anchor retrieval).
    Low α = gentle nudge (far-from-anchor, peripheral visibility).
    """
    dim = len(x)

    # Project retrieved content to B^n via deterministic hash encoding
    content_vec = _content_to_vector(retrieved_content, dim)

    # Scale by band's tongue weight (DR-band content has highest influence)
    tongue_scale = band.tongue_weight() / TONGUE_WEIGHTS[-1]  # normalize to DR=1.0

    # Distance-weighted integration (closer = stronger update)
    d = band.distance_from(x)
    distance_weight = math.exp(-d)  # exponential decay

    alpha = integration_strength * tongue_scale * distance_weight

    # Governance modulation: z_gov dampens if governance score is low
    gov_score = float(np.mean(z_gov)) if len(z_gov) > 0 else 1.0
    alpha *= gov_score

    x_new = (1.0 - alpha) * x + alpha * content_vec
    return poincare_project(x_new)


def _content_to_vector(content: str, dim: int) -> np.ndarray:
    """
    Deterministic projection of retrieved content string into B^dim.
    Uses character-level hashing — not semantic, but reproducible.
    Replace with a real embedding in production.
    """
    vec = np.zeros(dim)
    for i, ch in enumerate(content):
        vec[i % dim] += math.sin(ord(ch) * (i + 1) * 0.1)
    norm = np.linalg.norm(vec)
    if norm > 1e-8:
        vec /= norm
    return poincare_project(vec * 0.5)  # keep well inside ball


# ---------------------------------------------------------------------------
# Full OSB Pipeline (detector + formulator + retrieve + integrate)
# ---------------------------------------------------------------------------


@dataclass
class OSBPipelineResult:
    """Result of one OSB pipeline pass."""

    x_in: np.ndarray
    x_out: np.ndarray
    visible_bands: List[str]
    queried_bands: List[str]
    queries_fired: List[str]
    retrieved_content: List[str]
    d_H_changes: List[float]  # d_H to each queried band before/after
    governance_score: float


class OSBPipeline:
    """
    Full Orthogonal Stability Band pipeline.

    Integrates:
        BandProximityDetector → QueryFormulator → Retrieval → Integration

    The model learns this full chain during training. At inference,
    it executes the same chain — retrieval-augmented, geometry-triggered,
    governance-modulated.
    """

    def __init__(
        self,
        bands: List[OrthogonalStabilityBand],
        formulator: Optional[QueryFormulator] = None,
        z_gov: Optional[np.ndarray] = None,
    ):
        self.detector = BandProximityDetector(bands)
        self.formulator = formulator or QueryFormulator()
        self.z_gov = z_gov if z_gov is not None else np.ones(BALL_DIM)

    def run(self, x: np.ndarray) -> OSBPipelineResult:
        """Execute one full OSB pipeline pass for state x."""
        scan = self.detector.scan(x)
        visible_names = [b.label for b in scan["visible"]]
        queried_names = [b.label for b in scan["query"]]

        queries_fired = []
        retrieved = []
        d_H_changes = []
        x_current = x.copy()

        # Harmonic wall governance score at current position
        d_origin = hyperbolic_distance(x, np.zeros(len(x)))
        pd = 0.0  # perturbation density (wired from L11 in full pipeline)
        H_score = 1.0 / (1.0 + PHI * d_origin + 2.0 * pd)

        for band in scan["query"]:
            d_before = band.distance_from(x_current)
            query = self.formulator.formulate(x_current, band)
            queries_fired.append(query)

            content = band.retrieve(query) or f"[stub:{band.label}]"
            retrieved.append(content)

            x_current = integrate_retrieval(x_current, content, band, self.z_gov)
            d_after = band.distance_from(x_current)
            d_H_changes.append(d_before - d_after)  # positive = moved closer

        return OSBPipelineResult(
            x_in=x,
            x_out=x_current,
            visible_bands=visible_names,
            queried_bands=queried_names,
            queries_fired=queries_fired,
            retrieved_content=retrieved,
            d_H_changes=d_H_changes,
            governance_score=H_score,
        )


# ---------------------------------------------------------------------------
# SFT Training Pair Generator
# ---------------------------------------------------------------------------


def generate_osb_training_pairs(
    bands: List[OrthogonalStabilityBand],
    n_pairs: int = 200,
    dim: int = BALL_DIM,
) -> List[Dict[str, Any]]:
    """
    Generate SFT training pairs for OSB learning.

    Each pair teaches the model:
        1. Given position x, which bands are visible?
        2. Given a visible band, what query to formulate?
        3. Given retrieved content, how to integrate?

    Upsamples near-boundary pairs (||x|| > 0.7) 3:1 over center pairs
    to ensure the adversarial regime is well-covered.
    """
    pipeline = OSBPipeline(bands)
    pairs = []

    # 75% near-boundary, 25% center — adversarial regime matters most
    n_boundary = int(n_pairs * 0.75)
    n_center = n_pairs - n_boundary

    configs = [{"radial_alpha": 5.0, "radial_beta": 2.0}] * n_boundary + [  # near boundary
        {"radial_alpha": 2.0, "radial_beta": 8.0}
    ] * n_center  # near center

    for cfg in configs:
        x = sample_poincare_point(dim, **cfg)
        result = pipeline.run(x)

        d_vec = pipeline.detector.proximity_vector(x)
        visible_str = ", ".join(result.visible_bands) or "none"
        query_str = "; ".join(result.queries_fired) or "no query triggered"

        pairs.append(
            {
                "x": x.tolist(),
                "norm_x": float(np.linalg.norm(x)),
                "d_origin": float(hyperbolic_distance(x, np.zeros(dim))),
                "proximity_vector": d_vec.tolist(),
                "visible_bands": result.visible_bands,
                "queried_bands": result.queried_bands,
                "queries_fired": result.queries_fired,
                "governance_score": result.governance_score,
                "d_H_changes": result.d_H_changes,
                "sft_prompt": (
                    f"State vector x has ||x||={np.linalg.norm(x):.4f} "
                    f"(d_H from origin: {result.governance_score:.4f}). "
                    f"Visible OSBs: {visible_str}. "
                    f"What queries should fire?"
                ),
                "sft_response": query_str,
            }
        )

    return pairs


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Define reference anchors (real use: wire to your doc store / Notion / SPEC.md)
    bands = [
        OrthogonalStabilityBand(
            anchor=np.array([0.3, 0.0, 0.0, 0.0, 0.0, 0.0]),
            label="Theorem4_HyperbolicMetric",
            tongue="RU",
            epsilon_see=1.8,
            epsilon_query=0.9,
            retriever=lambda q: "d_H(u,v)=arccosh(1+2||u-v||²/((1-||u||²)(1-||v||²)))",
        ),
        OrthogonalStabilityBand(
            anchor=np.array([0.0, 0.4, 0.0, 0.0, 0.0, 0.0]),
            label="SPEC_md_Layer12",
            tongue="UM",
            epsilon_see=1.5,
            epsilon_query=0.7,
            retriever=lambda q: "H(d,pd) = 1/(1+phi*d_H+2*pd); ALLOW if score > 0.5",
        ),
        OrthogonalStabilityBand(
            anchor=np.array([0.0, 0.0, 0.0, 0.5, 0.0, 0.0]),
            label="Ratcliffe2006_Hyperbolic",
            tongue="DR",
            epsilon_see=2.0,
            epsilon_query=1.0,
            retriever=lambda q: "Poincaré ball model: constant curvature -1; geodesics are arcs",
        ),
        OrthogonalStabilityBand(
            anchor=np.array([0.0, 0.0, 0.5, 0.0, 0.0, 0.0]),
            label="DTN_RFC5050",
            tongue="CA",
            epsilon_see=1.6,
            epsilon_query=0.8,
            retriever=lambda q: "Bundle custody chain; store-and-forward; contact windows",
        ),
    ]

    # Run one pipeline pass
    x_test = sample_poincare_point(radial_alpha=5.0, radial_beta=2.0)  # near boundary
    pipeline = OSBPipeline(bands)
    result = pipeline.run(x_test)

    print(f"x norm:          {np.linalg.norm(x_test):.4f}")
    print(f"d_H from origin: {hyperbolic_distance(x_test, np.zeros(6)):.4f}")
    print(f"Governance score:{result.governance_score:.4f}")
    print(f"Visible bands:   {result.visible_bands}")
    print(f"Queried bands:   {result.queried_bands}")
    print(f"Queries fired:   {result.queries_fired}")
    print(f"d_H changes:     {result.d_H_changes}")

    # Generate a small batch of SFT pairs
    pairs = generate_osb_training_pairs(bands, n_pairs=10)
    print(f"\nGenerated {len(pairs)} SFT pairs")
    print("Sample pair prompt:", pairs[0]["sft_prompt"][:120])
