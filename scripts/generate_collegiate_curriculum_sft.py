#!/usr/bin/env python3
"""
Collegiate Curriculum Sweep — Grade-Level Classification & Multi-Angle Expansion
=================================================================================
Takes the existing SFT corpus, classifies every record into an academic grade
level based on topic complexity + learning intent, stages a curriculum path,
expands advanced topics with multi-angle contrastive training, and cross-relates
from convergent AND convexly opposed perspectives.

Grade Levels:
    100-level: Introductory (high school → freshman)
    200-level: Intermediate (sophomore → junior)
    300-level: Advanced undergraduate (junior → senior)
    400-level: Graduate seminar
    500-level: Research frontier / doctoral

Curriculum Stages:
    FOUNDATION  → EXPLORATION → SYNTHESIS → CRITIQUE → FRONTIER

Multi-Angle Expansion:
    For each 300+ record, generate views from:
    - Convergent angle: different discipline, same conclusion
    - Opposed angle: same discipline, inverse thesis
    - Orthogonal angle: unrelated field that maps structurally

Output: training-data/sft/collegiate_curriculum_sft.jsonl
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.trit_curriculum import compute_trit_signal
from src.crypto.multipath_generator import compute_multipath

# ---------------------------------------------------------------------------
# Grade-level indicators
# ---------------------------------------------------------------------------

# Complexity markers: words/phrases that signal academic depth
COMPLEXITY_MARKERS = {
    # 100-level: basic concepts, definitions, "what is"
    100: [
        "what is", "how to", "introduction", "basics", "getting started",
        "hello world", "first steps", "beginner", "tutorial", "overview",
        "simple", "easy", "fundamental", "basic concept",
    ],
    # 200-level: applied knowledge, comparisons, tradeoffs
    200: [
        "compare", "tradeoff", "implement", "design pattern", "architecture",
        "workflow", "pipeline", "integration", "configuration", "deploy",
        "optimize", "debug", "refactor", "api", "database", "middleware",
        "authentication", "authorization", "caching", "scaling",
    ],
    # 300-level: theory + practice, proofs, formal methods
    300: [
        "theorem", "proof", "formal", "invariant", "convergence",
        "complexity", "asymptotic", "polynomial", "exponential",
        "bijective", "injective", "surjective", "isomorphism",
        "eigenvalue", "eigenvector", "manifold", "topology",
        "lattice", "group theory", "ring", "field theory",
        "homomorphism", "functor", "category theory", "monad",
        "cryptographic", "post-quantum", "zero-knowledge",
    ],
    # 400-level: research synthesis, cross-domain, novel frameworks
    400: [
        "hypothesis", "conjecture", "open problem", "novel",
        "cross-domain", "interdisciplinary", "emergent", "meta-",
        "non-trivial", "higher-order", "compositional",
        "adversarial", "generalization", "transfer learning",
        "governance", "axiom", "unitarity", "causality",
        "hyperbolic", "poincare", "harmonic wall",
    ],
    # 500-level: frontier, unsolved, paradigm-shifting
    500: [
        "riemann", "zeta function", "p vs np", "quantum gravity",
        "consciousness", "toroidal", "polyhedral confinement",
        "phi-scaled", "sacred tongue", "triadic temporal",
        "multi-path", "polymorphic boundary", "monty hall",
        "spectral coherence", "spin coherence", "sacred egg",
        "21-dimensional", "47-dimensional", "world tree",
    ],
}

# Topic domains that map to academic departments
TOPIC_DOMAINS = {
    "computer_science": [
        "algorithm", "data structure", "compiler", "operating system",
        "network", "distributed", "database", "concurrency",
        "machine learning", "neural network", "transformer",
    ],
    "mathematics": [
        "theorem", "proof", "algebra", "topology", "geometry",
        "analysis", "number theory", "combinatorics", "statistics",
        "calculus", "differential", "integral", "manifold",
    ],
    "physics": [
        "quantum", "relativity", "thermodynamic", "entropy",
        "hamiltonian", "lagrangian", "wave function", "spin",
        "coherence", "interference", "diffraction",
    ],
    "philosophy": [
        "epistemology", "ontology", "ethics", "consciousness",
        "truth", "beauty", "good", "existence", "meaning",
        "free will", "determinism", "emergence",
    ],
    "security": [
        "cryptograph", "cipher", "hash", "signature", "key exchange",
        "zero-knowledge", "post-quantum", "adversarial", "threat",
        "governance", "compliance", "audit",
    ],
    "creative_writing": [
        "story", "narrative", "character", "world-building", "lore",
        "magic system", "quest", "guild", "realm", "prophecy",
        "rune", "tongue", "sacred", "ritual", "myth",
    ],
    "engineering": [
        "architecture", "pipeline", "deploy", "docker", "kubernetes",
        "api", "microservice", "monitoring", "ci/cd", "testing",
        "infrastructure", "scalability",
    ],
    "interdisciplinary": [
        "cross-domain", "hybrid", "convergence", "intersection",
        "analogy", "metaphor", "bridge", "translation", "mapping",
    ],
}

# Curriculum stages with learning intent
CURRICULUM_STAGES = {
    "FOUNDATION": {
        "grade_range": (100, 199),
        "intent": "Build vocabulary and mental models. The learner should leave with correct definitions and the ability to recognize patterns.",
        "verb": "define, identify, describe, list, recognize",
    },
    "EXPLORATION": {
        "grade_range": (200, 299),
        "intent": "Apply knowledge to real problems. The learner should leave able to implement, compare alternatives, and explain tradeoffs.",
        "verb": "implement, compare, analyze, apply, evaluate",
    },
    "SYNTHESIS": {
        "grade_range": (300, 399),
        "intent": "Combine ideas across domains. The learner should leave able to prove, derive, connect distant concepts, and build novel frameworks.",
        "verb": "synthesize, derive, prove, construct, integrate",
    },
    "CRITIQUE": {
        "grade_range": (400, 499),
        "intent": "Challenge assumptions and find limits. The learner should leave able to identify failure modes, propose alternatives, and defend positions.",
        "verb": "critique, challenge, defend, extend, reframe",
    },
    "FRONTIER": {
        "grade_range": (500, 599),
        "intent": "Push beyond known boundaries. The learner should leave with original questions, novel hypotheses, and the tools to test them.",
        "verb": "hypothesize, discover, pioneer, formalize, transcend",
    },
}

# Multi-angle expansion templates
CONVERGENT_ANGLES = {
    "computer_science": {
        "mathematics": "the same structure appears in {topic} when viewed through {math_lens} — the isomorphism is {connection}",
        "physics": "computationally, {topic} mirrors {physics_analog} — both minimize a cost function over a constraint surface",
        "philosophy": "the computational perspective on {topic} resolves the philosophical tension between {pole_a} and {pole_b}",
    },
    "mathematics": {
        "physics": "{topic} provides the geometric substrate for {physics_analog} — the theorem IS the physical law",
        "computer_science": "algorithmically, {topic} becomes {cs_analog} — what mathematicians prove, engineers implement",
        "creative_writing": "the narrative structure of {topic} follows {math_pattern} — story arcs obey the same topology as proofs",
    },
    "physics": {
        "mathematics": "the physics of {topic} is best expressed through {math_framework} — nature chose the optimal formalism",
        "engineering": "engineering {topic} requires understanding the physical constraints: {constraint_list}",
    },
    "security": {
        "mathematics": "the security of {topic} reduces to the hardness of {math_problem}",
        "physics": "adversarial cost in {topic} scales like {physics_analog} — exponential barriers are physical, not arbitrary",
    },
    "creative_writing": {
        "philosophy": "the lore of {topic} encodes {philosophical_principle} — world-building IS applied ontology",
        "mathematics": "the magic system in {topic} obeys {math_constraint} — narrative consistency requires formal structure",
    },
}

OPPOSED_ANGLES = [
    ("The standard view holds {thesis}. But inverting the assumption reveals {antithesis}. "
     "The productive tension between these views is where {synthesis} emerges."),
    ("If {thesis}, then we expect {prediction}. But observed behavior shows {counter_evidence}. "
     "This forces us to reconsider whether {assumption} actually holds."),
    ("Most treatments of {topic} assume {assumption}. The convex opposite — {negation} — "
     "produces a dual framework where {dual_consequence}. Both views are needed."),
    ("{topic} succeeds because it exploits {mechanism}. But the same mechanism, "
     "pushed past its convergence radius, produces {failure_mode}. Understanding "
     "BOTH the success and the failure teaches the boundary."),
]


# ---------------------------------------------------------------------------
# Grade classifier
# ---------------------------------------------------------------------------

@dataclass
class GradeAssignment:
    """A record's academic grade-level classification."""
    grade: int                    # 100, 200, 300, 400, 500
    stage: str                    # FOUNDATION, EXPLORATION, etc.
    confidence: float             # 0.0 to 1.0
    domains: List[str]            # detected topic domains
    complexity_hits: Dict[int, int]  # grade -> number of marker hits
    learning_intent: str          # what the learner should gain
    expansion_eligible: bool      # True if grade >= 300 (expand with angles)


def classify_grade(text: str) -> GradeAssignment:
    """Classify a text into an academic grade level."""
    text_lower = text.lower()
    text_len = len(text)

    # Count complexity marker hits per grade
    hits: Dict[int, int] = {}
    for grade, markers in COMPLEXITY_MARKERS.items():
        count = sum(1 for m in markers if m in text_lower)
        if count > 0:
            hits[grade] = count

    # Detect topic domains
    domains = []
    for domain, keywords in TOPIC_DOMAINS.items():
        domain_hits = sum(1 for k in keywords if k in text_lower)
        if domain_hits >= 2:
            domains.append(domain)
        elif domain_hits == 1 and len(text_lower) < 500:
            domains.append(domain)

    if not domains:
        domains = ["general"]

    # Compute weighted grade
    if hits:
        # Higher grades get exponentially more weight per hit
        weighted_sum = 0.0
        total_weight = 0.0
        for grade, count in hits.items():
            w = count * (grade / 100.0)  # higher grades amplified
            weighted_sum += grade * w
            total_weight += w
        raw_grade = weighted_sum / total_weight if total_weight > 0 else 200
    else:
        raw_grade = 200  # default to intermediate

    # Adjust by text length (longer = more complex, generally)
    if text_len > 2000:
        raw_grade += 30
    elif text_len > 1000:
        raw_grade += 15
    elif text_len < 200:
        raw_grade -= 20

    # Adjust by domain count (more domains = more interdisciplinary = higher)
    if len(domains) >= 3:
        raw_grade += 50
    elif len(domains) >= 2:
        raw_grade += 25

    # Quantize to nearest 100-level
    grade = max(100, min(500, round(raw_grade / 100) * 100))

    # Determine curriculum stage
    for stage_name, stage_info in CURRICULUM_STAGES.items():
        lo, hi = stage_info["grade_range"]
        if lo <= grade <= hi:
            stage = stage_name
            intent = stage_info["intent"]
            break
    else:
        stage = "FRONTIER"
        intent = CURRICULUM_STAGES["FRONTIER"]["intent"]

    # Confidence: how many markers actually hit vs total possible
    sum(len(m) for m in COMPLEXITY_MARKERS.values())
    total_hits = sum(hits.values())
    confidence = min(1.0, total_hits / 5.0)  # 5+ hits = confident

    return GradeAssignment(
        grade=grade,
        stage=stage,
        confidence=confidence,
        domains=domains,
        complexity_hits=hits,
        learning_intent=intent,
        expansion_eligible=grade >= 300,
    )


# ---------------------------------------------------------------------------
# Multi-angle expansion
# ---------------------------------------------------------------------------

def generate_convergent_view(
    text: str,
    grade: GradeAssignment,
    record_hash: str,
) -> Optional[dict]:
    """Generate a convergent-angle view: different discipline, same conclusion."""
    if not grade.expansion_eligible or len(grade.domains) < 1:
        return None

    primary_domain = grade.domains[0]
    # Pick a convergent domain deterministically
    h = int(hashlib.md5((record_hash + "convergent").encode()).hexdigest(), 16)

    # Find a domain that ISN'T the primary
    all_domains = list(TOPIC_DOMAINS.keys())
    other_domains = [d for d in all_domains if d != primary_domain]
    if not other_domains:
        return None
    conv_domain = other_domains[h % len(other_domains)]

    # Build the cross-domain framing
    topic_excerpt = text[:120].strip()
    stage_verbs = CURRICULUM_STAGES[grade.stage]["verb"]

    user_content = (
        f"[{grade.grade}-level | {grade.stage} | Convergent cross-domain]\n\n"
        f"The following concept from {primary_domain.replace('_', ' ')} also appears "
        f"in {conv_domain.replace('_', ' ')}. Explain the convergence.\n\n"
        f"Original framing: \"{topic_excerpt}...\"\n\n"
        f"Learning objective: {stage_verbs.split(', ')[0]} the structural parallel "
        f"between the {primary_domain.replace('_', ' ')} and "
        f"{conv_domain.replace('_', ' ')} perspectives."
    )

    # Generate response based on grade level
    if grade.grade >= 500:
        depth = "frontier"
        style = (
            f"At the research frontier, the convergence between "
            f"{primary_domain.replace('_', ' ')} and {conv_domain.replace('_', ' ')} "
            f"is not metaphorical — it is structural. Both disciplines arrive at "
            f"the same formal object through different construction paths.\n\n"
        )
    elif grade.grade >= 400:
        depth = "graduate"
        style = (
            f"A graduate-level analysis reveals that {primary_domain.replace('_', ' ')} "
            f"and {conv_domain.replace('_', ' ')} share an underlying categorical structure. "
            f"The morphisms between them preserve the essential properties.\n\n"
        )
    elif grade.grade >= 300:
        depth = "advanced_undergrad"
        style = (
            f"At the advanced undergraduate level, we can see that "
            f"{primary_domain.replace('_', ' ')} and {conv_domain.replace('_', ' ')} "
            f"approach the same problem from different starting axioms, yet arrive "
            f"at compatible conclusions.\n\n"
        )
    else:
        return None  # Only expand 300+

    # Extract key concepts from original text for grounding
    words = text.split()
    key_terms = [w for w in words if len(w) > 6 and w.isalpha()][:5]
    term_list = ", ".join(key_terms) if key_terms else "the core concepts"

    assistant_content = (
        f"{style}"
        f"The key terms — {term_list} — map naturally into "
        f"{conv_domain.replace('_', ' ')} as follows:\n\n"
        f"In {primary_domain.replace('_', ' ')}, these represent operational primitives. "
        f"In {conv_domain.replace('_', ' ')}, the same structure manifests as "
        f"{'constraint surfaces' if conv_domain == 'mathematics' else 'behavioral invariants' if conv_domain == 'physics' else 'design patterns' if conv_domain == 'engineering' else 'narrative arcs' if conv_domain == 'creative_writing' else 'epistemological commitments' if conv_domain == 'philosophy' else 'threat boundaries' if conv_domain == 'security' else 'applied frameworks'}. "
        f"The convergence is productive because it means insights from either domain "
        f"transfer directly — a proof in one becomes an implementation guide in the other.\n\n"
        f"This cross-domain alignment is not coincidence. It reflects the fact that "
        f"both disciplines are modeling the same underlying structure: the relationship "
        f"between constraint, freedom, and optimal paths through high-dimensional spaces."
    )

    trit = compute_trit_signal(user_content[:256])
    mp = compute_multipath(trit)

    return {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "source": "collegiate_curriculum_sweep",
            "record_type": "convergent_cross_domain",
            "grade": grade.grade,
            "stage": grade.stage,
            "primary_domain": primary_domain,
            "convergent_domain": conv_domain,
            "depth": depth,
            "parent_hash": record_hash,
            "trit_signal": trit.to_dict(),
            "multipath": mp.to_dict(),
        },
    }


def generate_opposed_view(
    text: str,
    grade: GradeAssignment,
    record_hash: str,
) -> Optional[dict]:
    """Generate a convexly opposed view: same domain, inverse thesis."""
    if not grade.expansion_eligible:
        return None

    primary_domain = grade.domains[0]
    h = int(hashlib.md5((record_hash + "opposed").encode()).hexdigest(), 16)
    OPPOSED_ANGLES[h % len(OPPOSED_ANGLES)]

    topic_excerpt = text[:120].strip()
    stage_verbs = CURRICULUM_STAGES[grade.stage]["verb"]

    user_content = (
        f"[{grade.grade}-level | {grade.stage} | Convexly opposed]\n\n"
        f"Present the inverse thesis of the following claim, then show how "
        f"the tension between thesis and antithesis produces a deeper understanding.\n\n"
        f"Claim: \"{topic_excerpt}...\"\n\n"
        f"Learning objective: {stage_verbs.split(', ')[-1]} the productive tension "
        f"between the claim and its negation."
    )

    # Build the opposed analysis
    words = [w for w in text.split() if len(w) > 5 and w.isalpha()][:6]
    key_claim = " ".join(words[:3]) if len(words) >= 3 else "this framework"
    opposing = " ".join(words[3:6]) if len(words) >= 6 else "the alternative view"

    if grade.grade >= 500:
        assistant_content = (
            f"The claim asserts that {key_claim} provides the correct frame. "
            f"The convex opposite — that {opposing} is the fundamental object, "
            f"and {key_claim} is merely a projection — deserves equal formal treatment.\n\n"
            f"Thesis: The original framing succeeds because it privileges "
            f"the structure that is locally observable. Within its convergence radius, "
            f"every prediction checks out.\n\n"
            f"Antithesis: But the same structure, examined from the dual perspective, "
            f"reveals that what appeared fundamental is actually derived. "
            f"The opposing view has its own convergence radius, and where the two "
            f"radii overlap is precisely where the deepest insights live.\n\n"
            f"Synthesis: The productive move is not to pick a side but to "
            f"characterize the BOUNDARY between the two convergence regions. "
            f"This boundary is a polymorphic zone — the exact territory where "
            f"the multipath generator finds its highest Monty Hall advantage. "
            f"Both thesis and antithesis are correct within their domains; "
            f"the curriculum value is in learning to navigate the transition.\n\n"
            f"At the research frontier, the ability to hold two convexly opposed "
            f"views simultaneously — and to identify which one applies given "
            f"specific boundary conditions — is the definition of expertise."
        )
    elif grade.grade >= 400:
        assistant_content = (
            f"The standard treatment presents {key_claim} as settled. "
            f"A graduate seminar should challenge this.\n\n"
            f"The thesis succeeds under specific assumptions that are rarely stated: "
            f"continuity, finite dimensionality, and the existence of a unique optimum. "
            f"Relaxing any of these assumptions produces a different optimal strategy.\n\n"
            f"The antithesis — that {opposing} provides a more robust foundation — "
            f"is not merely contrarian. It emerges naturally when we consider edge cases "
            f"where the original assumptions break down.\n\n"
            f"The critique-level insight: the value of the antithesis is not that it "
            f"is correct, but that it MAPS the failure modes of the thesis. "
            f"Together, thesis and antithesis form a covering of the problem space "
            f"that neither achieves alone."
        )
    else:  # 300
        assistant_content = (
            f"The claim centers on {key_claim}. To understand it deeply, we need "
            f"to construct its strongest counter-argument.\n\n"
            f"The opposing view would argue that the priorities are reversed — "
            f"what the original claim treats as foundational is actually derivative, "
            f"and what it treats as secondary is the load-bearing structure.\n\n"
            f"This tension is productive. In advanced coursework, you learn more "
            f"from the boundaries between valid frameworks than from either framework "
            f"alone. The synthesis emerges when you can articulate WHEN each view "
            f"applies and WHY the boundary falls where it does.\n\n"
            f"Exercise: Identify two concrete scenarios — one where the original "
            f"claim is clearly correct, and one where the opposing view wins. "
            f"The conditions that distinguish them ARE the learning target."
        )

    trit = compute_trit_signal(user_content[:256])
    mp = compute_multipath(trit)

    return {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "source": "collegiate_curriculum_sweep",
            "record_type": "convexly_opposed",
            "grade": grade.grade,
            "stage": grade.stage,
            "primary_domain": primary_domain,
            "parent_hash": record_hash,
            "trit_signal": trit.to_dict(),
            "multipath": mp.to_dict(),
        },
    }


def generate_orthogonal_view(
    text: str,
    grade: GradeAssignment,
    record_hash: str,
) -> Optional[dict]:
    """Generate an orthogonal view: unrelated field, same structure."""
    if grade.grade < 400:
        return None  # Only for graduate+ level

    primary_domain = grade.domains[0]
    h = int(hashlib.md5((record_hash + "orthogonal").encode()).hexdigest(), 16)

    # Pick the most DISTANT domain
    distance_map = {
        "computer_science": ["creative_writing", "philosophy"],
        "mathematics": ["creative_writing", "engineering"],
        "physics": ["creative_writing", "philosophy"],
        "philosophy": ["engineering", "computer_science"],
        "security": ["creative_writing", "philosophy"],
        "creative_writing": ["mathematics", "security"],
        "engineering": ["philosophy", "creative_writing"],
        "interdisciplinary": ["security", "creative_writing"],
    }
    distant = distance_map.get(primary_domain, ["philosophy", "creative_writing"])
    ortho_domain = distant[h % len(distant)]

    topic_excerpt = text[:120].strip()

    user_content = (
        f"[{grade.grade}-level | {grade.stage} | Orthogonal mapping]\n\n"
        f"Find the structural isomorphism between the following "
        f"{primary_domain.replace('_', ' ')} concept and an analogous structure "
        f"in {ortho_domain.replace('_', ' ')}.\n\n"
        f"Source concept: \"{topic_excerpt}...\"\n\n"
        f"This is not metaphor — identify the formal correspondence."
    )

    words = [w for w in text.split() if len(w) > 5 and w.isalpha()][:4]
    concepts = ", ".join(words) if words else "the key structures"

    if grade.grade >= 500:
        assistant_content = (
            f"The structural isomorphism between {primary_domain.replace('_', ' ')} "
            f"and {ortho_domain.replace('_', ' ')} runs deeper than analogy.\n\n"
            f"The source concepts — {concepts} — have direct correspondences:\n\n"
            f"In {primary_domain.replace('_', ' ')}, the operative structure is a "
            f"constrained optimization over a high-dimensional space. "
            f"In {ortho_domain.replace('_', ' ')}, the SAME structure appears as "
            f"{'narrative tension resolving through character choices' if ortho_domain == 'creative_writing' else 'ethical dilemmas navigated through principled reasoning' if ortho_domain == 'philosophy' else 'system reliability achieved through redundancy and fault isolation' if ortho_domain == 'engineering' else 'proof construction through axiom selection' if ortho_domain == 'mathematics' else 'threat surfaces defended through layered boundaries' if ortho_domain == 'security' else 'the intersection of multiple disciplinary lenses'}.\n\n"
            f"The isomorphism preserves:\n"
            f"- The dimensionality of the choice space\n"
            f"- The existence of local optima (false resolutions)\n"
            f"- The role of constraints in making the problem tractable\n"
            f"- The phase transition between solvable and intractable regimes\n\n"
            f"This is not a teaching trick. The two domains are modeling the same "
            f"abstract object. When you solve a hard problem in one, you get the "
            f"solution in the other for free — if you can identify the morphism.\n\n"
            f"The research frontier here: systematically cataloging these cross-domain "
            f"isomorphisms creates a transfer learning substrate that no single-domain "
            f"training can match. The SCBE trit curriculum naturally detects these "
            f"structural correspondences as polymorphic boundary crossings."
        )
    else:  # 400
        assistant_content = (
            f"At graduate level, we move beyond surface analogies to formal mappings.\n\n"
            f"The concepts {concepts} in {primary_domain.replace('_', ' ')} correspond to "
            f"specific structures in {ortho_domain.replace('_', ' ')}:\n\n"
            f"The key insight is that both domains face the same fundamental challenge: "
            f"navigating a space where multiple valid states exist, and the choice between "
            f"them depends on context that isn't fully determined by the local information.\n\n"
            f"In {primary_domain.replace('_', ' ')}, this manifests as "
            f"{'algorithmic complexity' if primary_domain == 'computer_science' else 'mathematical underdetermination' if primary_domain == 'mathematics' else 'quantum superposition' if primary_domain == 'physics' else 'narrative ambiguity' if primary_domain == 'creative_writing' else 'ethical dilemmas' if primary_domain == 'philosophy' else 'attack surface analysis' if primary_domain == 'security' else 'design tradeoffs'}.\n\n"
            f"In {ortho_domain.replace('_', ' ')}, the same structure appears as "
            f"{'the reader holding multiple interpretations simultaneously' if ortho_domain == 'creative_writing' else 'the limits of formal provability' if ortho_domain == 'mathematics' else 'engineering judgment under uncertainty' if ortho_domain == 'engineering' else 'epistemological humility' if ortho_domain == 'philosophy' else 'defense in depth' if ortho_domain == 'security' else 'cross-cutting concerns'}.\n\n"
            f"The graduate exercise: construct an explicit dictionary between the two "
            f"domains. Every term in one should have a precise counterpart in the other."
        )

    trit = compute_trit_signal(user_content[:256])
    mp = compute_multipath(trit)

    return {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "source": "collegiate_curriculum_sweep",
            "record_type": "orthogonal_mapping",
            "grade": grade.grade,
            "stage": grade.stage,
            "primary_domain": primary_domain,
            "orthogonal_domain": ortho_domain,
            "parent_hash": record_hash,
            "trit_signal": trit.to_dict(),
            "multipath": mp.to_dict(),
        },
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    input_path = ROOT / "training-data" / "sft" / "claude_conversations_sft.jsonl"
    output_path = ROOT / "training-data" / "sft" / "collegiate_curriculum_sft.jsonl"
    summary_path = ROOT / "training-data" / "sft" / "collegiate_curriculum_summary.json"

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    print("=" * 70)
    print("COLLEGIATE CURRICULUM SWEEP")
    print("Grade classification + multi-angle expansion")
    print("=" * 70)
    print()

    # Load source records
    print(f"Loading: {input_path}")
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"  Loaded {len(records)} records")
    print()

    # Phase 1: Grade classification
    print("Phase 1: Grade classification...")
    grade_dist: Dict[int, int] = {100: 0, 200: 0, 300: 0, 400: 0, 500: 0}
    stage_dist: Dict[str, int] = {}
    domain_dist: Dict[str, int] = {}
    graded_records = []
    expansion_pool = []

    for i, record in enumerate(records):
        # Extract text for grading
        messages = record.get("messages", [])
        combined = ""
        for msg in messages:
            combined += msg.get("content", "") + " "
        combined = combined.strip()

        # Classify
        grade = classify_grade(combined)
        record_hash = hashlib.md5(combined[:256].encode()).hexdigest()

        # Add grade metadata to record
        record["metadata"]["collegiate"] = {
            "grade": grade.grade,
            "stage": grade.stage,
            "confidence": round(grade.confidence, 3),
            "domains": grade.domains,
            "learning_intent": grade.learning_intent,
            "expansion_eligible": grade.expansion_eligible,
        }

        graded_records.append(record)
        grade_dist[grade.grade] = grade_dist.get(grade.grade, 0) + 1
        stage_dist[grade.stage] = stage_dist.get(grade.stage, 0) + 1
        for d in grade.domains:
            domain_dist[d] = domain_dist.get(d, 0) + 1

        if grade.expansion_eligible:
            expansion_pool.append((combined, grade, record_hash))

        if (i + 1) % 500 == 0:
            print(f"  [{i + 1}/{len(records)}] classified...")

    print(f"  Grade distribution:")
    for g in sorted(grade_dist.keys()):
        pct = grade_dist[g] / len(records) * 100
        bar = "#" * int(pct / 2)
        print(f"    {g}-level: {grade_dist[g]:>5} ({pct:>5.1f}%) {bar}")
    print(f"  Expansion eligible (300+): {len(expansion_pool)}")
    print()

    # Phase 2: Multi-angle expansion
    print("Phase 2: Multi-angle expansion...")
    expanded = []
    convergent_count = 0
    opposed_count = 0
    orthogonal_count = 0

    for i, (text, grade, rhash) in enumerate(expansion_pool):
        # Convergent view (300+)
        conv = generate_convergent_view(text, grade, rhash)
        if conv:
            expanded.append(conv)
            convergent_count += 1

        # Opposed view (300+)
        opp = generate_opposed_view(text, grade, rhash)
        if opp:
            expanded.append(opp)
            opposed_count += 1

        # Orthogonal view (400+ only)
        orth = generate_orthogonal_view(text, grade, rhash)
        if orth:
            expanded.append(orth)
            orthogonal_count += 1

        if (i + 1) % 200 == 0:
            print(f"  [{i + 1}/{len(expansion_pool)}] expanded...")

    print(f"  Convergent angles: {convergent_count}")
    print(f"  Opposed angles:    {opposed_count}")
    print(f"  Orthogonal angles: {orthogonal_count}")
    print(f"  Total expanded:    {len(expanded)}")
    print()

    # Phase 3: Write output
    print("Phase 3: Writing output...")
    all_output = graded_records + expanded
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_output:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Expansion grade distribution
    exp_grade_dist: Dict[int, int] = {}
    exp_type_dist: Dict[str, int] = {}
    for rec in expanded:
        g = rec["metadata"]["grade"]
        exp_grade_dist[g] = exp_grade_dist.get(g, 0) + 1
        rt = rec["metadata"]["record_type"]
        exp_type_dist[rt] = exp_type_dist.get(rt, 0) + 1

    # Summary
    summary = {
        "input_records": len(records),
        "expanded_records": len(expanded),
        "total_output": len(all_output),
        "expansion_ratio": round(len(all_output) / len(records), 2),
        "grade_distribution": dict(sorted(grade_dist.items())),
        "stage_distribution": dict(sorted(stage_dist.items())),
        "domain_distribution": dict(sorted(domain_dist.items(), key=lambda x: -x[1])),
        "expansion": {
            "convergent": convergent_count,
            "opposed": opposed_count,
            "orthogonal": orthogonal_count,
            "grade_distribution": dict(sorted(exp_grade_dist.items())),
            "type_distribution": exp_type_dist,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print("=" * 70)
    print(f"Input records:    {len(records)}")
    print(f"Expanded records: {len(expanded)}")
    print(f"Total output:     {len(all_output)}")
    print(f"Expansion ratio:  {summary['expansion_ratio']}x")
    print(f"Output: {output_path}")
    print()
    print("Grade distribution (original corpus):")
    for g in sorted(grade_dist.keys()):
        pct = grade_dist[g] / len(records) * 100
        print(f"  {g}-level: {grade_dist[g]:>5} ({pct:.1f}%)")
    print()
    print("Curriculum stages:")
    for stage, count in sorted(stage_dist.items()):
        pct = count / len(records) * 100
        print(f"  {stage:>12}: {count:>5} ({pct:.1f}%)")
    print()
    print("Topic domains:")
    for domain, count in sorted(domain_dist.items(), key=lambda x: -x[1])[:10]:
        pct = count / len(records) * 100
        print(f"  {domain:>20}: {count:>5} ({pct:.1f}%)")
    print()
    print("Expansion types:")
    for rtype, count in sorted(exp_type_dist.items(), key=lambda x: -x[1]):
        print(f"  {rtype:>25}: {count:>5}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
