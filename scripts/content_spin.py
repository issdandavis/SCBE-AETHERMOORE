#!/usr/bin/env python3
"""Content Spin Pipeline — Fibonacci relay branching for content multiplication.

Takes a topic seed and spins it through relay chains:
    1 speaker → 3 listeners → each speaks to 3 → relay chains → circle back

Uses the PivotKnowledge topic graph from Colab + FerrofluidAgenticCore
harmonic patterns for wave-based inter-communication.

The bent geodesic model: same fixed points (facts), different paths
(context, time, event, geo-location bend the lines).

Usage:
    python scripts/content_spin.py spin "ai_governance"     # Spin a topic
    python scripts/content_spin.py graph                     # Show topic graph
    python scripts/content_spin.py relay "ai_governance" 3   # 3 relay depths
    python scripts/content_spin.py batch                     # Spin all seeds

@layer Layer 5 (hyperbolic distance), Layer 12 (harmonic cost)
@component Content.Spin
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
#  Constants — Fibonacci + harmonic
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.618...
PHI_INV = PHI - 1              # 0.618...

# Harmonic ratios from ferrofluid core (musical intervals)
HARMONIC_RATIOS = {
    "unison": 1.0,
    "minor_third": 6 / 5,
    "major_third": 5 / 4,
    "perfect_fourth": 4 / 3,
    "perfect_fifth": 3 / 2,
    "minor_sixth": 8 / 5,
    "major_sixth": 5 / 3,
    "octave": 2.0,
}

# Sacred Tongue weights (phi-scaled)
TONGUE_WEIGHTS = {
    "KO": 1.00,
    "AV": 1.62,
    "RU": 2.62,
    "CA": 4.24,
    "UM": 6.85,
    "DR": 11.09,
}

# Platform voice profiles (how each platform bends the content)
PLATFORM_VOICES = {
    "twitter": {
        "max_len": 280,
        "tone": "punchy",
        "structure": "hook → insight → CTA",
        "harmonic": "perfect_fifth",  # 3:2 — concise resonance
    },
    "bluesky": {
        "max_len": 500,
        "tone": "technical_casual",
        "structure": "observation → mechanism → implication",
        "harmonic": "major_third",  # 5:4 — warm clarity
    },
    "mastodon": {
        "max_len": 500,
        "tone": "community_first",
        "structure": "hot_take → math → FOSS_ethos",
        "harmonic": "perfect_fourth",  # 4:3 — balanced
    },
    "linkedin": {
        "max_len": 3000,
        "tone": "professional",
        "structure": "problem → solution → layers → results → CTA",
        "harmonic": "minor_sixth",  # 8:5 — authoritative warmth
    },
    "medium": {
        "max_len": 10000,
        "tone": "deep_technical",
        "structure": "narrative → architecture → code → implications",
        "harmonic": "octave",  # 2:1 — full exploration
    },
    "shopify_blog": {
        "max_len": 5000,
        "tone": "product_focused",
        "structure": "problem → product → how_it_works → buy",
        "harmonic": "major_sixth",  # 5:3 — persuasive
    },
    "github": {
        "max_len": 2000,
        "tone": "developer",
        "structure": "changelog → technical_detail → usage",
        "harmonic": "unison",  # 1:1 — direct
    },
}


# ---------------------------------------------------------------------------
#  PivotKnowledge — Topic graph for natural conversation pivoting
#  (from Colab, extended for SCBE content domains)
# ---------------------------------------------------------------------------

class PivotKnowledge:
    """Topic graph for natural conversation pivoting.

    Extended from the Colab version with SCBE-specific topic domains.
    Each topic connects to 5 adjacent topics for natural content flow.
    """

    def __init__(self):
        self.topic_graph: Dict[str, List[str]] = {
            # Original Colab topics
            "programming": ["algorithms", "databases", "web_development", "AI", "cybersecurity"],
            "cooking": ["nutrition", "food_science", "travel_cuisine", "gardening", "chemistry"],
            "music": ["mathematics", "physics_of_sound", "emotions", "culture", "technology"],
            "astronomy": ["physics", "mythology", "navigation", "time", "philosophy"],
            "history": ["archaeology", "geography", "politics", "art", "economics"],
            "psychology": ["neuroscience", "philosophy", "behavior", "dreams", "creativity"],

            # SCBE content domains — fully connected graph (no dead ends)
            "ai_governance": ["ai_safety", "enterprise_ai", "multi_agent", "compliance", "post_quantum"],
            "ai_safety": ["alignment", "adversarial_ml", "ai_governance", "ethics", "multi_agent"],
            "post_quantum": ["cryptography", "cybersecurity", "quantum_computing", "ai_governance", "trust_systems"],
            "cryptography": ["post_quantum", "cybersecurity", "mathematics", "sacred_tongues", "ai_governance"],
            "multi_agent": ["trust_systems", "ai_governance", "geoseed", "automation", "game_dev"],
            "trust_systems": ["multi_agent", "ai_governance", "cryptography", "cybersecurity", "post_quantum"],
            "hyperbolic_geometry": ["mathematics", "geoseed", "sacred_tongues", "ai_safety", "ai_governance"],
            "sacred_tongues": ["cryptography", "hyperbolic_geometry", "geoseed", "education", "game_dev"],
            "geoseed": ["hyperbolic_geometry", "sacred_tongues", "multi_agent", "mathematics", "AI"],
            "game_dev": ["multi_agent", "sacred_tongues", "education", "automation", "AI"],
            "education": ["game_dev", "sacred_tongues", "AI", "content_pipeline", "shopify"],
            "shopify": ["automation", "content_pipeline", "education", "AI", "game_dev"],
            "enterprise_ai": ["ai_governance", "multi_agent", "shopify", "automation", "trust_systems"],
            "compliance": ["ai_governance", "cybersecurity", "enterprise_ai", "education", "trust_systems"],
            "alignment": ["ai_safety", "ai_governance", "ethics", "multi_agent", "education"],
            "adversarial_ml": ["ai_safety", "cybersecurity", "cryptography", "trust_systems", "post_quantum"],
            "ethics": ["ai_safety", "philosophy", "alignment", "ai_governance", "education"],
            "quantum_computing": ["post_quantum", "mathematics", "cryptography", "AI", "astronomy"],

            # Expanded adjacencies
            "algorithms": ["programming", "mathematics", "AI", "cryptography", "geoseed"],
            "AI": ["ai_safety", "ai_governance", "geoseed", "game_dev", "automation"],
            "cybersecurity": ["cryptography", "post_quantum", "compliance", "adversarial_ml", "trust_systems"],
            "mathematics": ["hyperbolic_geometry", "music", "algorithms", "cryptography", "geoseed"],
            "philosophy": ["ethics", "psychology", "astronomy", "sacred_tongues", "education"],
            "technology": ["AI", "programming", "automation", "shopify", "game_dev"],
            "automation": ["shopify", "content_pipeline", "AI", "multi_agent", "enterprise_ai"],
            "n8n_workflows": ["automation", "shopify", "content_pipeline", "AI", "enterprise_ai"],
            "content_pipeline": ["automation", "shopify", "education", "AI", "sacred_tongues"],
        }
        self.current_topic: Optional[str] = None
        self.pivot_history: List[str] = []

    def set_topic(self, topic: str) -> bool:
        """Set the starting topic."""
        if topic not in self.topic_graph:
            return False
        self.current_topic = topic
        self.pivot_history = [topic]
        return True

    def pivot(self, seed: Optional[int] = None) -> Optional[str]:
        """Pivot to an adjacent topic. Optionally seed for determinism."""
        if not self.current_topic or self.current_topic not in self.topic_graph:
            return None

        adjacent = self.topic_graph[self.current_topic]
        if not adjacent:
            return None

        rng = random.Random(seed)
        new_topic = rng.choice(adjacent)
        self.pivot_history.append(new_topic)
        self.current_topic = new_topic
        return new_topic

    def get_adjacents(self, topic: str) -> List[str]:
        """Get all adjacent topics for a given topic."""
        return self.topic_graph.get(topic, [])

    def fibonacci_relay(self, start_topic: str, depth: int = 3,
                        branch_factor: int = 3) -> List[List[str]]:
        """Generate Fibonacci relay chains from a starting topic.

        1 speaker → 3 listeners → each speaks to 3 → relay chains.
        Branch factor grows with Fibonacci: F(depth) branches per level.

        Returns list of relay chains (each chain is a list of topics).
        """
        chains: List[List[str]] = []

        # Precompute Fibonacci sequence for branching
        fibs = [1, 1]
        for _ in range(depth + 2):
            fibs.append(fibs[-1] + fibs[-2])

        def _relay(topic: str, chain: List[str], d: int):
            if d >= depth:
                chains.append(chain[:])
                return

            adjacents = self.get_adjacents(topic)
            if not adjacents:
                chains.append(chain[:])
                return

            # Fibonacci-controlled branching: more branches at shallow depths
            # Depth 0: branch_factor, Depth 1: branch_factor, Depth 2+: F(d+1)
            fib_branches = min(fibs[d + 1], branch_factor)
            n_branches = min(fib_branches, len(adjacents))
            n_branches = max(1, n_branches)  # At least 1

            # Deterministic selection based on chain hash for reproducibility
            chain_hash = int(hashlib.md5(":".join(chain).encode()).hexdigest(), 16)
            rng = random.Random(chain_hash)
            selected = rng.sample(adjacents, min(n_branches, len(adjacents)))

            for next_topic in selected:
                new_chain = chain + [next_topic]
                _relay(next_topic, new_chain, d + 1)

        _relay(start_topic, [start_topic], 0)

        # Circle back: connect last topic back to start via shortest path
        for chain in chains:
            if chain[-1] != start_topic:
                # Check if start is adjacent to end
                end_adjacents = self.get_adjacents(chain[-1])
                if start_topic in end_adjacents:
                    chain.append(start_topic)

        return chains


# ---------------------------------------------------------------------------
#  ContentVariation — a single spin output
# ---------------------------------------------------------------------------

@dataclass
class ContentVariation:
    """A content piece produced by spinning a topic through relay chains."""
    topic: str
    platform: str
    angle: str           # What bent the line (pivot chain)
    body: str
    tags: List[str] = field(default_factory=list)
    harmonic_freq: float = 1.0   # Musical ratio for this platform
    spin_depth: int = 0          # How many relay hops from original
    relay_chain: List[str] = field(default_factory=list)
    context_vector: List[float] = field(default_factory=list)  # 4D: time, context, prev_factor, harmonic
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  Spin templates — angle generators for each platform
# ---------------------------------------------------------------------------

# Angle templates: how to bend the same fact for different contexts
ANGLE_TEMPLATES = {
    "direct": "{topic} explained simply",
    "contrarian": "Why {topic} isn't what you think",
    "case_study": "How we built {topic} from scratch",
    "comparison": "{topic} vs the competition",
    "prediction": "Where {topic} is heading in 2027",
    "tutorial": "Step-by-step: implementing {topic}",
    "myth_bust": "3 myths about {topic} debunked",
    "listicle": "5 things you didn't know about {topic}",
    "origin": "The unexpected origin of {topic}",
    "intersection": "When {topic_a} meets {topic_b}",
}


def generate_angle(topic: str, relay_chain: List[str], depth: int) -> str:
    """Generate a content angle from a relay chain.

    The angle is determined by which topics the relay chain passes through.
    Deeper chains = more tangential angles.
    """
    angle_keys = list(ANGLE_TEMPLATES.keys())
    chain_hash = int(hashlib.md5(":".join(relay_chain).encode()).hexdigest(), 16)
    angle_idx = chain_hash % len(angle_keys)
    angle_key = angle_keys[angle_idx]

    if angle_key == "intersection" and len(relay_chain) >= 2:
        return ANGLE_TEMPLATES[angle_key].format(
            topic_a=relay_chain[0].replace("_", " "),
            topic_b=relay_chain[-1].replace("_", " "),
        )
    return ANGLE_TEMPLATES[angle_key].format(topic=topic.replace("_", " "))


# ---------------------------------------------------------------------------
#  4D Context Vector
# ---------------------------------------------------------------------------

def compute_context_vector(
    topic: str,
    platform: str,
    relay_chain: List[str],
    depth: int,
) -> List[float]:
    """Compute 4D context vector: (time, context, previous_factor, harmonic).

    Not decimal — wave patterns. Each component is a phase in [0, 2pi).
    """
    now = datetime.now(timezone.utc)
    chain_hash = int(hashlib.md5(":".join(relay_chain).encode()).hexdigest(), 16)

    # Time phase — where we are in the day/week cycle
    hour_phase = (now.hour / 24.0) * 2 * math.pi
    day_phase = (now.weekday() / 7.0) * 2 * math.pi

    # Context phase — topic position in graph (hash-based)
    topic_hash = int(hashlib.md5(topic.encode()).hexdigest(), 16)
    context_phase = (topic_hash % 1000 / 1000.0) * 2 * math.pi

    # Previous factor — Fibonacci spiral position
    fib_phase = (depth * PHI_INV * 2 * math.pi) % (2 * math.pi)

    # Harmonic — platform voice harmonic ratio as phase
    voice = PLATFORM_VOICES.get(platform, {})
    harmonic_name = voice.get("harmonic", "unison")
    harmonic_ratio = HARMONIC_RATIOS.get(harmonic_name, 1.0)
    harmonic_phase = harmonic_ratio * math.pi  # Scale into wave

    return [
        round(hour_phase + day_phase, 4),  # time wave
        round(context_phase, 4),            # context wave
        round(fib_phase, 4),                # previous_factor wave
        round(harmonic_phase, 4),           # harmonic wave
    ]


# ---------------------------------------------------------------------------
#  Content Spinner
# ---------------------------------------------------------------------------

class ContentSpinner:
    """Fibonacci content spin engine.

    Takes a topic seed, pivots through the topic graph,
    and generates platform-specific content variations.

    The math:
    - Fixed points (facts) connected by bent geodesics
    - What bends: context (platform), time (schedule), event (relay chain),
      geo-location (tongue weight)
    - Fibonacci branching controls the relay depth
    - Harmonic ratios set inter-communication frequency
    """

    def __init__(self):
        self.graph = PivotKnowledge()
        self.variations: List[ContentVariation] = []

    def spin(
        self,
        topic: str,
        depth: int = 2,
        platforms: Optional[List[str]] = None,
        branch_factor: int = 3,
    ) -> List[ContentVariation]:
        """Spin a topic into content variations.

        1 topic → relay chains (Fibonacci branching) → platform-specific output.

        Args:
            topic: Starting topic from the graph
            depth: Relay chain depth (1=direct, 2=tangential, 3=deep tangent)
            platforms: Target platforms (default: all)
            branch_factor: Max branches per relay hop

        Returns:
            List of ContentVariation objects
        """
        if platforms is None:
            platforms = list(PLATFORM_VOICES.keys())

        # Generate relay chains via Fibonacci branching
        chains = self.graph.fibonacci_relay(topic, depth=depth, branch_factor=branch_factor)

        variations: List[ContentVariation] = []

        for chain in chains:
            for platform in platforms:
                angle = generate_angle(topic, chain, len(chain) - 1)
                voice = PLATFORM_VOICES.get(platform, {})
                harmonic_name = voice.get("harmonic", "unison")
                harmonic_freq = HARMONIC_RATIOS.get(harmonic_name, 1.0)

                context_vec = compute_context_vector(topic, platform, chain, len(chain) - 1)

                # Generate the content body
                body = self._generate_body(topic, chain, platform, angle, voice)

                # Generate tags from chain
                tags = self._generate_tags(topic, chain, platform)

                variation = ContentVariation(
                    topic=topic,
                    platform=platform,
                    angle=angle,
                    body=body,
                    tags=tags,
                    harmonic_freq=harmonic_freq,
                    spin_depth=len(chain) - 1,
                    relay_chain=chain,
                    context_vector=context_vec,
                    metadata={
                        "chain_hash": hashlib.md5(":".join(chain).encode()).hexdigest()[:8],
                        "voice_tone": voice.get("tone", ""),
                        "structure": voice.get("structure", ""),
                    },
                )
                variations.append(variation)

        self.variations = variations
        return variations

    def _generate_body(
        self, topic: str, chain: List[str], platform: str,
        angle: str, voice: Dict[str, Any],
    ) -> str:
        """Generate content body for a specific platform + relay chain.

        This produces the template structure. In production, an LLM fills it.
        """
        max_len = voice.get("max_len", 500)
        tone = voice.get("tone", "neutral")
        structure = voice.get("structure", "")

        # Build pivot path description
        pivot_path = " -> ".join(c.replace("_", " ") for c in chain)
        topic_display = topic.replace("_", " ")
        tangent_topics = [c.replace("_", " ") for c in chain[1:]] if len(chain) > 1 else []

        if platform in ("twitter", "bluesky", "mastodon"):
            # Short form
            if tangent_topics:
                body = (
                    f"{angle}.\n\n"
                    f"The connection between {topic_display} and "
                    f"{tangent_topics[-1]} isn't obvious — until you see the math.\n\n"
                    f"Path: {pivot_path}"
                )
            else:
                body = f"{angle}.\n\nThe math behind {topic_display} changes everything."

        elif platform == "linkedin":
            # Professional long form
            sections = [
                f"{angle}.",
                "",
                f"Most people think about {topic_display} in isolation. "
                f"But the real insight comes from following the connections:",
                "",
                f"Path: {pivot_path}",
                "",
            ]
            for i, t in enumerate(tangent_topics):
                sections.append(f"- Step {i+1}: {t} reveals a hidden dimension")
            sections.extend([
                "",
                "This is the bent geodesic model — same facts, different paths "
                "based on context. The lines between knowledge points aren't straight.",
                "",
                f"#{topic_display.replace(' ', '')} #Innovation",
            ])
            body = "\n".join(sections)

        elif platform == "medium":
            # Deep technical article structure
            sections = [
                f"# {angle}",
                "",
                f"## The Fixed Points",
                "",
                f"In any knowledge domain, there are facts that don't move. "
                f"Events happened. Papers were published. Code was written. "
                f"These are the fixed points of {topic_display}.",
                "",
                f"## The Bent Lines",
                "",
                f"What makes the same fact interesting to different audiences "
                f"is the *path* you take to get there. In hyperbolic geometry, "
                f"these paths are geodesics — and they bend based on:",
                "",
                f"- **Context**: Who is reading, what they already know",
                f"- **Time**: When in the news cycle",
                f"- **Event**: What just happened that makes this relevant",
                f"- **Geo-location**: Cultural/regional perspective",
                "",
                f"## The Relay Chain",
                "",
                f"Starting from {topic_display}, the natural conversation flows through:",
                "",
            ]
            for i, t in enumerate(chain):
                sections.append(f"{i+1}. **{t.replace('_', ' ').title()}**")
            sections.extend([
                "",
                f"Each hop bends the geodesic further. By the time we reach "
                f"the end of the chain, we're looking at {topic_display} from "
                f"an angle that no single-step article could achieve.",
                "",
                f"---",
                "",
                f"*Built with the SCBE content spin pipeline.*",
            ])
            body = "\n".join(sections)

        elif platform == "shopify_blog":
            # Product-focused
            body = (
                f"# {angle}\n\n"
                f"Understanding {topic_display} is key to building better products.\n\n"
                f"At Aethermoore, we follow the connections: {pivot_path}\n\n"
                f"Each step reveals why our tools work the way they do.\n\n"
                f"[Explore our products](/collections/all)"
            )

        elif platform == "github":
            # Developer changelog
            body = (
                f"## {angle}\n\n"
                f"Related areas: {', '.join(tangent_topics) if tangent_topics else topic_display}\n\n"
                f"This update touches on the intersection of these domains "
                f"within the SCBE pipeline."
            )

        else:
            body = f"{angle}. Exploring {topic_display} through {pivot_path}."

        # Truncate to max length
        if len(body) > max_len:
            body = body[:max_len - 3] + "..."

        return body

    def _generate_tags(self, topic: str, chain: List[str], platform: str) -> List[str]:
        """Generate platform-appropriate tags from the relay chain."""
        base_tags = [topic.replace("_", " ").title()]

        # Add chain topics as tags (limited)
        for t in chain[1:3]:  # Max 2 tangent tags
            base_tags.append(t.replace("_", " ").title())

        # Platform-specific tag formatting
        if platform in ("twitter", "bluesky"):
            return [f"#{t.replace(' ', '')}" for t in base_tags[:4]]
        elif platform == "mastodon":
            return [f"#{t.replace(' ', '')}" for t in base_tags[:5]]
        elif platform in ("linkedin", "medium"):
            return base_tags[:6]
        else:
            return base_tags[:4]

    def spin_all_seeds(self, depth: int = 2) -> List[ContentVariation]:
        """Spin all TOPIC_SEEDS from the revenue engine through relay chains."""
        try:
            from scripts.revenue_engine import TOPIC_SEEDS
            seeds = [s["topic"] for s in TOPIC_SEEDS]
        except ImportError:
            seeds = ["ai_governance", "post_quantum", "multi_agent", "sacred_tongues", "geoseed"]

        all_variations: List[ContentVariation] = []
        for topic in seeds:
            variations = self.spin(topic, depth=depth)
            all_variations.extend(variations)

        return all_variations

    def export_to_queue(self, variations: List[ContentVariation]) -> int:
        """Export variations to the content queue for the revenue engine."""
        queue_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "spin_queue")
        os.makedirs(queue_dir, exist_ok=True)

        count = 0
        for v in variations:
            entry = {
                "id": hashlib.md5(
                    f"{v.topic}:{v.platform}:{':'.join(v.relay_chain)}".encode()
                ).hexdigest()[:12],
                "topic": v.topic,
                "platform": v.platform,
                "angle": v.angle,
                "body": v.body,
                "tags": v.tags,
                "harmonic_freq": v.harmonic_freq,
                "spin_depth": v.spin_depth,
                "relay_chain": v.relay_chain,
                "context_vector": v.context_vector,
                "status": "spun",
                "created": datetime.now(timezone.utc).isoformat(),
            }

            filepath = os.path.join(queue_dir, f"{entry['id']}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
            count += 1

        return count


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/content_spin.py <command> [args]")
        print("Commands:")
        print("  spin <topic> [depth]  — Spin a topic through relay chains")
        print("  graph                 — Show the topic graph")
        print("  relay <topic> [depth] — Show relay chains only")
        print("  batch                 — Spin all revenue engine seeds")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    spinner = ContentSpinner()

    if cmd == "spin":
        topic = sys.argv[2] if len(sys.argv) > 2 else "ai_governance"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2

        print(f"\nSpinning '{topic}' at depth {depth}...")
        variations = spinner.spin(topic, depth=depth)

        print(f"\n{'='*70}")
        print(f"  CONTENT SPIN: {topic} ({len(variations)} variations)")
        print(f"{'='*70}")

        # Group by platform
        by_platform: Dict[str, List[ContentVariation]] = {}
        for v in variations:
            by_platform.setdefault(v.platform, []).append(v)

        for platform, pvars in by_platform.items():
            voice = PLATFORM_VOICES.get(platform, {})
            print(f"\n  [{platform.upper()}] ({voice.get('tone', '')}) — {len(pvars)} pieces")
            for v in pvars[:3]:  # Show max 3 per platform
                print(f"    Angle: {v.angle}")
                print(f"    Chain: {' -> '.join(v.relay_chain)}")
                print(f"    Harmonic: {v.harmonic_freq:.3f}")
                print(f"    Context 4D: {v.context_vector}")
                body_preview = v.body[:80].replace("\n", " ")
                print(f"    Body: {body_preview}...")
                print()

        # Export
        count = spinner.export_to_queue(variations)
        print(f"  Exported {count} variations to artifacts/spin_queue/")
        print(f"{'='*70}")

    elif cmd == "graph":
        graph = spinner.graph
        print(f"\n{'='*70}")
        print(f"  TOPIC GRAPH ({len(graph.topic_graph)} nodes)")
        print(f"{'='*70}")
        for topic, adjacents in sorted(graph.topic_graph.items()):
            print(f"  {topic}")
            for adj in adjacents:
                print(f"    -> {adj}")
        print(f"\n  Total edges: {sum(len(v) for v in graph.topic_graph.values())}")
        print(f"{'='*70}")

    elif cmd == "relay":
        topic = sys.argv[2] if len(sys.argv) > 2 else "ai_governance"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3

        chains = spinner.graph.fibonacci_relay(topic, depth=depth)
        print(f"\n{'='*70}")
        print(f"  FIBONACCI RELAY CHAINS: {topic} (depth={depth})")
        print(f"  {len(chains)} chains generated")
        print(f"{'='*70}")
        for i, chain in enumerate(chains):
            looped = " [LOOP]" if chain[-1] == chain[0] and len(chain) > 1 else ""
            print(f"  Chain {i+1}: {' -> '.join(chain)}{looped}")
        print(f"{'='*70}")

    elif cmd == "batch":
        print("\nSpinning all revenue engine seeds...")
        variations = spinner.spin_all_seeds(depth=2)

        # Summary
        by_topic: Dict[str, int] = {}
        by_platform: Dict[str, int] = {}
        for v in variations:
            by_topic[v.topic] = by_topic.get(v.topic, 0) + 1
            by_platform[v.platform] = by_platform.get(v.platform, 0) + 1

        print(f"\n{'='*70}")
        print(f"  BATCH SPIN RESULTS: {len(variations)} total variations")
        print(f"{'='*70}")
        print(f"\n  By Topic:")
        for topic, count in sorted(by_topic.items()):
            print(f"    {topic}: {count}")
        print(f"\n  By Platform:")
        for platform, count in sorted(by_platform.items()):
            print(f"    {platform}: {count}")

        count = spinner.export_to_queue(variations)
        print(f"\n  Exported {count} variations to artifacts/spin_queue/")
        print(f"{'='*70}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
