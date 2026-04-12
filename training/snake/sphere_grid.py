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

from .config import PHI, TONGUES, TONGUE_WEIGHTS, TONGUE_HUMAN_ROOTS, TONGUE_CONLANG_NAMES

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
# Human Language <-> Sacred Tongue mapping (outer realm connectivity)
# ---------------------------------------------------------------------------


@dataclass
class HumanLanguageNode:
    """A natural human language positioned on the Sphere Grid as a conlang root."""

    name: str               # e.g. "Korean"
    iso_code: str           # e.g. "ko"
    root_tongue: str        # Primary Sacred Tongue this language roots
    conlang_name: str       # The conlang it birthed (e.g. "Kor'aelin")
    aesthetic_layer: str    # Fictional overlay (e.g. "Tolkien-elvish")
    affinity: dict[str, float] = field(default_factory=dict)
    script: str = ""        # Writing system
    direction: str = "ltr"  # Text direction

    @property
    def coordinate(self) -> list[float]:
        """6D coordinate in tongue space, phi-weighted."""
        return [
            self.affinity.get(t, 0.0) * TONGUE_WEIGHTS[t]
            for t in TONGUES
        ]

    @property
    def norm(self) -> float:
        c = self.coordinate
        return math.sqrt(sum(x * x for x in c))


# Root human languages — each Sacred Tongue conlang was derived from one
HUMAN_LANGUAGE_ROOTS = [
    HumanLanguageNode(
        name="Korean", iso_code="ko", root_tongue="KO",
        conlang_name="Kor'aelin", aesthetic_layer="Tolkien-elvish",
        affinity={"KO": 0.9, "AV": 0.5, "RU": 0.4, "CA": 0.5, "UM": 0.7, "DR": 0.8},
        script="Hangul", direction="ltr",
    ),
    HumanLanguageNode(
        name="Sanskrit", iso_code="sa", root_tongue="AV",
        conlang_name="Avali", aesthetic_layer="Wisdom tradition",
        affinity={"KO": 0.3, "AV": 1.0, "RU": 0.7, "CA": 0.8, "UM": 0.5, "DR": 0.9},
        script="Devanagari", direction="ltr",
    ),
    HumanLanguageNode(
        name="Arabic", iso_code="ar", root_tongue="AV",
        conlang_name="Avali", aesthetic_layer="Wisdom tradition (secondary root)",
        affinity={"KO": 0.5, "AV": 0.9, "RU": 0.7, "CA": 0.6, "UM": 0.8, "DR": 0.5},
        script="Arabic", direction="rtl",
    ),
    HumanLanguageNode(
        name="Russian", iso_code="ru", root_tongue="RU",
        conlang_name="Runethic", aesthetic_layer="Norse rune",
        affinity={"KO": 0.5, "AV": 0.4, "RU": 0.8, "CA": 0.5, "UM": 0.6, "DR": 0.7},
        script="Cyrillic", direction="ltr",
    ),
    HumanLanguageNode(
        name="Chinese", iso_code="zh", root_tongue="CA",
        conlang_name="Cassisivadan", aesthetic_layer="Sanskrit compound structure",
        affinity={"KO": 0.5, "AV": 0.8, "RU": 0.4, "CA": 0.9, "UM": 0.6, "DR": 0.7},
        script="Han", direction="ltr",
    ),
    HumanLanguageNode(
        name="Japanese", iso_code="ja", root_tongue="UM",
        conlang_name="Umbroth", aesthetic_layer="Shadow/darkness mythology",
        affinity={"KO": 0.4, "AV": 0.6, "RU": 0.5, "CA": 0.7, "UM": 0.9, "DR": 0.8},
        script="Kanji/Kana", direction="ltr",
    ),
    HumanLanguageNode(
        name="German", iso_code="de", root_tongue="DR",
        conlang_name="Draumric", aesthetic_layer="Norse/Germanic",
        affinity={"KO": 0.5, "AV": 0.3, "RU": 0.8, "CA": 0.6, "UM": 0.3, "DR": 0.9},
        script="Latin", direction="ltr",
    ),
]

HUMAN_LANG_BY_NAME: dict[str, HumanLanguageNode] = {
    lang.name: lang for lang in HUMAN_LANGUAGE_ROOTS
}
HUMAN_LANG_BY_TONGUE: dict[str, list[HumanLanguageNode]] = {}
for _hl in HUMAN_LANGUAGE_ROOTS:
    HUMAN_LANG_BY_TONGUE.setdefault(_hl.root_tongue, []).append(_hl)


# ---------------------------------------------------------------------------
# The Full Bridge: Human Language <-> Conlang <-> Programming Language
# ---------------------------------------------------------------------------

OUTER_REALM_BRIDGE: dict[str, dict[str, Any]] = {}
for _tongue in TONGUES:
    _roots = HUMAN_LANG_BY_TONGUE.get(_tongue, [])
    _prog_langs = [l for l in ALL_LANGUAGES if l.home_tongue == _tongue]
    OUTER_REALM_BRIDGE[_tongue] = {
        "conlang": TONGUE_CONLANG_NAMES.get(_tongue, _tongue),
        "human_roots": [{"name": r.name, "iso": r.iso_code, "script": r.script} for r in _roots],
        "programming_langs": [l.name for l in _prog_langs],
        "sacred_particles": {
            "KO": ["'vel", "'keth", "'zar", "'nav", "'sil", "'thul", "'ael"],
        }.get(_tongue, []),
    }


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


def human_language_for_tongue(tongue: str) -> list[HumanLanguageNode]:
    """Get the root human language(s) for a Sacred Tongue."""
    return HUMAN_LANG_BY_TONGUE.get(tongue, [])


def full_bridge(tongue: str) -> dict[str, Any]:
    """Get the full human <-> conlang <-> programming language bridge for a tongue."""
    return OUTER_REALM_BRIDGE.get(tongue, {})


def cross_realm_distance(human_lang: str, prog_lang: str) -> float:
    """Distance between a human language and a programming language on the grid."""
    hl = HUMAN_LANG_BY_NAME.get(human_lang)
    pl = LANGUAGE_BY_NAME.get(prog_lang)
    if not hl or not pl:
        return float("inf")
    ch, cp = hl.coordinate, pl.coordinate
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(ch, cp)))


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
    print(f"Sphere Grid: {len(ALL_LANGUAGES)} programming languages + {len(HUMAN_LANGUAGE_ROOTS)} human languages mapped")
    print()

    print("=== Outer Realm Bridge (Human <-> Conlang <-> Programming) ===")
    for tongue in TONGUES:
        bridge = full_bridge(tongue)
        roots = ", ".join(r["name"] for r in bridge.get("human_roots", []))
        progs = ", ".join(bridge.get("programming_langs", []))
        print(f"  {tongue} ({bridge.get('conlang', '?')}):")
        print(f"    Human roots: {roots or 'none'}")
        print(f"    Prog langs:  {progs or 'none'}")

    print()
    print("=== Programming Languages by Tongue ===")
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
                print(f"  {a.name} <-> {b.name}: dist={d:.4f}, bridge={bridge}")

    print()
    print("Cross-realm distances (Korean <-> programming languages):")
    for lang in FOUNDATION_LANGUAGES:
        d = cross_realm_distance("Korean", lang.name)
        print(f"  Korean <-> {lang.name}: {d:.4f}")

    print()
    print("Tier counts:")
    for tier in ["foundation", "standard", "esoteric", "international"]:
        print(f"  {tier}: {len(languages_by_tier(tier))}")
