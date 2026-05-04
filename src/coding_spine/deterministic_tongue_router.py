"""Deterministic Sacred Tongue routing for agent harness control signals.

LLMs can help write code, but they should not be trusted as the control-plane
authority for choosing a Sacred Tongue lane. This module wraps the existing
atomic-token router with prompt cleanup and intent overrides so harnesses can
route first, then ask the model to generate within the chosen lane.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from src.coding_spine.router import RouteResult, route_task

TONGUE_CANONICAL_LANG: dict[str, str] = {
    "KO": "Python",
    "AV": "TypeScript",
    "RU": "Rust",
    "CA": "C",
    "UM": "Julia",
    "DR": "Markdown",
}

TONGUE_ROUTE_HINTS: dict[str, tuple[str, ...]] = {
    "KO": (
        "python",
        "fastapi",
        "django",
        "flask",
        "pandas",
        "pytest",
        "script",
        "helper",
    ),
    "AV": (
        "typescript",
        "javascript",
        "react",
        "browser",
        "dom",
        "node",
        "npm",
        "tsx",
        "jsx",
    ),
    "RU": (
        "rust",
        "cargo",
        "borrow",
        "ownership",
        "memory-safe",
        "zero-cost",
        "ring buffer",
        "tokio",
    ),
    "CA": (
        "c ",
        " c.",
        "c language",
        "c function",
        "gcc",
        "clang",
        "cmake",
        "cuda",
        "fortran",
        "symbolic",
        "mathematica",
        "raw computation",
    ),
    "UM": (
        "julia",
        "differentialequations",
        "dataframes",
        "flux",
        "spectral",
        "anomaly",
        "security",
        "defense",
    ),
    "DR": (
        "haskell",
        "ghc",
        "cabal",
        "stack",
        "monad",
        "monadic",
        "functor",
        "applicative",
        "parser combinator",
        "readme",
        "documentation",
        "markdown",
        "architecture",
        "specification",
    ),
}

_TASK_CLAUSE_RX = re.compile(r"\btask\s*:\s*(.*?)(?:\bchoose\b|\breply\b|$)", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class DeterministicTongueRoute:
    tongue: str
    language: str
    confidence: float
    source: str
    reason: str
    routed_text: str
    base_route: dict[str, Any] | None = None

    def as_json(self) -> dict[str, Any]:
        return asdict(self)

    def compact_json(self) -> str:
        return json.dumps({"tongue": self.tongue, "lang": self.language}, sort_keys=True)


def extract_routing_text(prompt: str) -> str:
    """Extract the task body and avoid contaminating routing with map instructions."""

    text = " ".join((prompt or "").split())
    match = _TASK_CLAUSE_RX.search(text)
    if match:
        candidate = match.group(1).strip(" .:-")
        if candidate:
            return candidate
    return text


def _first_hint(text: str) -> tuple[str, str] | None:
    haystack = f" {text.lower()} "
    hits: list[tuple[int, str, str]] = []
    for tongue, hints in TONGUE_ROUTE_HINTS.items():
        for hint in hints:
            idx = haystack.find(hint)
            if idx >= 0:
                hits.append((idx, tongue, hint.strip()))
    if not hits:
        return None
    _, tongue, hint = min(hits, key=lambda row: row[0])
    return tongue, hint


def route_prompt(prompt: str, *, force_tongue: str | None = None) -> DeterministicTongueRoute:
    routed_text = extract_routing_text(prompt)

    if force_tongue:
        tongue = force_tongue.upper()
        return DeterministicTongueRoute(
            tongue=tongue,
            language=TONGUE_CANONICAL_LANG.get(tongue, "Python"),
            confidence=1.0,
            source="force",
            reason=f"forced:{tongue}",
            routed_text=routed_text,
            base_route=None,
        )

    hint = _first_hint(routed_text)
    if hint is not None:
        tongue, keyword = hint
        return DeterministicTongueRoute(
            tongue=tongue,
            language=TONGUE_CANONICAL_LANG[tongue],
            confidence=0.98,
            source="keyword",
            reason=keyword,
            routed_text=routed_text,
            base_route=None,
        )

    base: RouteResult = route_task(routed_text)
    tongue = base.tongue
    return DeterministicTongueRoute(
        tongue=tongue,
        language=TONGUE_CANONICAL_LANG.get(tongue, base.language),
        confidence=base.confidence,
        source="atomic-token-router",
        reason=base.override_keyword or "trit-aggregate",
        routed_text=routed_text,
        base_route={
            "tongue": base.tongue,
            "language": base.language,
            "full_name": base.full_name,
            "phi_weight": base.phi_weight,
            "confidence": base.confidence,
            "trit_scores": base.trit_scores,
            "override_keyword": base.override_keyword,
        },
    )
