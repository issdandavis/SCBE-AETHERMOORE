"""
Code Lattice — Coding Patterns as Tongue-Mapped Training Signals
=================================================================

Core insight (Issac Davis, 2026-04-05):
    "You build understanding, not repetition. Repetition is a phase
    over time, but the intentions of the system and the learner
    compound on each other."

This module maps coding patterns onto the six Sacred Tongues so the AI
learns to LIVE in a coding world:

    Tongue  Domain              Good Pattern              "Swear Word" (Anti-Pattern)
    ------  ------------------  -----------------------   ---------------------------
    KO      Intent / Naming     Clear names, doc intent   Cryptic names, no docstrings
    AV      Flow / Transport    Clean async, data pipes   Callback hell, race conditions
    RU      Power / Governance  Proper auth, access ctrl  Hardcoded secrets, no authZ
    CA      Compute / Algorithm Efficient structures      O(n^2) in hot loops, leaks
    UM      Shadow / Edge Cases Explicit error handling   Bare except, silent failures
    DR      Structure / Types   Strong types, modularity  God objects, circular deps

The trit signal from the text SELECTS which patterns to teach:
    - High structure axis (+1) -> KO/DR domain patterns
    - High stability axis (+1) -> AV/UM domain patterns
    - High creativity axis (-1) -> RU/CA domain patterns
    - Near boundary (polymorphic) -> teaches the FORK itself (both sides)

Anti-patterns = "swear words" -- flagged like VRS entry in flight sims.
The QHO level determines the DIFFICULTY of the code pattern:
    n=0: basic naming, simple functions (ground state)
    n=1-2: async patterns, error handling (low excitation)
    n=3-4: architecture, security, concurrency (mid excitation)
    n=5+: distributed systems, formal verification (high excitation)

Understanding compounds: system intent (governance cost, QHO n) and
learner intent (what the text's trit pattern says) MULTIPLY together.
Each bundle teaches WHY through cross-domain mapping, not just WHAT.

Uses only verified existing functions:
    - qho_bundle.QHOLevel, QHOBundle, compute_qho_level
    - trit_curriculum.TritSignal, TRIT_AXES
    - polymorphic_multipath.MultipathRecord
    - crossing_energy.harmonic_cost

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.crypto.trit_curriculum import TritSignal, TRIT_AXES
from src.crypto.qho_bundle import (
    QHOBundle,
    QHOLevel,
    generate_qho_bundle,
    generate_qho_batch,
    flatten_qho_for_sft,
    MAX_N,
)
from src.crypto.harmonic_dark_fill import PHI

# ---------------------------------------------------------------------------
# Constants: Tongue -> Coding Domain
# ---------------------------------------------------------------------------

TONGUE_DOMAIN: Dict[str, str] = {
    "ko": "intent",  # naming, documentation, API design
    "av": "flow",  # async, data pipelines, transport
    "ru": "governance",  # auth, access control, security
    "ca": "compute",  # algorithms, data structures, optimization
    "um": "edge_cases",  # error handling, edge cases, hidden state
    "dr": "structure",  # types, modularity, architecture
}

DOMAIN_DESCRIPTION: Dict[str, str] = {
    "intent": "Naming clarity, documentation, API contract design",
    "flow": "Async patterns, data pipelines, message passing",
    "governance": "Authentication, authorization, security boundaries",
    "compute": "Algorithm efficiency, data structures, resource management",
    "edge_cases": "Error handling, boundary conditions, failure modes",
    "structure": "Type safety, modularity, dependency management",
}


# ---------------------------------------------------------------------------
# Pattern Registry: Good patterns and "swear words" per domain per level
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodePattern:
    """A coding pattern -- good or anti-pattern -- with cross-domain analogy."""

    name: str
    domain: str  # which tongue domain
    is_antipattern: bool  # True = "swear word"
    min_n: int  # minimum QHO level to encounter this
    description: str  # what it is (understanding, not memorization)
    why: str  # WHY it matters (the compounding insight)
    code_good: str  # the correct way
    code_bad: str  # the anti-pattern way (empty if good-only)
    cross_domain: str  # maps to physics/lore analogy


# The registry. Each pattern has a minimum QHO level (curriculum difficulty).
# The AI encounters harder patterns only after mastering easier ones.
# "swear words" are anti-patterns the AI must learn to detect and avoid.

PATTERN_REGISTRY: List[CodePattern] = [
    # ── KO / Intent (n=0+) ──────────────────────────────────────────────
    CodePattern(
        name="clear_naming",
        domain="intent",
        is_antipattern=False,
        min_n=0,
        description="Variable and function names express intent, not implementation",
        why="Names are the first contract. A reader should know WHAT without reading HOW.",
        code_good="remaining_retries = max_attempts - attempt_count",
        code_bad="x = n - i",
        cross_domain="Like KO binding intent: the name IS the spell. Unclear name = miscast.",
    ),
    CodePattern(
        name="cryptic_naming",
        domain="intent",
        is_antipattern=True,
        min_n=0,
        description="Single-letter variables, abbreviations, misleading names",
        why="Forces every reader to reverse-engineer intent. Compounds confusion over time.",
        code_good="def calculate_shipping_cost(weight_kg: float, distance_km: float) -> float:",
        code_bad="def calc(w, d):",
        cross_domain="Swear word in KO: speaking without intent. The binding fails.",
    ),
    CodePattern(
        name="doc_contracts",
        domain="intent",
        is_antipattern=False,
        min_n=2,
        description="Docstrings as contracts: inputs, outputs, invariants, not implementation",
        why="Documentation that describes HOW ages. Documentation that describes WHAT persists.",
        code_good="def transfer(src: Account, dst: Account, amount: Decimal) -> Receipt:\n"
        '    """Move funds between accounts. Raises InsufficientFunds if src < amount."""',
        code_bad="def transfer(src, dst, amount):\n" "    # transfers money",
        cross_domain="Sacred Egg shell inscription: states what WILL hatch, not how the egg was laid.",
    ),
    # ── AV / Flow (n=1+) ────────────────────────────────────────────────
    CodePattern(
        name="structured_async",
        domain="flow",
        is_antipattern=False,
        min_n=1,
        description="Async operations with structured concurrency: clear start, join, cancel",
        why="Unstructured concurrency leaks tasks like unclosed file handles leak memory.",
        code_good="async with TaskGroup() as tg:\n" "    tg.create_task(fetch_a())\n" "    tg.create_task(fetch_b())",
        code_bad="asyncio.create_task(fetch_a())  # fire and forget, who cancels this?",
        cross_domain="AV diplomacy: every message needs a sender, a receiver, and a handshake.",
    ),
    CodePattern(
        name="callback_hell",
        domain="flow",
        is_antipattern=True,
        min_n=1,
        description="Deeply nested callbacks instead of linear async flow",
        why="Each nesting level multiplies cognitive load. 4 deep = 4! mental paths.",
        code_good="result_a = await fetch_a()\nresult_b = await process(result_a)\nreturn await save(result_b)",
        code_bad="fetch_a(lambda a: process(a, lambda b: save(b, lambda c: done(c))))",
        cross_domain="Swear word in AV: messages that require a chain of whispers to deliver.",
    ),
    CodePattern(
        name="race_condition",
        domain="flow",
        is_antipattern=True,
        min_n=3,
        description="Shared mutable state accessed from concurrent paths without synchronization",
        why="Outcome depends on timing, not logic. Passes tests 99% of the time, fails in prod.",
        code_good="async with lock:\n    balance = await get_balance()\n    await set_balance(balance - amount)",
        code_bad="balance = await get_balance()  # another task modifies balance HERE\nawait set_balance(balance - amount)",
        cross_domain="Two tongues casting on the same target without coordination. Spell collision.",
    ),
    # ── RU / Governance (n=2+) ──────────────────────────────────────────
    CodePattern(
        name="auth_boundary",
        domain="governance",
        is_antipattern=False,
        min_n=2,
        description="Authentication and authorization checked at system boundary, not sprinkled through code",
        why="Security scattered through business logic = holes everywhere. One gate, one check.",
        code_good="@require_auth(role='admin')\ndef delete_user(user_id: str) -> None:",
        code_bad="def delete_user(user_id, auth_token):\n    if not check_token(auth_token): ...  # missed in 3 other callers",
        cross_domain="RU governance: one gatekeeper at the boundary, not a hundred scattered guards.",
    ),
    CodePattern(
        name="hardcoded_secrets",
        domain="governance",
        is_antipattern=True,
        min_n=2,
        description="Credentials, API keys, or tokens embedded in source code",
        why="Source code is shared, versioned, and cached. A secret in code is a secret told to everyone.",
        code_good='api_key = os.environ["SERVICE_API_KEY"]',
        code_bad='api_key = "sk-live-abc123xyz"  # TODO: move to env',
        cross_domain="Swear word in RU: writing the vault combination on the vault door.",
    ),
    CodePattern(
        name="privilege_escalation",
        domain="governance",
        is_antipattern=True,
        min_n=4,
        description="Code path that allows lower-privilege operations to escalate to higher privilege",
        why="Every escalation path is an attack surface. The harmonic wall cost should be exponential.",
        code_good="def admin_action(user):\n    assert user.role == Role.ADMIN  # checked at boundary\n    ...",
        code_bad="def admin_action(user):\n    user.role = Role.ADMIN  # 'temporary' escalation\n    ...",
        cross_domain="Breaking the harmonic wall: d* should make this cost R^((phi*d*)^2), not zero.",
    ),
    # ── CA / Compute (n=1+) ─────────────────────────────────────────────
    CodePattern(
        name="right_data_structure",
        domain="compute",
        is_antipattern=False,
        min_n=1,
        description="Choose data structure by access pattern: sets for membership, dicts for lookup, heaps for priority",
        why="Wrong structure = wrong complexity class. A list used as a set is O(n) for every lookup.",
        code_good="seen = set()\nfor item in stream:\n    if item.id not in seen: ...",
        code_bad="seen = []\nfor item in stream:\n    if item.id not in seen: ...",
        cross_domain="CA compute: the polyhedron shape determines what fits. Wrong shape = wrong capacity.",
    ),
    CodePattern(
        name="quadratic_hot_loop",
        domain="compute",
        is_antipattern=True,
        min_n=1,
        description="O(n^2) or worse algorithm in a hot path when O(n log n) or O(n) exists",
        why="Scales into a wall. 1K items = fine. 1M items = hours. The wall is geometric, not linear.",
        code_good="index = {r.key: r for r in records}  # O(n) build, O(1) lookup",
        code_bad="for a in records:\n    for b in records:\n        if a.key == b.key: ...",
        cross_domain="Swear word in CA: climbing phi^(d^2) instead of walking around the base.",
    ),
    CodePattern(
        name="resource_leak",
        domain="compute",
        is_antipattern=True,
        min_n=3,
        description="Opened resources (files, connections, locks) not guaranteed to close",
        why="Leaked resources accumulate. One is nothing. A thousand is a crash. Time compounds the error.",
        code_good="with open(path) as f:\n    data = f.read()",
        code_bad="f = open(path)\ndata = f.read()\n# f.close() never reached if exception above",
        cross_domain="Energy leak in the polyhedral cavity: each unclosed face bleeds heat until collapse.",
    ),
    # ── UM / Edge Cases (n=0+) ──────────────────────────────────────────
    CodePattern(
        name="explicit_error_handling",
        domain="edge_cases",
        is_antipattern=False,
        min_n=0,
        description="Catch specific exceptions, handle or propagate with context",
        why="Every error is information. Silencing it destroys the signal.",
        code_good="try:\n    result = parse(data)\nexcept ValueError as e:\n    log.warning('Parse failed: %s', e)\n    return fallback(data)",
        code_bad="try:\n    result = parse(data)\nexcept:\n    pass",
        cross_domain="UM shadow: the edge case IS the boundary signal. Silencing it = going blind at the edge.",
    ),
    CodePattern(
        name="bare_except",
        domain="edge_cases",
        is_antipattern=True,
        min_n=0,
        description="Catching all exceptions without discrimination, especially silently",
        why="Hides bugs, hides crashes, hides security violations. The worst anti-pattern because it hides ALL anti-patterns.",
        code_good="except (ConnectionError, TimeoutError) as e:\n    retry_with_backoff(e)",
        code_bad="except:\n    pass  # this swallows KeyboardInterrupt, SystemExit, EVERYTHING",
        cross_domain="Worst swear word in UM: painting over the cracks. The void hides what the void consumes.",
    ),
    CodePattern(
        name="silent_data_corruption",
        domain="edge_cases",
        is_antipattern=True,
        min_n=3,
        description="Operations that can produce wrong results without raising errors",
        why="Wrong answer > no answer > silent wrong answer. The last one compounds into cascading lies.",
        code_good="def divide(a: float, b: float) -> float:\n    if b == 0:\n        raise ZeroDivisionError('denominator is zero')\n    return a / b",
        code_bad="def divide(a, b):\n    return a / b if b else 0  # silently returns 0 for division by zero",
        cross_domain="Trit boundary without a fork: the model saw one side, believed it was the only side.",
    ),
    # ── DR / Structure (n=2+) ───────────────────────────────────────────
    CodePattern(
        name="single_responsibility",
        domain="structure",
        is_antipattern=False,
        min_n=2,
        description="Each module/class/function does one thing and owns one reason to change",
        why="When a unit has two responsibilities, changes to one break the other. Coupling compounds.",
        code_good="class UserRepository:\n    def find(self, user_id): ...\n\nclass EmailService:\n    def send(self, to, body): ...",
        code_bad="class UserManager:\n    def find(self, user_id): ...\n    def send_email(self, to, body): ...\n    def generate_report(self): ...",
        cross_domain="DR forge: one anvil, one blade. A forge that also bakes bread makes bad swords and bad bread.",
    ),
    CodePattern(
        name="god_object",
        domain="structure",
        is_antipattern=True,
        min_n=2,
        description="One class that knows about and controls everything",
        why="Every change touches the god object. Every test needs the god object. It becomes the bottleneck of all work.",
        code_good="# Separate concerns into focused modules\nauth = AuthService()\nrouter = Router()\nstore = DataStore()",
        code_bad="class App:\n    def authenticate(self): ...\n    def route(self): ...\n    def query_db(self): ...\n    def send_email(self): ...\n    def render_html(self): ...",
        cross_domain="Swear word in DR: one polyhedron trying to be all 16 shapes at once. Structural impossibility.",
    ),
    CodePattern(
        name="circular_dependency",
        domain="structure",
        is_antipattern=True,
        min_n=4,
        description="Module A imports B, B imports A (directly or through a chain)",
        why="Creates a Mobius strip of initialization: neither can exist without the other already existing.",
        code_good="# A depends on interface, B implements interface\nclass Repository(Protocol):\n    def save(self, item): ...",
        code_bad="# a.py: from b import B\n# b.py: from a import A\n# boom on import",
        cross_domain="Two tongues that each require the other to be spoken first. Logical deadlock. Break with interface.",
    ),
    CodePattern(
        name="mutable_global_state",
        domain="structure",
        is_antipattern=True,
        min_n=1,
        description="Global mutable variables that any code can read and write",
        why="Every function that touches global state has an invisible dependency on every other such function.",
        code_good="def process(config: Config, data: Data) -> Result:\n    return Result(data.transform(config.params))",
        code_bad="CONFIG = {}  # any module mutates this\ndef process(data):\n    return data.transform(CONFIG['params'])  # who set this? when?",
        cross_domain="Swear word in DR: uncontrolled torque on the lattice. Every node vibrates from every mutation.",
    ),
]


# ---------------------------------------------------------------------------
# Quick lookup structures
# ---------------------------------------------------------------------------


def _patterns_by_domain() -> Dict[str, List[CodePattern]]:
    """Group patterns by domain for fast lookup."""
    result: Dict[str, List[CodePattern]] = {}
    for p in PATTERN_REGISTRY:
        result.setdefault(p.domain, []).append(p)
    return result


def _antipatterns() -> List[CodePattern]:
    """All swear words."""
    return [p for p in PATTERN_REGISTRY if p.is_antipattern]


def _good_patterns() -> List[CodePattern]:
    """All good patterns."""
    return [p for p in PATTERN_REGISTRY if not p.is_antipattern]


PATTERNS_BY_DOMAIN = _patterns_by_domain()
ALL_ANTIPATTERNS = _antipatterns()
ALL_GOOD_PATTERNS = _good_patterns()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CodeLesson:
    """A single code pattern matched to a training text by the trit signal."""

    pattern: CodePattern
    relevance: float  # 0..1 how strongly this text triggers this pattern
    compound_intent: float  # system_intent * learner_intent (the compounding score)
    tongue: str  # which tongue activated this
    axis: str  # which trit axis triggered it


@dataclass
class CodeLatticeBundle:
    """QHO bundle augmented with code lessons.

    The AI sees: text + trit + forks + QHO level + code patterns + cross-domain.
    Understanding compounds because each lesson has WHY + analogy, not just WHAT.
    """

    qho_bundle: QHOBundle
    lessons: List[CodeLesson]
    total_compound_intent: float  # sum of all lesson compound intents
    active_domains: List[str]  # which tongue domains are teaching
    swear_word_count: int  # how many anti-patterns detected


# ---------------------------------------------------------------------------
# Pattern selection: trit signal -> which code patterns to teach
# ---------------------------------------------------------------------------


def select_patterns(
    signal: TritSignal,
    qho: QHOLevel,
    gain: float,
) -> List[CodeLesson]:
    """Select code patterns to teach based on trit signal and QHO level.

    The trit axes determine which DOMAINS to draw patterns from:
        structure axis  -> KO (intent) and DR (structure) domains
        stability axis  -> AV (flow) and UM (edge_cases) domains
        creativity axis -> RU (governance) and CA (compute) domains

    The QHO level filters by minimum difficulty.
    The Monty Hall gain and crossing energy weight the relevance.

    Understanding compounds: the same text at different QHO levels
    teaches different patterns. Level 0 sees naming. Level 4 sees
    circular dependencies. The INTENTIONS compound.
    """
    lessons: List[CodeLesson] = []

    # Map axes to tongue pairs and their domains
    axis_domains = [
        ("structure", signal.c_structure, signal.edge_structure, "ko", "dr"),
        ("stability", signal.c_stability, signal.edge_stability, "av", "um"),
        ("creativity", signal.c_creativity, signal.edge_creativity, "ru", "ca"),
    ]

    for axis_name, content_trit, edge_dist, tongue_fwd, tongue_inv in axis_domains:
        # Determine which tongue is dominant on this axis
        if content_trit >= 0:
            active_tongue = tongue_fwd
        else:
            active_tongue = tongue_inv

        domain = TONGUE_DOMAIN[active_tongue]
        domain_patterns = PATTERNS_BY_DOMAIN.get(domain, [])

        # Also include the complement tongue's domain if near boundary
        # (teaches BOTH sides of the fork -- polymorphic understanding)
        complement_tongue = tongue_inv if active_tongue == tongue_fwd else tongue_fwd
        complement_domain = TONGUE_DOMAIN[complement_tongue]
        if edge_dist < 0.01:  # polymorphic boundary
            domain_patterns = domain_patterns + PATTERNS_BY_DOMAIN.get(complement_domain, [])

        for pattern in domain_patterns:
            # Filter by QHO level (curriculum difficulty)
            if pattern.min_n > qho.n:
                continue

            # Relevance: how strongly this text activates this pattern
            # Strong trit value = strong activation for that domain
            trit_strength = abs(content_trit)  # 0 or 1
            edge_proximity = max(0, 1.0 - edge_dist * 100)  # closer to boundary = higher
            relevance = 0.4 * trit_strength + 0.3 * edge_proximity + 0.3 * (qho.n / MAX_N)
            relevance = min(1.0, relevance)

            # Compound intent: system knows (governance cost) * learner shows (gain)
            system_intent = qho.harmonic_wall_cost * (qho.n + 1)
            learner_intent = gain * (1.0 + relevance)
            compound = system_intent * learner_intent

            lessons.append(
                CodeLesson(
                    pattern=pattern,
                    relevance=round(relevance, 4),
                    compound_intent=round(compound, 4),
                    tongue=active_tongue,
                    axis=axis_name,
                )
            )

    # Sort by compound intent (highest first) and deduplicate by pattern name
    seen = set()
    unique_lessons = []
    for lesson in sorted(lessons, key=lambda l: l.compound_intent, reverse=True):
        if lesson.pattern.name not in seen:
            seen.add(lesson.pattern.name)
            unique_lessons.append(lesson)

    return unique_lessons


# ---------------------------------------------------------------------------
# Public API: generate Code Lattice bundle
# ---------------------------------------------------------------------------


def generate_code_lattice_bundle(
    text: str,
    edge_threshold: float = 0.01,
    content_threshold: float = 0.05,
    threshold: float = 0.3,
) -> CodeLatticeBundle:
    """Generate a full code-lattice-augmented training bundle.

    Pipeline:
        text -> QHO bundle (trit + forks + siblings + QHO + visual + acoustic)
             -> select_patterns (trit signal selects code patterns by domain)
             -> CodeLatticeBundle (everything combined)

    The AI trains on these bundles and learns:
        1. The text's trit classification
        2. Which coding domain the text maps to
        3. Concrete code examples (good AND bad)
        4. WHY the pattern matters (understanding)
        5. Cross-domain analogy (physics/lore/code bridge)
    """
    qho_bundle = generate_qho_bundle(text, edge_threshold, content_threshold, threshold)

    lessons = select_patterns(
        signal=qho_bundle.multipath.primary,
        qho=qho_bundle.qho,
        gain=qho_bundle.multipath.monty_hall_gain,
    )

    active_domains = list(dict.fromkeys(l.pattern.domain for l in lessons))
    swear_count = sum(1 for l in lessons if l.pattern.is_antipattern)
    total_compound = sum(l.compound_intent for l in lessons)

    return CodeLatticeBundle(
        qho_bundle=qho_bundle,
        lessons=lessons,
        total_compound_intent=round(total_compound, 4),
        active_domains=active_domains,
        swear_word_count=swear_count,
    )


# ---------------------------------------------------------------------------
# SFT export: flatten for training
# ---------------------------------------------------------------------------


def flatten_code_lattice_for_sft(
    bundles: List[CodeLatticeBundle],
) -> List[Dict]:
    """Flatten code lattice bundles into SFT-ready dicts.

    Each record includes the QHO metadata PLUS code lesson fields.
    Multiple lessons per bundle produce multiple records -- each one
    is a focused teaching moment.
    """
    records = []

    for bundle in bundles:
        # Get the base QHO-flattened records
        qho_records = flatten_qho_for_sft([bundle.qho_bundle])

        if not bundle.lessons:
            # No code patterns triggered -- emit base records as-is
            for rec in qho_records:
                rec["code_lesson"] = None
                rec["code_domain"] = None
                rec["swear_word_count"] = 0
                rec["compound_intent"] = 0.0
                records.append(rec)
            continue

        # For each lesson, create a focused training record
        for lesson in bundle.lessons:
            # Use the first QHO record as base (primary path)
            if qho_records:
                rec = dict(qho_records[0])  # copy
            else:
                rec = {"text": bundle.qho_bundle.text}

            rec["code_lesson"] = {
                "name": lesson.pattern.name,
                "domain": lesson.pattern.domain,
                "is_antipattern": lesson.pattern.is_antipattern,
                "description": lesson.pattern.description,
                "why": lesson.pattern.why,
                "code_good": lesson.pattern.code_good,
                "code_bad": lesson.pattern.code_bad,
                "cross_domain": lesson.pattern.cross_domain,
                "relevance": lesson.relevance,
            }
            rec["code_domain"] = lesson.pattern.domain
            rec["code_tongue"] = lesson.tongue
            rec["code_axis"] = lesson.axis
            rec["compound_intent"] = lesson.compound_intent
            rec["swear_word_count"] = bundle.swear_word_count
            rec["active_domains"] = bundle.active_domains

            records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_code_lattice_report(bundles: List[CodeLatticeBundle]) -> str:
    """Human-readable code lattice report."""
    lines = [
        "=" * 64,
        "  CODE LATTICE TRAINING REPORT",
        "  Understanding Compounds. Repetition is a Phase.",
        "=" * 64,
        "",
        f"  Total bundles:        {len(bundles)}",
    ]

    total_lessons = sum(len(b.lessons) for b in bundles)
    total_swears = sum(b.swear_word_count for b in bundles)
    total_compound = sum(b.total_compound_intent for b in bundles)

    lines.extend(
        [
            f"  Total lessons:        {total_lessons}",
            f"  Swear words detected: {total_swears}",
            f"  Total compound intent:{total_compound:.2f}",
            "",
            "  Domain Activity:",
        ]
    )

    domain_counts: Dict[str, int] = {}
    for b in bundles:
        for d in b.active_domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1

    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        tongue = [t for t, d in TONGUE_DOMAIN.items() if d == domain][0]
        bar = "#" * count
        lines.append(f"    {tongue.upper():>2} {domain:<14} {count:3d} {bar}")

    lines.extend(["", "  Sample Lessons:", "  " + "-" * 60])

    for bundle in bundles[:3]:
        text = bundle.qho_bundle.text
        text_short = text[:50] + "..." if len(text) > 50 else text
        lines.append(f'    text: "{text_short}"')
        lines.append(
            f"      QHO n={bundle.qho_bundle.qho.n}  "
            f"difficulty={bundle.qho_bundle.curriculum_difficulty:.3f}  "
            f"compound={bundle.total_compound_intent:.2f}"
        )

        for lesson in bundle.lessons[:3]:
            marker = "XX" if lesson.pattern.is_antipattern else "OK"
            lines.append(
                f"      [{marker}] {lesson.pattern.name} "
                f"({lesson.tongue}/{lesson.axis}) "
                f"relevance={lesson.relevance:.2f}"
            )
            lines.append(f"           {lesson.pattern.description[:70]}")
            lines.append(f"           -> {lesson.pattern.cross_domain[:70]}")

        if len(bundle.lessons) > 3:
            lines.append(f"      ... and {len(bundle.lessons) - 3} more lessons")
        lines.append("")

    lines.append("=" * 64)
    return "\n".join(lines)
