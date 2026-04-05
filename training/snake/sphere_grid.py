"""FFX Sphere Grid — Programming language-to-tongue mapping.

Maps programming languages onto the 6-tongue sphere like Final Fantasy X's
Sphere Grid. Each language has a HOME tongue and adjacent tongue activations,
giving it a coordinate in Sacred Tongue space.

The grid also encodes interop bridges — which languages can directly call
which via FFI, WASM, subprocess, or gRPC.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS

# ---------------------------------------------------------------------------
# Language entries
# ---------------------------------------------------------------------------


@dataclass
class LanguageNode:
    """A programming language positioned on the Sphere Grid."""

    name: str
    home_tongue: str  # Primary tongue affinity
    affinity: dict[str, float] = field(default_factory=dict)  # All tongue scores
    tier: str = "foundation"  # foundation | esoteric | international
    interop_bridges: list[str] = field(default_factory=list)  # Direct FFI targets
    description: str = ""

    @property
    def coordinate(self) -> list[float]:
        """6D coordinate in tongue space, phi-weighted."""
        return [
            self.affinity.get(t, 0.0) * TONGUE_WEIGHTS[t]
            for t in TONGUES
        ]

    @property
    def norm(self) -> float:
        """L2 norm of the phi-weighted coordinate."""
        c = self.coordinate
        return math.sqrt(sum(x * x for x in c))


# ---------------------------------------------------------------------------
# The Grid — all languages with tongue affinities
# ---------------------------------------------------------------------------

def _make_affinity(home: str, adjacent: list[str], home_weight: float = 0.8) -> dict[str, float]:
    """Build affinity dict: home tongue gets home_weight, adjacents split the rest."""
    aff = {t: 0.0 for t in TONGUES}
    aff[home] = home_weight
    remaining = 1.0 - home_weight
    if adjacent:
        per_adj = remaining / len(adjacent)
        for t in adjacent:
            aff[t] = per_adj
    return aff


# Foundation trio (Python + TypeScript + Rust)
FOUNDATION_LANGUAGES = [
    LanguageNode(
        name="Python",
        home_tongue="AV",
        affinity=_make_affinity("AV", ["CA", "KO"]),
        tier="foundation",
        interop_bridges=["Rust:PyO3", "TypeScript:subprocess", "C:ctypes", "Go:cgo"],
        description="Wisdom/Knowledge — orchestration, data science, ML",
    ),
    LanguageNode(
        name="TypeScript",
        home_tongue="DR",
        affinity=_make_affinity("DR", ["CA", "AV"]),
        tier="foundation",
        interop_bridges=["Rust:wasm-bindgen", "Python:child_process", "C:N-API"],
        description="Architecture/Structure — APIs, type systems, frontend",
    ),
    LanguageNode(
        name="Rust",
        home_tongue="UM",
        affinity=_make_affinity("UM", ["CA", "DR"]),
        tier="foundation",
        interop_bridges=["Python:PyO3", "TypeScript:napi-rs", "C:extern_C", "Go:cgo"],
        description="Security/Defense — memory safety, zero-cost, crypto",
    ),
]

# Standard languages (positioned on the grid)
STANDARD_LANGUAGES = [
    LanguageNode("C", "CA", _make_affinity("CA", ["UM"]), "standard",
                 ["Python:CPython", "Rust:extern_C", "Go:cgo"],
                 "Raw compute, systems programming"),
    LanguageNode("C++", "CA", _make_affinity("CA", ["UM", "DR"]), "standard",
                 ["Python:pybind11", "Rust:cxx"],
                 "Compute with architecture — OOP, templates"),
    LanguageNode("Go", "DR", _make_affinity("DR", ["CA", "KO"]), "standard",
                 ["Rust:cgo", "Python:cgo", "C:cgo"],
                 "Architecture/Concurrency — goroutines, channels"),
    LanguageNode("Shell", "KO", _make_affinity("KO", ["DR"]), "standard",
                 ["Python:subprocess", "Any:pipe"],
                 "Pure intent/command — glue language"),
    LanguageNode("SQL", "AV", _make_affinity("AV", ["DR", "RU"]), "standard",
                 ["Python:sqlalchemy", "TypeScript:prisma"],
                 "Declarative knowledge query"),
    LanguageNode("Haskell", "AV", _make_affinity("AV", ["CA", "RU"]), "standard",
                 [], "Pure functional wisdom — monads, types"),
    LanguageNode("Solidity", "RU", _make_affinity("RU", ["UM", "CA"]), "standard",
                 [], "Governance on-chain — smart contracts"),
    LanguageNode("CUDA", "CA", _make_affinity("CA", ["UM"]), "standard",
                 ["Python:cupy", "Rust:cuda-sys"],
                 "GPU compute — parallel kernels"),
    LanguageNode("Assembly", "UM", _make_affinity("UM", ["CA"]), "standard",
                 ["C:inline_asm", "Rust:asm!"],
                 "Hardware-level security and control"),
    LanguageNode("Zig", "UM", _make_affinity("UM", ["CA", "DR"]), "standard",
                 ["C:extern_C"], "Safety without hidden control flow"),
    LanguageNode("Terraform", "DR", _make_affinity("DR", ["RU", "KO"]), "standard",
                 [], "Infrastructure as code — declarative architecture"),
    LanguageNode("Lua", "KO", _make_affinity("KO", ["AV", "CA"]), "standard",
                 ["C:lua_api"], "Lightweight intent scripting — game engines"),
    LanguageNode("COBOL", "RU", _make_affinity("RU", ["AV"]), "standard",
                 [], "Legacy governance — financial systems"),
    LanguageNode("Fortran", "CA", _make_affinity("CA", ["AV"]), "standard",
                 ["Python:f2py", "C:extern"],
                 "Scientific compute — numerical methods"),
    LanguageNode("Prolog", "AV", _make_affinity("AV", ["RU", "KO"]), "standard",
                 [], "Logic/Knowledge representation"),
    LanguageNode("Verilog", "UM", _make_affinity("UM", ["DR", "CA"]), "standard",
                 [], "Hardware description — security at silicon level"),
    LanguageNode("GraphQL", "AV", _make_affinity("AV", ["DR"]), "standard",
                 ["TypeScript:apollo", "Python:strawberry"],
                 "Declarative data query — schema-driven"),
    LanguageNode("YAML", "RU", _make_affinity("RU", ["DR", "KO"]), "standard",
                 [], "Configuration governance — k8s, CI/CD"),
    LanguageNode("Nix", "RU", _make_affinity("RU", ["DR", "UM"]), "standard",
                 [], "Reproducible builds — immutable governance"),
    LanguageNode("Kotlin", "DR", _make_affinity("DR", ["AV", "CA"]), "standard",
                 ["Java:JVM"], "Modern structured architecture — JVM"),
]

# Esoteric languages (force novel pattern recognition)
ESOTERIC_LANGUAGES = [
    LanguageNode("Brainfuck", "KO", _make_affinity("KO", []),
                 "esoteric", [], "Pure intent — 8 commands, nothing else"),
    LanguageNode("Whitespace", "KO", {t: 0.0 for t in TONGUES},  # ALL null
                 "esoteric", [], "Pure null-pattern — absence IS the program"),
    LanguageNode("Befunge", "DR", _make_affinity("DR", ["KO", "CA"]),
                 "esoteric", [], "2D pathfinding — quasicrystal analogy"),
    LanguageNode("Malbolge", "UM", _make_affinity("UM", ["RU"]),
                 "esoteric", [], "Adversarial by design — security training"),
    LanguageNode("APL", "CA", _make_affinity("CA", []),
                 "esoteric", [], "Pure computation — symbols distilled to math"),
    LanguageNode("J", "CA", _make_affinity("CA", ["AV"]),
                 "esoteric", [], "APL descendant — tacit programming"),
]

# International languages (holistic understanding)
INTERNATIONAL_LANGUAGES = [
    LanguageNode("Wenyan", "AV", _make_affinity("AV", ["RU"]),
                 "international", [],
                 "Classical Chinese — ancient wisdom encoded as code"),
    LanguageNode("EPL", "CA", _make_affinity("CA", ["AV"]),
                 "international", [],
                 "Easy Programming Language (Chinese) — modern compute"),
    LanguageNode("Rapira", "RU", _make_affinity("RU", ["AV", "CA"]),
                 "international", [],
                 "Russian — governance-oriented education language"),
    LanguageNode("Robik", "AV", _make_affinity("AV", ["KO"]),
                 "international", [],
                 "Russian educational — knowledge building"),
    LanguageNode("Dolittle", "KO", _make_affinity("KO", ["AV"]),
                 "international", [],
                 "Japanese — intent-driven, natural language syntax"),
    LanguageNode("Fjolnir", "DR", _make_affinity("DR", ["RU"]),
                 "international", [],
                 "Icelandic — Nordic structural programming"),
]

# Combined registry
ALL_LANGUAGES = (
    FOUNDATION_LANGUAGES
    + STANDARD_LANGUAGES
    + ESOTERIC_LANGUAGES
    + INTERNATIONAL_LANGUAGES
)

LANGUAGE_BY_NAME: dict[str, LanguageNode] = {lang.name: lang for lang in ALL_LANGUAGES}


# ---------------------------------------------------------------------------
# Grid queries
# ---------------------------------------------------------------------------


def languages_by_tongue(tongue: str) -> list[LanguageNode]:
    """Get all languages whose home tongue matches."""
    return [l for l in ALL_LANGUAGES if l.home_tongue == tongue]


def languages_by_tier(tier: str) -> list[LanguageNode]:
    """Get all languages in a tier (foundation/standard/esoteric/international)."""
    return [l for l in ALL_LANGUAGES if l.tier == tier]


def tongue_distance(lang_a: str, lang_b: str) -> float:
    """Compute phi-weighted Euclidean distance between two languages on the grid."""
    a = LANGUAGE_BY_NAME.get(lang_a)
    b = LANGUAGE_BY_NAME.get(lang_b)
    if not a or not b:
        return float("inf")
    ca, cb = a.coordinate, b.coordinate
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(ca, cb)))


def interop_path(lang_a: str, lang_b: str) -> str | None:
    """Find the FFI/interop bridge between two languages, if one exists."""
    a = LANGUAGE_BY_NAME.get(lang_a)
    if not a:
        return None
    for bridge in a.interop_bridges:
        target, method = bridge.split(":", 1)
        if target == lang_b:
            return method
    return None


def closest_language(tongue_profile: dict[str, float], tier: str | None = None) -> LanguageNode:
    """Find the language closest to a given tongue profile on the sphere grid."""
    candidates = languages_by_tier(tier) if tier else ALL_LANGUAGES
    target = [tongue_profile.get(t, 0.0) * TONGUE_WEIGHTS[t] for t in TONGUES]

    best = candidates[0]
    best_dist = float("inf")
    for lang in candidates:
        coord = lang.coordinate
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, coord)))
        if dist < best_dist:
            best_dist = dist
            best = lang
    return best


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Sphere Grid: {len(ALL_LANGUAGES)} languages mapped")
    print()

    for tongue in TONGUES:
        langs = languages_by_tongue(tongue)
        names = ", ".join(l.name for l in langs)
        print(f"  {tongue}: {names}")

    print()
    print("Foundation trio distances:")
    for a in FOUNDATION_LANGUAGES:
        for b in FOUNDATION_LANGUAGES:
            if a.name < b.name:
                d = tongue_distance(a.name, b.name)
                bridge = interop_path(a.name, b.name) or "none"
                print(f"  {a.name} ↔ {b.name}: dist={d:.4f}, bridge={bridge}")

    print()
    print("Tier counts:")
    for tier in ["foundation", "standard", "esoteric", "international"]:
        print(f"  {tier}: {len(languages_by_tier(tier))}")
