#!/usr/bin/env python3
"""Geometric Route Tagger — tags every interaction with its optimal thought-path.

Classifies prompts by dominant tongue, selects minimum-energy polyhedron,
computes geodesic adherence, and generates SFT + DPO training pairs
that teach AI to think efficiently through geometry.

Usage:
    from scripts.route_tagger import RouteTagger
    tagger = RouteTagger()
    tag = tagger.tag("What is the harmonic wall formula?", "H(d,R) = R^(d^2)...")
    # tag.tongue = "RU", tag.polyhedron = "dodecahedron", tag.energy = 2.0, tag.tpe = 0.85
"""

import json
import math
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTE_LOG = REPO_ROOT / "training-data" / "sft" / "route_tagged_sft.jsonl"
DPO_LOG = REPO_ROOT / "training-data" / "dpo" / "route_efficiency_dpo.jsonl"

# ── Tongue classifier keywords ──

TONGUE_KEYWORDS = {
    "KO": {
        "keywords": [
            "what is", "define", "list", "show", "status", "hello", "help",
            "explain", "describe", "tell me", "who", "where", "when",
            "get", "fetch", "retrieve", "lookup", "find",
        ],
        "weight": 1.0,
        "domain": "control",
        "neurotransmitter": "dopamine",
        "color": "#8B0000",
    },
    "AV": {
        "keywords": [
            "read", "write", "file", "input", "output", "import", "export",
            "load", "save", "stream", "pipe", "transfer", "send", "receive",
            "upload", "download", "copy", "move", "sync",
        ],
        "weight": 1.618,
        "domain": "io_phase",
        "neurotransmitter": "acetylcholine",
        "color": "#FFBF00",
    },
    "RU": {
        "keywords": [
            "policy", "rule", "safe", "secure", "allow", "deny", "block",
            "permission", "access", "guard", "validate", "check", "verify",
            "audit", "compliance", "governance", "energy", "cost",
        ],
        "weight": 2.618,
        "domain": "policy_energy",
        "neurotransmitter": "GABA",
        "color": "#50C878",
    },
    "CA": {
        "keywords": [
            "calculate", "compute", "algorithm", "logic", "function", "code",
            "implement", "build", "create", "generate", "transform", "parse",
            "compile", "execute", "run", "test", "debug", "fix", "refactor",
            "optimize", "class", "method", "api",
        ],
        "weight": 4.236,
        "domain": "logic_compute",
        "neurotransmitter": "glutamate",
        "color": "#0F52BA",
    },
    "UM": {
        "keywords": [
            "encrypt", "decrypt", "key", "token", "secret", "credential",
            "auth", "trust", "identity", "certificate", "sign", "hash",
            "pqc", "quantum", "kyber", "dilithium", "geoseal", "seal",
        ],
        "weight": 6.854,
        "domain": "security_trust",
        "neurotransmitter": "serotonin",
        "color": "#9966CC",
    },
    "DR": {
        "keywords": [
            "architecture", "redesign", "restructure", "migrate", "rewrite",
            "schema", "type", "model", "manifold", "topology", "geometry",
            "axiom", "proof", "theorem", "layer", "pipeline", "framework",
            "specification", "canon", "fundamental",
        ],
        "weight": 11.09,
        "domain": "deep_structure",
        "neurotransmitter": "noradrenaline",
        "color": "#3D3D3D",
    },
}

# ── Polyhedra energy table ──

POLYHEDRA = [
    {"name": "tetrahedron", "family": "platonic", "energy": 1.0, "complexity": "trivial"},
    {"name": "cube", "family": "platonic", "energy": 1.5, "complexity": "simple"},
    {"name": "octahedron", "family": "platonic", "energy": 1.8, "complexity": "simple"},
    {"name": "dodecahedron", "family": "platonic", "energy": 2.0, "complexity": "standard"},
    {"name": "icosahedron", "family": "platonic", "energy": 2.5, "complexity": "standard"},
    {"name": "truncated_icosahedron", "family": "archimedean", "energy": 4.0, "complexity": "complex"},
    {"name": "square_gyrobicupola", "family": "johnson", "energy": 5.0, "complexity": "complex"},
    {"name": "rhombicosidodecahedron", "family": "archimedean", "energy": 5.5, "complexity": "complex"},
    {"name": "rhombic_dodecahedron", "family": "rhombic", "energy": 6.0, "complexity": "complex"},
    {"name": "snub_dodecahedron", "family": "archimedean", "energy": 7.0, "complexity": "complex"},
    {"name": "pentagonal_orthobirotunda", "family": "johnson", "energy": 7.0, "complexity": "complex"},
    {"name": "rhombic_triacontahedron", "family": "rhombic", "energy": 8.0, "complexity": "deep"},
    {"name": "genus1_torus", "family": "toroidal", "energy": 8.0, "complexity": "deep"},
    {"name": "hexagonal_torus", "family": "toroidal", "energy": 10.0, "complexity": "deep"},
    {"name": "small_stellated_dodecahedron", "family": "kepler_poinsot", "energy": 12.0, "complexity": "adversarial"},
    {"name": "great_stellated_dodecahedron", "family": "kepler_poinsot", "energy": 15.0, "complexity": "adversarial"},
]

# ── Complexity estimator ──

def estimate_complexity(text: str) -> str:
    """Estimate thought complexity from text length and structure."""
    words = len(text.split())
    has_code = bool(re.search(r'[{}\[\]();=]|def |class |function |import ', text))
    has_math = bool(re.search(r'[=+\-*/^].*[=+\-*/^]|\d+\.\d+|sum|integral|matrix', text, re.I))
    has_multi_step = text.count("?") > 1 or text.count("\n") > 3
    question_marks = text.count("?")

    if words < 10 and question_marks <= 1:
        return "trivial"
    if words < 30 and not has_code and not has_math:
        return "simple"
    if words < 100 and not has_multi_step:
        return "standard"
    if has_code or has_math or has_multi_step:
        return "complex"
    if words > 200:
        return "deep"
    return "standard"


@dataclass
class RouteTag:
    """Complete geometric route tag for a thought."""
    tongue: str
    tongue_weight: float
    tongue_domain: str
    tongue_scores: dict
    polyhedron: str
    polyhedron_family: str
    energy: float
    energy_optimal: float
    complexity: str
    gateway: int  # 1, 2, or 3
    mera_level: int  # 0-3
    geodesic_adherence: float
    hausdorff_roughness: float
    tpe: float  # Thought Processing Efficiency
    rqs: float  # Route Quality Score
    tongues_active: list
    tongues_null: list
    view_type: str  # full, partial, null-heavy
    governance: str  # ALLOW, QUARANTINE, DENY
    timestamp: str


class RouteTagger:
    """Tag every interaction with its geometric route through SCBE."""

    def __init__(self):
        self.route_log = ROUTE_LOG
        self.dpo_log = DPO_LOG
        self.route_log.parent.mkdir(parents=True, exist_ok=True)
        self.dpo_log.parent.mkdir(parents=True, exist_ok=True)

    def classify_tongue(self, text: str) -> tuple[str, dict]:
        """Classify dominant tongue from text content."""
        text_lower = text.lower()
        scores = {}

        for tongue, info in TONGUE_KEYWORDS.items():
            score = sum(1 for kw in info["keywords"] if kw in text_lower)
            # Weight by tongue cost (cheaper tongues are preferred)
            scores[tongue] = score

        # Default to KO (cheapest) if no keywords match
        if all(v == 0 for v in scores.values()):
            return "KO", scores

        dominant = max(scores, key=lambda k: scores[k])
        # If tie between multiple tongues, prefer the cheapest
        max_score = scores[dominant]
        tied = [t for t, s in scores.items() if s == max_score]
        if len(tied) > 1:
            dominant = min(tied, key=lambda t: TONGUE_KEYWORDS[t]["weight"])

        return dominant, scores

    def select_polyhedron(self, tongue: str, complexity: str) -> dict:
        """Select minimum-energy polyhedron for given tongue and complexity."""
        # Filter polyhedra by complexity level
        valid = [p for p in POLYHEDRA if p["complexity"] == complexity]
        if not valid:
            # Fall back to closest complexity
            complexity_order = ["trivial", "simple", "standard", "complex", "deep"]
            idx = complexity_order.index(complexity) if complexity in complexity_order else 2
            for offset in [0, -1, 1, -2, 2]:
                check = max(0, min(len(complexity_order) - 1, idx + offset))
                valid = [p for p in POLYHEDRA if p["complexity"] == complexity_order[check]]
                if valid:
                    break
        if not valid:
            valid = [POLYHEDRA[0]]  # Tetrahedron fallback

        # Select cheapest valid polyhedron
        return min(valid, key=lambda p: p["energy"])

    def compute_optimal_energy(self, complexity: str) -> float:
        """Minimum possible energy for a given complexity level."""
        valid = [p for p in POLYHEDRA if p["complexity"] == complexity]
        if not valid:
            return 1.0
        return min(p["energy"] for p in valid)

    def select_gateway(self, tongue: str) -> int:
        """Map tongue to nearest geodesic gateway (1, 2, or 3)."""
        # Gateway 1: Direct factual (KO, AV)
        # Gateway 2: Analytical (RU, CA)
        # Gateway 3: Creative/structural (UM, DR)
        mapping = {"KO": 1, "AV": 1, "RU": 2, "CA": 2, "UM": 3, "DR": 3}
        return mapping.get(tongue, 1)

    def compute_mera_level(self, complexity: str, tongue: str) -> int:
        """Minimum MERA compression level needed.

        Level 0: Full 6-channel (only for deep/adversarial)
        Level 1: 3-channel paired (complex operations)
        Level 2: 3-abstract (standard operations)
        Level 3: 1-decision (trivial/simple)
        """
        complexity_to_level = {
            "trivial": 3,
            "simple": 3,
            "standard": 2,
            "complex": 1,
            "deep": 0,
            "adversarial": 0,
        }
        return complexity_to_level.get(complexity, 2)

    def compute_adherence(self, tongue: str, polyhedron: dict) -> float:
        """How well the route follows the geodesic highway (0-1)."""
        # Platonic paths on cheap tongues = high adherence
        # Expensive polyhedra on cheap tongues = low adherence (mismatch)
        tongue_weight = TONGUE_KEYWORDS[tongue]["weight"]
        energy = polyhedron["energy"]
        # Adherence drops when energy exceeds what tongue weight suggests
        ratio = tongue_weight / max(energy, 0.1)
        return min(1.0, max(0.1, ratio))

    def compute_roughness(self, response_len: int, complexity: str) -> float:
        """Estimate Hausdorff roughness from response characteristics."""
        # Longer responses for simple tasks = rougher path (over-thinking)
        expected_len = {"trivial": 50, "simple": 150, "standard": 400, "complex": 800, "deep": 1500}
        expected = expected_len.get(complexity, 400)
        if response_len == 0:
            return 1.0
        ratio = response_len / expected
        if ratio > 3.0:
            return min(5.0, 1.0 + ratio)
        if ratio < 0.3:
            return 1.0 + (1.0 / max(ratio, 0.1))
        return max(1.0, ratio)

    def compute_active_tongues(self, scores: dict) -> tuple[list, list]:
        """Determine which tongues are active vs null."""
        active = [t for t, s in scores.items() if s > 0]
        null = [t for t, s in scores.items() if s == 0]
        return active, null

    def determine_view_type(self, active: list, null: list) -> str:
        """Classify the view type based on tongue activation."""
        if len(active) >= 5:
            return "full"
        if len(null) >= 4:
            return "null-heavy"
        return "partial"

    def tag(self, prompt: str, response: str, layer: str = "L2") -> RouteTag:
        """Tag a prompt-response pair with its geometric route."""
        tongue, scores = self.classify_tongue(prompt)
        complexity = estimate_complexity(prompt)
        polyhedron = self.select_polyhedron(tongue, complexity)
        gateway = self.select_gateway(tongue)
        mera_level = self.compute_mera_level(complexity, tongue)
        adherence = self.compute_adherence(tongue, polyhedron)
        roughness = self.compute_roughness(len(response), complexity)
        optimal_energy = self.compute_optimal_energy(complexity)
        active, null = self.compute_active_tongues(scores)
        view_type = self.determine_view_type(active, null)

        energy = polyhedron["energy"]
        energy_waste = max(0, energy - optimal_energy) / max(energy, 0.1)
        tpe = (optimal_energy / max(energy, 0.1)) * adherence * (1.0 / max(mera_level, 1))
        tpe = min(1.0, tpe)
        rqs = (1.0 / (1.0 + roughness)) * (1.0 - energy_waste)

        # Governance from harmonic wall
        value = 1.0 / (1.0 + energy * roughness * 0.1)
        if value >= 0.7:
            governance = "ALLOW"
        elif value >= 0.3:
            governance = "QUARANTINE"
        else:
            governance = "DENY"

        return RouteTag(
            tongue=tongue,
            tongue_weight=TONGUE_KEYWORDS[tongue]["weight"],
            tongue_domain=TONGUE_KEYWORDS[tongue]["domain"],
            tongue_scores=scores,
            polyhedron=polyhedron["name"],
            polyhedron_family=polyhedron["family"],
            energy=energy,
            energy_optimal=optimal_energy,
            complexity=complexity,
            gateway=gateway,
            mera_level=mera_level,
            geodesic_adherence=round(adherence, 4),
            hausdorff_roughness=round(roughness, 4),
            tpe=round(tpe, 4),
            rqs=round(rqs, 4),
            tongues_active=active,
            tongues_null=null,
            view_type=view_type,
            governance=governance,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def log_sft(self, prompt: str, response: str, tag: RouteTag) -> dict:
        """Log a route-tagged SFT training pair."""
        record = {
            "instruction": prompt[:500],
            "output": response[:1000],
            "tongue": tag.tongue,
            "tongue_weight": tag.tongue_weight,
            "tongue_domain": tag.tongue_domain,
            "tongues_active": tag.tongues_active,
            "tongues_null": tag.tongues_null,
            "polyhedron": tag.polyhedron,
            "polyhedron_family": tag.polyhedron_family,
            "energy": tag.energy,
            "energy_optimal": tag.energy_optimal,
            "complexity": tag.complexity,
            "gateway": tag.gateway,
            "mera_level": tag.mera_level,
            "geodesic_adherence": tag.geodesic_adherence,
            "hausdorff_roughness": tag.hausdorff_roughness,
            "tpe": tag.tpe,
            "rqs": tag.rqs,
            "view_type": tag.view_type,
            "governance": tag.governance,
            "layer": "L2",
            "source": "route_tagger",
            "timestamp": tag.timestamp,
        }

        with open(self.route_log, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record

    def log_dpo(self, prompt: str, efficient_response: str, wasteful_response: str,
                efficient_tag: RouteTag, wasteful_tag: RouteTag) -> dict:
        """Log a DPO pair: efficient vs wasteful route for same prompt."""
        record = {
            "prompt": prompt[:500],
            "chosen": {
                "response": efficient_response[:1000],
                "route": f"{efficient_tag.tongue} -> {efficient_tag.polyhedron} -> Gateway{efficient_tag.gateway} -> Level{efficient_tag.mera_level}",
                "energy": efficient_tag.energy,
                "tpe": efficient_tag.tpe,
                "rqs": efficient_tag.rqs,
            },
            "rejected": {
                "response": wasteful_response[:1000],
                "route": f"{wasteful_tag.tongue} -> {wasteful_tag.polyhedron} -> Gateway{wasteful_tag.gateway} -> Level{wasteful_tag.mera_level}",
                "energy": wasteful_tag.energy,
                "tpe": wasteful_tag.tpe,
                "rqs": wasteful_tag.rqs,
            },
            "efficiency_gain": round(wasteful_tag.energy / max(efficient_tag.energy, 0.1), 2),
            "source": "route_tagger_dpo",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with open(self.dpo_log, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record

    def tag_and_log(self, prompt: str, response: str) -> RouteTag:
        """Tag and log in one call."""
        tag = self.tag(prompt, response)
        self.log_sft(prompt, response, tag)
        return tag


# ── Demo / self-test ──

if __name__ == "__main__":
    tagger = RouteTagger()

    demos = [
        ("What is SCBE?", "SCBE is an AI safety framework using hyperbolic geometry."),
        ("Read the file at src/harmonic/phdm.ts", "The PHDM module defines 16 polyhedra..."),
        ("Is this API endpoint safe to expose publicly?", "No, it exposes internal governance state. Add authentication middleware and rate limiting."),
        ("Implement a function that computes the harmonic wall H(d,R) = R^(d^2)", "def harmonic_wall(d, R): return R ** (d ** 2)"),
        ("Encrypt this message with ML-KEM-768", "Encapsulated using post-quantum KEM with shared secret derivation..."),
        ("Redesign the 14-layer pipeline to support streaming", "This requires fundamental changes to layers L1-L4 realification, adding async generators at each stage, modifying the Poincare embedding to support incremental updates, and restructuring the harmonic wall to evaluate partial states."),
    ]

    print(f"{'Prompt':<50} {'Tongue':>6} {'Poly':<20} {'E':>5} {'TPE':>6} {'RQS':>6} {'Gov':<12}")
    print("-" * 115)

    for prompt, response in demos:
        tag = tagger.tag_and_log(prompt, response)
        print(f"{prompt[:48]:<50} {tag.tongue:>6} {tag.polyhedron:<20} {tag.energy:>5.1f} {tag.tpe:>6.3f} {tag.rqs:>6.3f} {tag.governance:<12}")

    print(f"\nLogged {len(demos)} route-tagged SFT pairs to {ROUTE_LOG}")
    print(f"Active tongues / null tongues per record:")
    for prompt, response in demos:
        tag = tagger.tag(prompt, response)
        print(f"  {prompt[:40]:<42} active={tag.tongues_active}  null={tag.tongues_null}  view={tag.view_type}")
