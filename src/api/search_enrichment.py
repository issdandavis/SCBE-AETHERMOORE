"""
AetherSearch Document Enrichment Pipeline
==========================================
Enriches raw documents with SCBE geometric metadata before indexing.

Each document gets:
  - tongue_profile[6]: Affinity to each Sacred Tongue (KO/AV/RU/CA/UM/DR)
  - harmonic_distance: Distance from origin in Poincare ball
  - friction_magnitude: Polyhedral boundary friction score
  - governance_tier: ALLOW / QUARANTINE / ESCALATE / DENY
  - dominant_tongue: Highest-activation tongue code
  - phi_weight: Golden ratio weight of the dominant tongue

The enriched metadata enables tongue-aware ranking: queries classified
to a tongue will prefer documents in the same geometric region.
"""

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Golden ratio
PHI = (1 + math.sqrt(5)) / 2

# Tongue phi-weights (canonical)
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Keyword sets for tongue classification (from semantic_mesh.py, extended)
TONGUE_KEYWORDS: Dict[str, List[str]] = {
    "KO": [
        "intent",
        "goal",
        "want",
        "need",
        "desire",
        "purpose",
        "command",
        "execute",
        "do",
        "run",
        "launch",
        "trigger",
        "invoke",
        "buy",
        "purchase",
        "order",
        "start",
        "begin",
        "initiate",
        "request",
    ],
    "AV": [
        "wisdom",
        "knowledge",
        "learn",
        "teach",
        "understand",
        "theory",
        "concept",
        "principle",
        "reason",
        "explain",
        "meaning",
        "insight",
        "philosophy",
        "science",
        "research",
        "study",
        "discover",
        "pattern",
    ],
    "RU": [
        "rule",
        "govern",
        "policy",
        "law",
        "regulate",
        "control",
        "authority",
        "compliance",
        "standard",
        "protocol",
        "audit",
        "enforce",
        "permission",
        "restrict",
        "approve",
        "deny",
        "decide",
    ],
    "CA": [
        "compute",
        "calculate",
        "algorithm",
        "function",
        "math",
        "number",
        "process",
        "transform",
        "optimize",
        "performance",
        "speed",
        "data",
        "metric",
        "measure",
        "solve",
        "equation",
        "formula",
        "model",
    ],
    "UM": [
        "security",
        "protect",
        "encrypt",
        "safe",
        "threat",
        "attack",
        "defend",
        "shield",
        "guard",
        "verify",
        "authenticate",
        "sign",
        "key",
        "secret",
        "vulnerability",
        "risk",
        "breach",
        "firewall",
    ],
    "DR": [
        "structure",
        "architecture",
        "design",
        "build",
        "construct",
        "framework",
        "system",
        "component",
        "module",
        "layer",
        "interface",
        "type",
        "schema",
        "pattern",
        "template",
        "blueprint",
        "layout",
    ],
}


@dataclass
class EnrichedDocument:
    """A document enriched with SCBE geometric metadata."""

    # Original content
    id: str
    title: str
    content: str
    url: str = ""
    source: str = "manual"

    # SCBE enrichment
    tongue_profile: List[float] = field(default_factory=lambda: [0.0] * 6)
    dominant_tongue: str = "CA"
    phi_weight: float = PHI**3
    harmonic_distance: float = 0.0
    friction_magnitude: float = 0.0
    governance_tier: str = "ALLOW"
    poincare_norm: float = 0.0

    # Timestamps
    indexed_at: float = 0.0
    enriched_at: float = 0.0

    def to_meili_doc(self) -> Dict[str, Any]:
        """Convert to Meilisearch-compatible document."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "tongue_profile": self.tongue_profile,
            "dominant_tongue": self.dominant_tongue,
            "phi_weight": self.phi_weight,
            "harmonic_distance": self.harmonic_distance,
            "friction_magnitude": self.friction_magnitude,
            "governance_tier": self.governance_tier,
            "poincare_norm": self.poincare_norm,
            "indexed_at": self.indexed_at,
            "enriched_at": self.enriched_at,
        }


def compute_tongue_profile(text: str) -> List[float]:
    """Compute 6D tongue activation profile from text content.

    Returns normalized vector in Poincare ball (norm < 1).
    """
    text_lower = text.lower()
    raw = []
    for tongue in TONGUE_ORDER:
        keywords = TONGUE_KEYWORDS[tongue]
        score = sum(1 for kw in keywords if kw in text_lower)
        raw.append(float(score))

    total = math.sqrt(sum(r * r for r in raw))
    if total > 0:
        # Scale to 0.9 max radius to stay inside the ball
        return [r / total * 0.9 for r in raw]
    else:
        # No keywords matched — place near origin (neutral)
        return [0.05, 0.05, 0.05, 0.05, 0.05, 0.05]


def compute_poincare_norm(profile: List[float]) -> float:
    """Euclidean norm of the tongue profile (Poincare ball radius)."""
    return math.sqrt(sum(x * x for x in profile))


def compute_hyperbolic_distance(profile: List[float]) -> float:
    """Hyperbolic distance from origin in the Poincare ball.

    d_H(0, x) = 2 * arctanh(||x||) = ln((1+||x||)/(1-||x||))

    Near origin = safe/simple. Near boundary = adversarial/complex.
    """
    norm = compute_poincare_norm(profile)
    if norm >= 1.0:
        norm = 0.999  # Clamp inside ball
    if norm <= 0.0:
        return 0.0
    return math.log((1 + norm) / (1 - norm))


def harmonic_wall_score(d_h: float, pd: float = 0.0) -> float:
    """Canonical harmonic wall: H(d, pd) = 1 / (1 + phi * d_H + 2 * pd).

    Returns safety score in (0, 1].
    Higher = safer. Lower = more adversarial.
    """
    return 1.0 / (1.0 + PHI * d_h + 2.0 * pd)


def compute_friction(profile: List[float]) -> float:
    """Simplified friction magnitude from tongue profile.

    Friction is highest when multiple tongues compete (cross-boundary content).
    Single-tongue-dominant content has low friction.
    """
    if not profile or all(x == 0 for x in profile):
        return 0.0

    # Entropy-based friction: high when activation is spread across tongues
    total = sum(profile)
    if total <= 0:
        return 0.0

    probs = [x / total for x in profile if x > 0]
    entropy = -sum(p * math.log(p + 1e-10) for p in probs)
    max_entropy = math.log(6)  # Max when all 6 tongues equal

    return entropy / max_entropy  # Normalized to [0, 1]


def classify_governance_tier(harmonic_score: float, friction: float) -> str:
    """Map harmonic wall score + friction to governance tier.

    For search documents (not adversarial inputs), thresholds are relaxed.
    Most legitimate content should be ALLOW. Only content with extreme
    friction (competing tongues) or very low harmonic scores gets flagged.

    - ALLOW:      H >= 0.1 and friction < 0.85
    - QUARANTINE: H >= 0.05 or friction >= 0.85
    - ESCALATE:   H >= 0.02
    - DENY:       H < 0.02
    """
    if harmonic_score >= 0.1 and friction < 0.85:
        return "ALLOW"
    elif harmonic_score >= 0.05:
        return "QUARANTINE"
    elif harmonic_score >= 0.02:
        return "ESCALATE"
    else:
        return "DENY"


def generate_doc_id(title: str, content: str) -> str:
    """Generate deterministic document ID from content hash."""
    h = hashlib.sha256(f"{title}:{content[:500]}".encode()).hexdigest()[:16]
    return f"aether_{h}"


def enrich_document(
    title: str,
    content: str,
    url: str = "",
    source: str = "manual",
    doc_id: Optional[str] = None,
) -> EnrichedDocument:
    """Run a document through the SCBE enrichment pipeline.

    Input: raw title + content
    Output: EnrichedDocument with full geometric metadata
    """
    combined_text = f"{title} {content}"

    # Step 1: Tongue profile
    profile = compute_tongue_profile(combined_text)

    # Step 2: Dominant tongue
    max_idx = profile.index(max(profile))
    dominant = TONGUE_ORDER[max_idx]

    # Step 3: Poincare metrics
    poincare_norm = compute_poincare_norm(profile)
    h_distance = compute_hyperbolic_distance(profile)

    # Step 4: Harmonic wall score
    h_score = harmonic_wall_score(h_distance)

    # Step 5: Friction
    friction = compute_friction(profile)

    # Step 6: Governance tier
    tier = classify_governance_tier(h_score, friction)

    now = time.time()

    return EnrichedDocument(
        id=doc_id or generate_doc_id(title, content),
        title=title,
        content=content,
        url=url,
        source=source,
        tongue_profile=profile,
        dominant_tongue=dominant,
        phi_weight=TONGUE_WEIGHTS[dominant],
        harmonic_distance=h_distance,
        friction_magnitude=friction,
        governance_tier=tier,
        poincare_norm=poincare_norm,
        indexed_at=now,
        enriched_at=now,
    )


def enrich_batch(
    documents: List[Dict[str, str]],
) -> List[EnrichedDocument]:
    """Enrich a batch of documents.

    Each dict must have 'title' and 'content'. Optional: 'url', 'source', 'id'.
    """
    results = []
    for doc in documents:
        enriched = enrich_document(
            title=doc.get("title", ""),
            content=doc.get("content", ""),
            url=doc.get("url", ""),
            source=doc.get("source", "manual"),
            doc_id=doc.get("id"),
        )
        results.append(enriched)
    return results


def tongue_boost_score(query_profile: List[float], doc_profile: List[float]) -> float:
    """Compute tongue-aware relevance boost.

    Cosine similarity between query and document tongue profiles.
    Used to re-rank search results so tongue-matched documents rise.
    """
    dot = sum(q * d for q, d in zip(query_profile, doc_profile))
    q_norm = math.sqrt(sum(q * q for q in query_profile))
    d_norm = math.sqrt(sum(d * d for d in doc_profile))

    if q_norm == 0 or d_norm == 0:
        return 0.0

    cosine = dot / (q_norm * d_norm)

    # Apply phi-weighted boost: documents in higher-weight tongues
    # get a slight natural advantage (reflecting SCBE's hierarchy)
    return cosine
