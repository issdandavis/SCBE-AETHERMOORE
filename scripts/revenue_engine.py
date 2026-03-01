#!/usr/bin/env python3
"""Revenue Engine — Generate, govern, and publish monetizable content.

One command to run the full supply chain:
    generate content → governance scan → queue for publishing → track revenue

Usage:
    python scripts/revenue_engine.py generate     # Generate content batch
    python scripts/revenue_engine.py publish       # Publish queued content
    python scripts/revenue_engine.py status        # Show pipeline status
    python scripts/revenue_engine.py products      # List/update store products
    python scripts/revenue_engine.py full          # Full pipeline (generate + publish)

Revenue streams wired:
    1. Social content → audience → funnel to products
    2. Medium articles → thought leadership → consulting leads
    3. Gumroad/Shopify products → direct sales
    4. GitHub → open source reputation → enterprise contracts
    5. HuggingFace → model/dataset visibility → licensing

@layer Layer 13 (governance), Layer 14 (telemetry)
@component Revenue.Engine
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ==========================================================================
# Content Templates — what to post and where
# ==========================================================================

class ContentType(str, Enum):
    SOCIAL_SHORT = "social_short"       # Twitter/Bluesky/Mastodon (280-500 chars)
    SOCIAL_LONG = "social_long"         # LinkedIn (3000 chars)
    BLOG_POST = "blog_post"             # Medium/WordPress
    GITHUB_UPDATE = "github_update"     # Release notes, issue updates
    PRODUCT_UPDATE = "product_update"   # Gumroad/Shopify descriptions
    DATASET_CARD = "dataset_card"       # HuggingFace model/dataset cards


@dataclass
class ContentPiece:
    """A single piece of generated content."""
    content_type: ContentType
    title: str
    body: str
    tags: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    link: str = ""
    governance_score: float = 0.0
    governance_passed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==========================================================================
# Content Generation — templates that produce real posts
# ==========================================================================

# ==========================================================================
# Topic Seeds — one topic, multiple platform-specific variations
# ==========================================================================
# Hub-and-spokes: each topic generates unique content per platform.
# Same angle, different voice. Never identical on two platforms.

TOPIC_SEEDS = [
    {
        "topic": "ai_governance",
        "hub_title": "The Missing Layer in AI Safety",
        "tags_base": ["AISafety", "AIGovernance"],
        "link": "https://github.com/issdandavis/SCBE-AETHERMOORE",
        "spokes": {
            "twitter": {
                "body": "90% of AI governance is checkbox compliance theater.\n\nReal governance needs math, not meetings.\n\nWe built a 14-layer pipeline where adversarial behavior costs exponentially more. Rogue agents can't even tell they're being governed.\n\n1,700+ tests. Patent pending. Open source.",
                "tags": ["AISafety", "AIGovernance", "OpenSource"],
            },
            "bluesky": {
                "body": "Building a 14-layer security pipeline for AI agents. Each layer adds exponential cost to adversarial behavior using hyperbolic geometry.\n\nThe key insight: safe AI agents sit near the center of a Poincare ball. Rogue agents drift to the edge where everything costs exponentially more.",
                "tags": ["AISafety", "MachineLearning", "OpenSource"],
            },
            "mastodon": {
                "body": "Hot take: your AI fleet is one prompt injection away from chaos.\n\nWe use hyperbolic geometry to make attacks cost exponentially more. Safe agents live near the center of a Poincare ball. Drift to the edge? Everything gets expensive.\n\nMath > vibes for AI safety.",
                "tags": ["AISafety", "InfoSec", "FOSS"],
            },
            "linkedin": {
                "body": "Most AI safety approaches focus on alignment during training. But what happens after deployment?\n\nSCBE-AETHERMOORE addresses the gap between training-time alignment and runtime governance with a 14-layer mathematical pipeline:\n\n- Layers 1-4: Context capture and embedding\n- Layer 5: Hyperbolic distance measurement (Poincare ball)\n- Layers 6-10: Behavioral analysis and spectral coherence\n- Layer 11: Temporal trajectory binding\n- Layer 12: Harmonic cost scaling (H(d,R) = R^(d^2))\n- Layer 13: Risk decision (ALLOW/QUARANTINE/ESCALATE/DENY)\n- Layer 14: Audit telemetry\n\nThe core insight: adversarial intent costs exponentially more the further it drifts from safe operation. This makes attacks computationally infeasible, not just probabilistically unlikely.\n\n1,700+ tests. Post-quantum cryptography. Patent pending. Open source.\n\n#AISafety #AIGovernance #Cybersecurity #StartupLife",
                "tags": ["AISafety", "AIGovernance", "Cybersecurity", "StartupLife"],
            },
            "medium": {
                "body": "# Why Your AI Fleet Needs Mathematical Governance\n\nMost AI safety systems work like bouncers at a club. SCBE works like physics.\n\n## The Hyperbolic Geometry Approach\n\nImagine a circle. Safe agents live near the center. As behavior drifts toward adversarial, agents move toward the edge. In hyperbolic geometry, distances near the edge grow exponentially.\n\n- **Small deviations** (honest mistakes) cost almost nothing\n- **Medium deviations** (edge cases) cost moderately more\n- **Large deviations** (adversarial intent) cost exponentially more\n\nThe formula: `H(d,R) = R^(d^2)`\n\nThis isn't a policy decision. It's math.\n\n## What This Means for Your AI Operations\n\n1. **Which agents are behaving normally?** (Trust score tracking)\n2. **Which are drifting?** (Behavioral authorization via Hopfield energy)\n3. **Which have gone rogue?** (Self-excluding swarm consensus)\n\nSCBE answers all three without central coordination. Each agent carries its own trust math.\n\n## The Stack\n\n- **14-layer security pipeline** (cheap checks first, expensive crypto last)\n- **Post-quantum cryptography** (ML-KEM-768, ML-DSA-65)\n- **Fail-to-noise property** (wrong parameters = noise, not errors)\n- **1,700+ tests** across TypeScript and Python\n\nOpen source: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)\n\n---\n\n*Isaac Davis builds mathematical governance for AI fleets. Patent pending.*",
                "tags": ["ai-safety", "machine-learning", "cybersecurity", "open-source"],
            },
        },
    },
    {
        "topic": "post_quantum",
        "hub_title": "Your AI Fleet's Encryption Has an Expiration Date",
        "tags_base": ["PostQuantum", "Cryptography"],
        "link": "https://github.com/issdandavis/SCBE-AETHERMOORE",
        "spokes": {
            "twitter": {
                "body": "Your AI fleet's encryption will break when quantum computers arrive.\n\nSCBE uses ML-KEM-768 and ML-DSA-65 (NIST post-quantum standards) + chaos-based spectral diffusion.\n\nWrong context = noise output, not error messages. Attackers can't even tell they're close.",
                "tags": ["PostQuantum", "CyberSecurity", "NIST"],
            },
            "bluesky": {
                "body": "The encryption protecting your AI fleet has a timer on it. Quantum computers will crack RSA and ECC.\n\nWe already migrated to post-quantum: ML-KEM-768 for key exchange, ML-DSA-65 for signatures. Both NIST-approved.\n\nPlus our fail-to-noise property: wrong key = random garbage. Not errors. Random.",
                "tags": ["PostQuantum", "Cryptography", "InfoSec"],
            },
            "mastodon": {
                "body": "Migrated our entire crypto stack to post-quantum.\n\nML-KEM-768 (key encapsulation) + ML-DSA-65 (digital signatures) + chaos diffusion.\n\nThe fail-to-noise property means wrong decryption produces random bytes, not plaintexts with errors. Attackers get zero signal about how close they were.",
                "tags": ["PostQuantum", "NIST", "Cryptography", "FOSS"],
            },
            "linkedin": {
                "body": "Every AI fleet running RSA or ECC encryption is operating on borrowed time.\n\nQuantum computers will break these algorithms. The question isn't if, it's when.\n\nSCBE-AETHERMOORE already uses NIST-approved post-quantum standards:\n\n- ML-KEM-768 for key encapsulation\n- ML-DSA-65 for digital signatures\n- Chaos-based spectral diffusion for additional entropy\n\nThe most interesting property: fail-to-noise. Wrong decryption parameters produce output computationally indistinguishable from random noise. Attackers get zero signal about proximity to the correct key.\n\nThis matters for enterprise AI because your agents exchange sensitive context continuously. If that channel breaks, everything downstream breaks.\n\nWe built the migration path. 1,700+ tests verify it works.\n\n#PostQuantum #Cybersecurity #AISafety #Enterprise",
                "tags": ["PostQuantum", "Cybersecurity", "AISafety", "Enterprise"],
            },
            "medium": {
                "body": "# Post-Quantum Cryptography for AI Fleets: A Practical Migration Guide\n\nRSA and ECC have an expiration date. Here's how we migrated.\n\n## The Problem\n\nEvery AI agent that exchanges context, credentials, or instructions uses encryption. Most use RSA or ECC. Both will break under quantum computing.\n\n## Our Solution\n\nSCBE migrated to NIST-approved post-quantum algorithms:\n\n- **ML-KEM-768**: Key encapsulation (replaces Diffie-Hellman/ECDH)\n- **ML-DSA-65**: Digital signatures (replaces RSA/ECDSA)\n- **Chaos diffusion**: Additional spectral entropy layer\n\n## The Fail-to-Noise Property\n\nThe most important feature: wrong decryption produces output *indistinguishable from random noise*. Not garbled plaintext. Not error messages. Pure randomness.\n\nThis means brute-force attacks get zero feedback. There's no gradient to follow.\n\n## Migration Steps\n\n1. Replace KEM primitives (our `_select_kem_algorithm()` helper tries ML-KEM-768 first, falls back to Kyber768)\n2. Replace DSA primitives (same pattern for ML-DSA-65/Dilithium3)\n3. Add chaos diffusion layer (spectral domain mixing)\n4. Test with 14-layer pipeline integration tests\n\nOpen source: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)\n\n---\n\n*Isaac Davis builds post-quantum governance infrastructure for AI fleets.*",
                "tags": ["post-quantum", "cryptography", "cybersecurity", "migration-guide"],
            },
        },
    },
    {
        "topic": "multi_agent_trust",
        "hub_title": "How to Know When Your AI Agent Goes Rogue",
        "tags_base": ["MultiAgent", "TrustSystems"],
        "link": "https://github.com/issdandavis/SCBE-AETHERMOORE",
        "spokes": {
            "twitter": {
                "body": "How do you know if one of your AI agents has gone rogue?\n\nSCBE detects it mathematically. No messaging, no polling, no central authority.\n\nEach agent carries a trust score that decays when behavior drifts. Rogue agents self-exclude. No revocation needed.",
                "tags": ["MultiAgent", "AIAgents", "TrustSystems"],
            },
            "bluesky": {
                "body": "Trust in multi-agent AI should work like physics, not like HR.\n\nIn SCBE, trust is a continuous value in hyperbolic space. Good behavior keeps you near the center (low cost). Drift toward adversarial? Costs grow exponentially.\n\nNo trust committee. No revocation lists. Just math.",
                "tags": ["AIAgents", "Governance", "Math"],
            },
            "mastodon": {
                "body": "Implemented self-excluding trust for multi-agent systems.\n\nKey insight: trust = position in Poincare ball. Center = trusted. Edge = expensive.\n\nFormula: H(d,R) = R^(d^2)\n\nAt d=0.1 (slight drift): cost multiplier ~1.01\nAt d=0.9 (rogue): cost multiplier ~2.2\nAt d=2.0 (adversarial): cost multiplier ~16+\n\nRogue agents price themselves out. No governance meeting needed.",
                "tags": ["AIGovernance", "Math", "FOSS", "MultiAgent"],
            },
            "linkedin": {
                "body": "When one of your AI agents goes rogue, how long until you know?\n\nMost systems rely on monitoring dashboards, alert rules, or periodic audits. By the time you catch it, damage is done.\n\nSCBE uses continuous mathematical trust scoring. Every agent operation has a cost that scales with behavioral drift:\n\n- On-track agents (d < 0.3): near-zero overhead\n- Drifting agents (d = 0.3-1.2): increasing cost, gentle correction signals\n- Rogue agents (d > 2.0): operations cost 16x+ more, effectively self-excluding\n\nNo central authority needed. No revocation infrastructure. The math handles it.\n\nThis is particularly important for enterprise AI fleets where you might have hundreds of agents operating semi-autonomously across different tasks.\n\nBuilt with 1,700+ tests. Patent pending.\n\nWhat's your current approach to multi-agent trust?\n\n#MultiAgent #AIGovernance #Enterprise #TrustSystems",
                "tags": ["MultiAgent", "AIGovernance", "Enterprise", "TrustSystems"],
            },
            "medium": {
                "body": "# Rogue AI Detection Without Central Authority\n\n## The Trust Decay Problem\n\nIn a fleet of 100 AI agents, how do you know when one has gone rogue? Traditional approaches (monitoring, alerting, auditing) are reactive. SCBE makes it physics.\n\n## Continuous Trust as Hyperbolic Position\n\nEach agent's trust is a position in a Poincare ball. The center represents perfect alignment. The edge represents adversarial behavior.\n\nThe harmonic cost function: `H(d,R) = R^(d^2)`\n\n| Distance d | Behavior | Cost Multiplier |\n|-----------|----------|----------------|\n| 0.0-0.3 | On-track | ~1.0x |\n| 0.3-0.7 | Gentle drift | ~1.1-1.5x |\n| 0.7-1.2 | Concerning | ~1.5-3x |\n| 1.2-2.0 | Suspicious | ~3-16x |\n| >2.0 | Adversarial | >16x |\n\nRogue agents don't get \"caught\" — they price themselves out.\n\n## Swarm Consensus\n\nThe swarm validates trust scores through Byzantine fault-tolerant consensus. No single agent can override the math. Compromising the trust system requires corrupting >1/3 of the swarm simultaneously.\n\n## Implementation\n\nOpen source with 1,700+ tests: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)\n\n---\n\n*Isaac Davis is building the mathematical backbone for trusted AI operations.*",
                "tags": ["multi-agent-systems", "ai-safety", "trust-systems", "distributed-systems"],
            },
        },
    },
    {
        "topic": "sacred_tongues",
        "hub_title": "When Language Becomes Cryptography",
        "tags_base": ["Cryptography", "ConLang"],
        "link": "https://github.com/issdandavis/SCBE-AETHERMOORE",
        "spokes": {
            "twitter": {
                "body": "What if your encryption parameters came from a constructed language?\n\nSCBE maps linguistic tokens to fractal basin centers in Julia set parameter space. Wrong word = wrong fractal region = chaos fails.\n\n6 Sacred Tongues, golden ratio weighted. Intent becomes cryptography.",
                "tags": ["Cryptography", "ConLang", "FractalMath"],
            },
            "bluesky": {
                "body": "We built a constructed language where pronunciation literally IS the encryption key.\n\n6 Sacred Tongues, each weighted by powers of phi (1.618...):\nKO: 1.00, AV: 1.62, RU: 2.62, CA: 4.24, UM: 6.85, DR: 11.09\n\nEach token maps to a Julia set basin center. Say the wrong word? You get noise, not data.",
                "tags": ["ConLang", "Cryptography", "FractalMath"],
            },
            "mastodon": {
                "body": "Linguistic cryptography: 6 constructed languages where vocabulary tokens map to Julia set basin centers.\n\nThe golden ratio weights: KO(1.00) AV(1.62) RU(2.62) CA(4.24) UM(6.85) DR(11.09)\n\n256 tokens per language, 1,536 total fractal basins. Wrong tongue = wrong basin = chaos output.\n\nInspired by conlang worldbuilding. Built for post-quantum security.",
                "tags": ["ConLang", "Cryptography", "FOSS", "Worldbuilding"],
            },
            "linkedin": {
                "body": "The most creative part of our AI security framework: constructed languages as cryptographic parameters.\n\nSCBE-AETHERMOORE uses 6 Sacred Tongues — each a constructed language where vocabulary tokens map directly to fractal basin centers in Julia set parameter space.\n\nWhy this matters:\n- Traditional encryption uses numeric keys. Keys can be brute-forced.\n- Our system uses linguistic context as the key space. Wrong language = wrong fractal region = chaos diffusion fails = noise output.\n- 256 tokens per language, 6 languages = 1,536 unique fractal basins\n- Weights follow the golden ratio: each successive tongue is phi times more influential\n\nIt's the intersection of computational linguistics, fractal mathematics, and post-quantum cryptography.\n\nPatent pending. Open source.\n\nWhat's the most creative approach to security you've seen?\n\n#Innovation #Cryptography #ConLang #AISafety",
                "tags": ["Innovation", "Cryptography", "ConLang", "AISafety"],
            },
        },
    },
    {
        "topic": "geoseed",
        "hub_title": "A Neural Architecture Built on Geometry",
        "tags_base": ["DeepLearning", "GeometricDL"],
        "link": "https://huggingface.co/issdandavis",
        "spokes": {
            "twitter": {
                "body": "Novel neural architecture: 6 origin nodes spawn icosahedral sphere grids in Clifford algebra Cl(6,0).\n\n642 vertices per grid, 15 bivector channels, 64-dim signals. Cross-tongue convolution on the Poincare ball.\n\nHuggingFace compatible. 62 tests passing.",
                "tags": ["DeepLearning", "NeuralArchitecture", "Research"],
            },
            "bluesky": {
                "body": "Just shipped GeoSeed — a neural architecture where 6 origin nodes spawn icosahedral sphere grids.\n\nThe math: Clifford algebra Cl(6,0), 15 bivector rotation channels, signals propagate on the Poincare ball.\n\n3,852 total nodes. Cross-tongue convolution. HuggingFace compatible.",
                "tags": ["GeometricDL", "NeuralArchitecture", "AI"],
            },
            "linkedin": {
                "body": "Shipped a novel neural architecture this week: GeoSeed.\n\nInstead of flat tensor operations, GeoSeed uses geometric algebra on sphere grids:\n\n- 6 origin nodes (one per Sacred Tongue) spawn icosahedral grids\n- Clifford algebra Cl(6,0) provides 15 bivector rotation channels\n- Signals propagate via cross-tongue convolution on the Poincare ball\n- 642 vertices per grid, 3,852 total nodes, 64-dimensional signals\n\nHuggingFace-compatible PyTorch model with numpy fallback. 62 tests passing.\n\nThe thesis: geometric structure in the architecture enforces geometric structure in the learned representations. Safe behavior stays near manifold centers. Adversarial behavior gets pushed to expensive edges.\n\nAvailable on HuggingFace: issdandavis/\n\n#DeepLearning #NeuralArchitecture #GeometricDL #Research",
                "tags": ["DeepLearning", "NeuralArchitecture", "GeometricDL", "Research"],
            },
        },
    },
]


# ==========================================================================
# Generate from Topic Seeds
# ==========================================================================

# Platform → ContentType mapping
_PLATFORM_TYPE = {
    "twitter": ContentType.SOCIAL_SHORT,
    "bluesky": ContentType.SOCIAL_SHORT,
    "mastodon": ContentType.SOCIAL_SHORT,
    "linkedin": ContentType.SOCIAL_LONG,
    "medium": ContentType.BLOG_POST,
}


# ==========================================================================
# Governance Gate — L14 quality/flux monitoring
# ==========================================================================

@dataclass
class GovernanceResult:
    """Result of running content through the governance gate."""
    passed: bool
    score: float           # 0.0 = bad, 1.0 = good
    flags: List[str] = field(default_factory=list)
    recommendation: str = ""


def governance_scan(content: ContentPiece) -> GovernanceResult:
    """Run content through L14 quality gate.

    Checks:
    1. Is this too many posts? (rate limiting)
    2. Will it get flagged as AI? (naturalness check)
    3. Is the content actually good? (quality check)
    4. Does it contain anything dangerous? (safety check)
    """
    flags: List[str] = []
    score = 1.0

    text = content.body

    # --- Safety check (use antivirus membrane if available) ---
    try:
        from agents.antivirus_membrane import scan_text_for_threats
        threat = scan_text_for_threats(text)
        if threat.verdict.upper() not in ("CLEAN", "LOW"):
            flags.append(f"threat_detected:{threat.verdict}")
            score -= 0.5
    except ImportError:
        pass  # No membrane available, skip

    # --- Quality checks ---

    # Too short?
    if len(text) < 50:
        flags.append("too_short")
        score -= 0.2

    # Too long for platform?
    if content.content_type == ContentType.SOCIAL_SHORT and len(text) > 300:
        flags.append("exceeds_social_limit")
        score -= 0.1

    # Has links? (Good for engagement)
    if content.link:
        score += 0.05

    # Has tags? (Good for discovery)
    if content.tags:
        score += 0.05

    # --- AI detection resistance ---
    # Check for common AI giveaways
    ai_markers = [
        "as an ai", "i'm an ai", "language model",
        "here's a", "here is a", "certainly!",
        "absolutely!", "great question",
        "it's important to note",
        "it's worth noting",
        "in conclusion",
    ]
    text_lower = text.lower()
    for marker in ai_markers:
        if marker in text_lower:
            flags.append(f"ai_marker:{marker}")
            score -= 0.1

    # --- Rate check (flux monitoring) ---
    # Check if we've posted too recently
    rate_file = os.path.join(
        os.path.dirname(__file__), "..", "artifacts", "post_rate.json"
    )
    if os.path.exists(rate_file):
        try:
            with open(rate_file, "r") as f:
                rate_data = json.load(f)
            posts_today = rate_data.get("posts_today", 0)
            if posts_today > 10:
                flags.append("rate_limit:too_many_today")
                score -= 0.3
            elif posts_today > 5:
                flags.append("rate_warning:approaching_limit")
                score -= 0.1
        except (json.JSONDecodeError, OSError):
            pass

    score = max(0.0, min(1.0, score))
    passed = score >= 0.5 and "threat_detected" not in str(flags)

    recommendation = "publish" if passed else "review"
    if not passed:
        if "threat_detected" in str(flags):
            recommendation = "block"
        elif score < 0.3:
            recommendation = "rewrite"

    return GovernanceResult(
        passed=passed,
        score=round(score, 2),
        flags=flags,
        recommendation=recommendation,
    )


# ==========================================================================
# Pipeline — generate, govern, queue
# ==========================================================================

@dataclass
class PipelineResult:
    """Result of a full pipeline run."""
    generated: int
    passed_governance: int
    queued: int
    blocked: int
    errors: List[str] = field(default_factory=list)
    pieces: List[ContentPiece] = field(default_factory=list)


def generate_content_batch(*, topics: Optional[List[str]] = None) -> List[ContentPiece]:
    """Generate a batch of content from topic seeds.

    Each topic seed produces one unique piece per platform.
    Never the same content on two platforms.
    """
    pieces: List[ContentPiece] = []

    for seed in TOPIC_SEEDS:
        if topics and seed["topic"] not in topics:
            continue

        for platform, spoke in seed["spokes"].items():
            content_type = _PLATFORM_TYPE.get(platform, ContentType.SOCIAL_SHORT)
            pieces.append(ContentPiece(
                content_type=content_type,
                title=f"{seed['hub_title']}",
                body=spoke["body"],
                tags=spoke.get("tags", seed["tags_base"]),
                platforms=[platform],
                link=seed.get("link", ""),
                metadata={"topic": seed["topic"], "platform": platform},
            ))

    return pieces


def run_pipeline(*, publish: bool = False) -> PipelineResult:
    """Run the full content pipeline: generate → govern → queue."""
    pieces = generate_content_batch()
    result = PipelineResult(generated=len(pieces), passed_governance=0, queued=0, blocked=0)

    queue_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "content_queue")
    os.makedirs(queue_dir, exist_ok=True)

    for piece in pieces:
        # Governance gate
        gov = governance_scan(piece)
        piece.governance_score = gov.score
        piece.governance_passed = gov.passed

        if gov.passed:
            result.passed_governance += 1

            # Save to queue
            platform_key = piece.platforms[0] if piece.platforms else "generic"
            topic_key = piece.metadata.get("topic", piece.title)
            queue_entry = {
                "id": hashlib.md5(f"{topic_key}:{platform_key}".encode()).hexdigest()[:12],
                "type": piece.content_type.value,
                "title": piece.title,
                "body": piece.body,
                "tags": piece.tags,
                "platforms": piece.platforms,
                "link": piece.link,
                "governance_score": piece.governance_score,
                "governance_flags": gov.flags,
                "status": "queued",
                "created": datetime.now(timezone.utc).isoformat(),
            }

            filepath = os.path.join(queue_dir, f"{queue_entry['id']}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(queue_entry, f, indent=2)

            result.queued += 1
            result.pieces.append(piece)
        else:
            result.blocked += 1
            result.errors.append(
                f"BLOCKED [{gov.recommendation}] {piece.title}: "
                f"score={gov.score}, flags={gov.flags}"
            )

    return result


def show_status():
    """Show current pipeline status."""
    queue_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "content_queue")
    if not os.path.exists(queue_dir):
        print("No content queue found.")
        return

    queued = []
    published = []
    for f in os.listdir(queue_dir):
        if f.endswith(".json"):
            with open(os.path.join(queue_dir, f), "r") as fh:
                entry = json.load(fh)
                if entry.get("status") == "published":
                    published.append(entry)
                else:
                    queued.append(entry)

    print(f"\n{'='*60}")
    print(f"  REVENUE ENGINE STATUS")
    print(f"{'='*60}")
    print(f"  Queued:    {len(queued)}")
    print(f"  Published: {len(published)}")
    print(f"{'='*60}")

    if queued:
        print(f"\n  QUEUED CONTENT:")
        for entry in queued:
            platforms = ", ".join(entry.get("platforms", []))
            print(f"    [{entry['type']}] {entry['title']}")
            print(f"      Platforms: {platforms}")
            print(f"      Score: {entry.get('governance_score', 'N/A')}")
            print()

    if published:
        print(f"\n  PUBLISHED:")
        for entry in published:
            print(f"    [{entry['type']}] {entry['title']} -> {entry.get('post_url', 'N/A')}")


def show_products():
    """Show available products across stores."""
    print(f"\n{'='*60}")
    print(f"  STORE PRODUCTS")
    print(f"{'='*60}")

    products = [
        {"name": "SCBE Governance Toolkit", "store": "Gumroad", "price": "$29.99",
         "status": "needs content update"},
        {"name": "WorldForge Game Engine", "store": "Gumroad", "price": "$49.99",
         "status": "needs content update"},
        {"name": "HYDRA Protocol Guide", "store": "Gumroad", "price": "$19.99",
         "status": "needs content update"},
        {"name": "Notion AI Workspace Templates", "store": "Gumroad", "price": "$9.99",
         "status": "active"},
        {"name": "Aethermoor Creator OS", "store": "Shopify", "price": "varies",
         "status": "theme ready"},
        {"name": "SCBE Training Dataset", "store": "HuggingFace", "price": "free/license",
         "status": "active - issdandavis/scbe-aethermoore-training-data"},
    ]

    for p in products:
        print(f"  [{p['store']}] {p['name']} — {p['price']} ({p['status']})")

    print(f"\n  PAYMENT RAILS:")
    rails = {
        "Stripe": os.environ.get("STRIPE_SECRET_KEY", "NOT SET"),
        "CashApp": os.environ.get("CASHAPP_TAG", "NOT SET"),
        "Ko-fi": "https://ko-fi.com/ (needs setup)",
        "Shopify": "Storefront ready",
        "Gumroad": "Products listed",
    }
    for name, status in rails.items():
        masked = "configured" if status not in ("NOT SET", "") and "needs" not in status else status
        print(f"    {name}: {masked}")


# ==========================================================================
# CLI
# ==========================================================================

def run_spin_pipeline(topic: Optional[str] = None, depth: int = 2) -> PipelineResult:
    """Run the content spin pipeline: spin topics → govern → queue.

    Uses Fibonacci relay branching from content_spin.py to multiply
    content variations, then runs each through the governance gate.
    """
    try:
        from scripts.content_spin import ContentSpinner
    except ImportError:
        # Try relative import
        from content_spin import ContentSpinner

    spinner = ContentSpinner()

    if topic:
        variations = spinner.spin(topic, depth=depth)
    else:
        variations = spinner.spin_all_seeds(depth=depth)

    # Convert spin variations to ContentPieces and run through governance
    pieces = []
    for v in variations:
        # Map spin platform to content type
        platform_map = {
            "twitter": ContentType.SOCIAL_SHORT,
            "bluesky": ContentType.SOCIAL_SHORT,
            "mastodon": ContentType.SOCIAL_SHORT,
            "linkedin": ContentType.SOCIAL_LONG,
            "medium": ContentType.BLOG_POST,
            "shopify_blog": ContentType.BLOG_POST,
            "github": ContentType.GITHUB_UPDATE,
        }
        content_type = platform_map.get(v.platform, ContentType.SOCIAL_SHORT)

        pieces.append(ContentPiece(
            content_type=content_type,
            title=v.angle,
            body=v.body,
            tags=v.tags,
            platforms=[v.platform],
            link="",
            metadata={
                "topic": v.topic,
                "platform": v.platform,
                "spin_depth": v.spin_depth,
                "relay_chain": v.relay_chain,
                "harmonic_freq": v.harmonic_freq,
                "context_vector": v.context_vector,
                "source": "content_spin",
            },
        ))

    result = PipelineResult(generated=len(pieces), passed_governance=0, queued=0, blocked=0)

    queue_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "content_queue")
    os.makedirs(queue_dir, exist_ok=True)

    for piece in pieces:
        gov = governance_scan(piece)
        piece.governance_score = gov.score
        piece.governance_passed = gov.passed

        if gov.passed:
            result.passed_governance += 1
            platform_key = piece.platforms[0] if piece.platforms else "generic"
            topic_key = piece.metadata.get("topic", piece.title)
            chain_key = ":".join(piece.metadata.get("relay_chain", []))

            queue_entry = {
                "id": hashlib.md5(f"spin:{topic_key}:{platform_key}:{chain_key}".encode()).hexdigest()[:12],
                "type": piece.content_type.value,
                "title": piece.title,
                "body": piece.body,
                "tags": piece.tags,
                "platforms": piece.platforms,
                "governance_score": piece.governance_score,
                "governance_flags": gov.flags,
                "spin_depth": piece.metadata.get("spin_depth", 0),
                "relay_chain": piece.metadata.get("relay_chain", []),
                "harmonic_freq": piece.metadata.get("harmonic_freq", 1.0),
                "status": "queued",
                "source": "content_spin",
                "created": datetime.now(timezone.utc).isoformat(),
            }

            filepath = os.path.join(queue_dir, f"spin_{queue_entry['id']}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(queue_entry, f, indent=2)

            result.queued += 1
            result.pieces.append(piece)
        else:
            result.blocked += 1
            result.errors.append(
                f"BLOCKED [{gov.recommendation}] {piece.title}: "
                f"score={gov.score}, flags={gov.flags}"
            )

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/revenue_engine.py <command>")
        print("Commands: generate, publish, status, products, full, spin")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "generate":
        result = run_pipeline(publish=False)
        print(f"\nGenerated: {result.generated}")
        print(f"Passed governance: {result.passed_governance}")
        print(f"Queued: {result.queued}")
        print(f"Blocked: {result.blocked}")
        if result.errors:
            print("\nBlocked content:")
            for err in result.errors:
                print(f"  {err}")
        print(f"\nContent queued to: artifacts/content_queue/")

    elif cmd == "publish":
        print("Publishing queued content...")
        print("(Set platform credentials in .env to enable live publishing)")
        show_status()

    elif cmd == "status":
        show_status()

    elif cmd == "products":
        show_products()

    elif cmd == "spin":
        topic = sys.argv[2] if len(sys.argv) > 2 else None
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        print(f"Running spin pipeline{f' for {topic}' if topic else ' (all seeds)'}...")
        result = run_spin_pipeline(topic=topic, depth=depth)
        print(f"\nSpin Results:")
        print(f"  Generated: {result.generated} variations")
        print(f"  Passed governance: {result.passed_governance}")
        print(f"  Queued: {result.queued}")
        print(f"  Blocked: {result.blocked}")
        if result.errors:
            print("\nBlocked:")
            for err in result.errors:
                print(f"  {err}")

    elif cmd == "full":
        print("Running full pipeline: generate → govern → queue")
        result = run_pipeline(publish=True)
        print(f"\nResults: {result.passed_governance}/{result.generated} passed governance")
        print(f"Queued {result.queued} pieces for publishing")
        if result.blocked > 0:
            print(f"Blocked {result.blocked} pieces")
        show_status()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
