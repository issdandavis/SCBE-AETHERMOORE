"""Topology engine for curved-browser visualization.

Computes a Poincare disk layout from page analysis data.
Each link becomes a node positioned by semantic distance from the center page.
Trust zones (GREEN/YELLOW/RED) render as concentric rings.
Langues Metric cost gradient darkens toward the boundary.

Origin: Issac Davis concept ("mirrors are like browsers kinda" +
"the space is non-Euclidean and bending it reveals more truth than looking at it flat").
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TopologyNode:
    id: str
    label: str
    url: str
    x: float
    y: float
    radius: float
    zone: str
    risk_tier: str
    semantic_dist: float
    topics: list[str] = field(default_factory=list)


@dataclass
class TopologyData:
    center: dict
    nodes: list[dict]
    zone_rings: list[dict]
    langues_cost: list[dict]
    node_count: int


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
R_FIFTH = 1.5
ALPHA_EMBED = 0.8  # compression factor for tanh projection

# Zone boundaries in Poincare disk radius
ZONE_GREEN_MAX = 0.33
ZONE_YELLOW_MAX = 0.66

# Langues Metric weights (phi-scaled, 6 tongues)
LANGUES_WEIGHTS = [PHI ** i for i in range(6)]
LANGUES_BETA_BASE = 0.5

# Known safe domains (reuse from hyperlane concept)
GREEN_DOMAINS = {
    "github.com", "huggingface.co", "arxiv.org", "notion.so",
    "google.com", "stackoverflow.com", "wikipedia.org",
    "docs.python.org", "developer.mozilla.org", "npmjs.com",
}

YELLOW_DOMAINS = {
    "reddit.com", "twitter.com", "x.com", "medium.com",
    "dev.to", "linkedin.com", "youtube.com", "discord.com",
}


# ---------------------------------------------------------------------------
# Semantic distance (lightweight, no model needed)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Extract lowercase word tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def semantic_distance(page_text: str, link_text: str, link_url: str = "") -> float:
    """Compute semantic distance using Jaccard-like word overlap.

    Returns a value in [0, 1] where 0 = identical, 1 = no overlap.
    """
    page_tokens = _tokenize(page_text)
    link_tokens = _tokenize(link_text + " " + link_url)

    if not page_tokens or not link_tokens:
        return 1.0

    intersection = len(page_tokens & link_tokens)
    union = len(page_tokens | link_tokens)

    if union == 0:
        return 1.0

    jaccard = intersection / union
    return 1.0 - jaccard


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------

def classify_zone(url: str) -> str:
    """Classify a URL into GREEN/YELLOW/RED trust zone."""
    try:
        # Extract domain from URL
        domain = url.split("//")[-1].split("/")[0].split(":")[0]
        # Strip www prefix
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return "RED"

    if domain in GREEN_DOMAINS:
        return "GREEN"
    if domain in YELLOW_DOMAINS:
        return "YELLOW"

    # Check if it's a subdomain of a known domain
    for green in GREEN_DOMAINS:
        if domain.endswith("." + green):
            return "GREEN"
    for yellow in YELLOW_DOMAINS:
        if domain.endswith("." + yellow):
            return "YELLOW"

    return "RED"


def zone_to_risk(zone: str) -> str:
    if zone == "GREEN":
        return "low"
    if zone == "YELLOW":
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Poincare disk projection
# ---------------------------------------------------------------------------

def project_to_disk(distance: float, angle: float) -> tuple[float, float]:
    """Map semantic distance to Poincare ball radius, then to (x, y).

    Uses tanh(alpha * d) which maps [0, inf) -> [0, 1).
    """
    r = math.tanh(ALPHA_EMBED * distance)
    # Clamp to stay strictly inside disk
    r = min(r, 0.98)
    x = r * math.cos(angle)
    y = r * math.sin(angle)
    return x, y


# ---------------------------------------------------------------------------
# Angular layout with topic clustering
# ---------------------------------------------------------------------------

def angular_layout(links: list[dict], topics: list[str]) -> list[float]:
    """Distribute link angles around the circle.

    Links matching similar topics cluster together.
    """
    n = len(links)
    if n == 0:
        return []

    # Base: uniform distribution
    angles = [2 * math.pi * i / n for i in range(n)]

    if not topics:
        return angles

    # Topic-based offset: links matching page topics get pulled toward sector 0
    topic_set = set(t.lower() for t in topics)

    for i, link in enumerate(links):
        link_text = (link.get("text", "") + " " + link.get("href", "")).lower()
        matches = sum(1 for t in topic_set if t in link_text)
        if matches > 0:
            # Pull toward the "topic sector" (first quadrant)
            pull = 0.3 * matches / max(len(topic_set), 1)
            angles[i] = angles[i] * (1 - pull)

    return angles


# ---------------------------------------------------------------------------
# Langues Metric cost gradient
# ---------------------------------------------------------------------------

def compute_langues_cost_gradient(n_samples: int = 20) -> list[dict]:
    """Compute the Langues Metric cost at sampled radii for gradient rendering.

    L(d) = sum(w_l * exp(beta_l * d)) for l=1..6
    """
    stops = []
    for i in range(n_samples):
        r = i / (n_samples - 1)  # 0 to 1
        # Convert disk radius to hyperbolic distance
        # d_H ~ 2 * arctanh(r) for Poincare disk
        clamped_r = min(r, 0.99)
        d_h = 2 * math.atanh(clamped_r) if clamped_r > 0 else 0

        # Langues metric cost
        cost = sum(
            LANGUES_WEIGHTS[l] * math.exp(LANGUES_BETA_BASE * PHI ** (l * 0.5) * min(d_h, 10))
            for l in range(6)
        )

        stops.append({
            "radius": round(r, 3),
            "hyperbolic_distance": round(d_h, 4),
            "cost": round(cost, 4),
        })

    return stops


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_page_topology(
    url: str,
    title: str,
    text: str,
    links: list[dict],
    headings: list[dict] | None = None,
    topics: list[str] | None = None,
    risk_tier: str = "low",
    max_nodes: int = 40,
) -> dict:
    """Compute the full Poincare disk topology for a page.

    Returns a TopologyData dict ready for JSON serialization.
    """
    headings = headings or []
    topics = topics or []

    # Build page text corpus for semantic comparison
    page_corpus = " ".join([
        title,
        text[:2000],  # First 2000 chars of body
        " ".join(h.get("text", "") for h in headings),
    ])

    # Limit links
    links_trimmed = links[:max_nodes]

    # Compute angles
    angles = angular_layout(links_trimmed, topics)

    # Build center node
    center = TopologyNode(
        id=hashlib.md5(url.encode()).hexdigest()[:12],
        label=title[:40] if title else "Current Page",
        url=url,
        x=0.0,
        y=0.0,
        radius=0.0,
        zone="GREEN",
        risk_tier="low",
        semantic_dist=0.0,
        topics=topics[:5],
    )

    # Build link nodes
    nodes = []
    for i, link in enumerate(links_trimmed):
        link_text = link.get("text", "")
        link_url = link.get("href", link.get("url", ""))

        if not link_url:
            continue

        dist = semantic_distance(page_corpus, link_text, link_url)
        zone = classify_zone(link_url)
        angle = angles[i] if i < len(angles) else 2 * math.pi * i / max(len(links_trimmed), 1)

        x, y = project_to_disk(dist, angle)

        node = TopologyNode(
            id=hashlib.md5(link_url.encode()).hexdigest()[:12],
            label=link_text[:30] if link_text else link_url.split("/")[-1][:30],
            url=link_url,
            x=round(x, 6),
            y=round(y, 6),
            radius=round(math.sqrt(x * x + y * y), 6),
            zone=zone,
            risk_tier=zone_to_risk(zone),
            semantic_dist=round(dist, 4),
            topics=[t for t in topics if t.lower() in (link_text + " " + link_url).lower()][:3],
        )
        nodes.append(node)

    # Zone rings
    zone_rings = [
        {"zone": "GREEN", "inner_radius": 0, "outer_radius": ZONE_GREEN_MAX, "color": "#3fb950"},
        {"zone": "YELLOW", "inner_radius": ZONE_GREEN_MAX, "outer_radius": ZONE_YELLOW_MAX, "color": "#d29922"},
        {"zone": "RED", "inner_radius": ZONE_YELLOW_MAX, "outer_radius": 1.0, "color": "#f85149"},
    ]

    # Langues cost gradient
    langues_cost = compute_langues_cost_gradient()

    topology = TopologyData(
        center=asdict(center),
        nodes=[asdict(n) for n in nodes],
        zone_rings=zone_rings,
        langues_cost=langues_cost,
        node_count=len(nodes),
    )

    return asdict(topology)
