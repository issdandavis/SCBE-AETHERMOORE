"""
Coding Spine — Atomic Token Router
====================================
Aggregates AtomicTokenState trit vectors across a task prompt to determine
the dominant Sacred Tongue (and therefore the target programming language).

No ML required — deterministic, instant, zero-shot. The atomic tokenizer's
element chemistry handles intent routing entirely.

Tongue → language map:
    Kor'aelin   (KO) → Python
    Avali       (AV) → TypeScript
    Runethic    (RU) → Rust
    Cassisivadan(CA) → C / symbolic
    Umbroth     (UM) → Julia
    Draumric    (DR) → Haskell

Usage:
    from src.coding_spine.router import route_task
    result = route_task("write a thread-safe queue in rust")
    # result.tongue = "RU", result.language = "Rust", result.confidence = 0.71
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# Resolve python/scbe package
_repo_root = Path(__file__).resolve().parents[2]
_python_path = str(_repo_root / "python")
if _python_path not in sys.path:
    sys.path.insert(0, _python_path)

from scbe.atomic_tokenization import (
    TONGUES,
    AtomicTokenState,
    map_token_to_atomic_state,
)

PHI = (1 + 5**0.5) / 2

# Phi-scaled weights per tongue (same as LWS)
TONGUE_PHI_WEIGHTS: Dict[str, float] = {
    "KO": 1.000,  # Kor'aelin  — Python
    "AV": 1.618,  # Avali      — TypeScript
    "RU": 2.618,  # Runethic   — Rust
    "CA": 4.236,  # Cassisivadan — C / symbolic
    "UM": 6.854,  # Umbroth      — Julia
    "DR": 11.090,  # Draumric     — Haskell
}

TONGUE_LANGUAGE: Dict[str, str] = {
    "KO": "Python",
    "AV": "TypeScript",
    "RU": "Rust",
    "CA": "C",
    "UM": "Julia",
    "DR": "Haskell",
}

TONGUE_FULL_NAME: Dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

# Strong keyword overrides — language-specific terms bypass trit aggregation
_LANGUAGE_KEYWORDS: Dict[str, list[str]] = {
    "RU": ["rust", "cargo", "borrow", "ownership", "lifetimes", "unsafe", "tokio", "async fn"],
    "AV": ["typescript", "javascript", "node", "react", "deno", "npm", "tsx", "jsx"],
    "KO": ["python", "django", "flask", "fastapi", "numpy", "pandas", "asyncio", "pytest"],
    "CA": ["c++", "c language", "mathematica", "symbolic", "cmake", "gcc", "clang"],
    "UM": ["julia", "pkg", "dataframes", "differentialequations", "flux"],
    "DR": ["haskell", "ghc", "cabal", "stack", "monadic", "functors", "applicative", "parser combinator"],
}


@dataclass
class RouteResult:
    tongue: str  # e.g. "RU"
    language: str  # e.g. "Rust"
    full_name: str  # e.g. "Runethic"
    phi_weight: float  # e.g. 2.618
    confidence: float  # 0.0 – 1.0
    trit_scores: Dict[str, float]  # raw aggregated scores per tongue
    override_keyword: Optional[str]  # set if a keyword forced the choice
    token_states: list[AtomicTokenState]  # atomic state for each token


def _tokenize(task: str) -> list[str]:
    """Split task into lowercase tokens, preserving compound words."""
    # Keep hyphenated and apostrophe forms as single tokens where useful
    tokens = re.findall(r"[a-z][a-z'\-]*[a-z]|[a-z]", task.lower())
    return tokens


def _check_keyword_override(task_lower: str) -> Optional[Tuple[str, str]]:
    """Return (tongue, keyword) if a strong language keyword is present."""
    for tongue, keywords in _LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in task_lower:
                return tongue, kw
    return None


def _aggregate_trits(states: list[AtomicTokenState]) -> Dict[str, float]:
    """
    Sum trit vectors across all tokens, weighted by element electronegativity
    and semantic class relevance. Higher electronegativity = stronger signal.

    Returns a dict of tongue → weighted score.
    """
    scores: Dict[str, float] = {t: 0.0 for t in TONGUES}

    for state in states:
        # Electronegativity as signal strength (0.0 inert → 4.0 max)
        strength = max(state.element.electronegativity, 0.1)

        # INERT_WITNESS tokens contribute minimally
        if state.semantic_class == "INERT_WITNESS":
            strength *= 0.1

        # ACTION and ENTITY tokens are the strongest routing signals
        if state.semantic_class in ("ACTION", "ENTITY"):
            strength *= 1.5

        # NEGATION flips the trit (negative intent)
        flip = -1 if state.negative_state else 1

        trit_dict = state.tau.as_dict()
        for tongue in TONGUES:
            trit_val = trit_dict[tongue] * flip
            scores[tongue] += trit_val * strength

    return scores


def _normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """Shift all scores positive then normalize to [0, 1]."""
    min_v = min(scores.values())
    shifted = {t: v - min_v for t, v in scores.items()}
    total = sum(shifted.values()) or 1.0
    return {t: v / total for t, v in shifted.items()}


def route_task(task: str, force_tongue: Optional[str] = None) -> RouteResult:
    """
    Route a natural-language coding task to the most appropriate Sacred Tongue.

    Args:
        task:        Natural language coding task description.
        force_tongue: Override routing and use this tongue (e.g. "RU").

    Returns:
        RouteResult with dominant tongue, language, confidence, and debug info.
    """
    task_lower = task.lower()
    tokens = _tokenize(task)
    states = [map_token_to_atomic_state(tok) for tok in tokens if tok]

    # --- Forced tongue ---
    if force_tongue:
        tongue = force_tongue.upper()
        return RouteResult(
            tongue=tongue,
            language=TONGUE_LANGUAGE.get(tongue, "Python"),
            full_name=TONGUE_FULL_NAME.get(tongue, tongue),
            phi_weight=TONGUE_PHI_WEIGHTS.get(tongue, 1.0),
            confidence=1.0,
            trit_scores={t: 0.0 for t in TONGUES},
            override_keyword=f"--tongue {tongue}",
            token_states=states,
        )

    # --- Keyword override (deterministic, highest priority) ---
    kw_result = _check_keyword_override(task_lower)
    if kw_result:
        tongue, keyword = kw_result
        return RouteResult(
            tongue=tongue,
            language=TONGUE_LANGUAGE[tongue],
            full_name=TONGUE_FULL_NAME[tongue],
            phi_weight=TONGUE_PHI_WEIGHTS[tongue],
            confidence=0.95,
            trit_scores={t: 0.0 for t in TONGUES},
            override_keyword=keyword,
            token_states=states,
        )

    # --- Trit aggregation ---
    raw_scores = _aggregate_trits(states)
    norm_scores = _normalize_scores(raw_scores)

    # Pick dominant tongue
    dominant = max(norm_scores, key=lambda t: norm_scores[t])
    confidence = norm_scores[dominant]

    # If confidence is very low (uniform distribution), default to Kor'aelin/Python
    if confidence < 0.20:
        dominant = "KO"
        confidence = 0.5

    return RouteResult(
        tongue=dominant,
        language=TONGUE_LANGUAGE[dominant],
        full_name=TONGUE_FULL_NAME[dominant],
        phi_weight=TONGUE_PHI_WEIGHTS[dominant],
        confidence=round(confidence, 3),
        trit_scores={t: round(norm_scores[t], 4) for t in TONGUES},
        override_keyword=None,
        token_states=states,
    )


if __name__ == "__main__":
    # Quick smoke test
    tasks = [
        "write a thread-safe concurrent queue",
        "parse JSON and send to an API in typescript",
        "build a binary search tree in python",
        "implement a memory allocator with ownership",
        "document the SCBE pipeline architecture",
    ]
    for t in tasks:
        r = route_task(t)
        kw = f" (keyword: {r.override_keyword!r})" if r.override_keyword else ""
        print(f"{t!r}")
        print(f"  → {r.full_name} ({r.tongue}) / {r.language} | conf={r.confidence:.2f}{kw}")
        print(f"  trits: {r.trit_scores}")
        print()
