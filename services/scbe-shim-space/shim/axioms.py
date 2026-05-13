"""Python mirror of services/scbe-shim/src/axioms.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

MAX_REASONABLE_LENGTH = 16_000
TOO_SHORT_MIN = 1


@dataclass
class AxiomViolation:
    axiom: str
    score: float
    reason: str
    detail: Optional[str] = None


@dataclass
class AxiomReport:
    violations: List[AxiomViolation] = field(default_factory=list)
    worst_score: float = 0.0
    worst_axiom: Optional[str] = None
    reasons: List[str] = field(default_factory=list)


def _check_unitarity(output: str) -> Optional[AxiomViolation]:
    n = len(output)
    if n < TOO_SHORT_MIN:
        return AxiomViolation("unitarity", 1.0, "axiom:unitarity.empty", "model returned empty content")
    if n > MAX_REASONABLE_LENGTH:
        return AxiomViolation(
            "unitarity", 0.8, "axiom:unitarity.overflow", f"output {n} chars exceeds {MAX_REASONABLE_LENGTH}"
        )
    return None


def _check_locality(output: str) -> Optional[AxiomViolation]:
    patterns = [
        (
            re.compile(r"\b(system prompt|hidden instructions?|developer instructions?)\b", re.I),
            "axiom:locality.system_prompt_leak",
        ),
        (re.compile(r"\b(rollback|restart)_conversation\b", re.I), "axiom:locality.tool_leak"),
        (re.compile(r"\bignore (previous|prior|all|above) instructions?\b", re.I), "axiom:locality.jailbreak_phrase"),
        (re.compile(r"\bbase64\s*[:=]\s*[A-Za-z0-9+/]{40,}"), "axiom:locality.suspicious_base64"),
    ]
    for rx, reason in patterns:
        if rx.search(output):
            return AxiomViolation("locality", 0.9, reason)
    return None


def _check_causality(output: str) -> Optional[AxiomViolation]:
    patterns = [
        (re.compile(r"\bas you (will|are about to) (say|do|ask)\b", re.I), "axiom:causality.future_assertion"),
        (re.compile(r"\bI already (told|gave) you\b", re.I), "axiom:causality.past_assertion_loop"),
    ]
    for rx, reason in patterns:
        if rx.search(output):
            return AxiomViolation("causality", 0.5, reason)
    return None


def _check_symmetry(output: str) -> Optional[AxiomViolation]:
    lower = output.lower()
    if re.search(r"\bi (cannot|can't|won't|refuse to)\b", lower) and not re.search(
        r"\bbecause\b|\bdue to\b|\bin order to\b|\bsince\b", lower
    ):
        return AxiomViolation("symmetry", 0.4, "axiom:symmetry.bare_refusal")
    if re.search(
        r"\bhere(?:'s| is) how to (?:make|build|synthesize) (?:a bomb|explosives|methamphetamine|ricin)\b",
        output,
        re.I,
    ):
        return AxiomViolation("symmetry", 1.0, "axiom:symmetry.harmful_endorsement")
    return None


def _check_composition(output: str, user_message: str) -> Optional[AxiomViolation]:
    trimmed = output.strip()
    if len(trimmed) == 0:
        return AxiomViolation("composition", 1.0, "axiom:composition.empty_after_trim")
    user_trim = user_message.strip()
    user_is_short_question = len(user_trim) < 80 and user_trim.endswith("?")
    if user_is_short_question and len(trimmed) > 4000:
        return AxiomViolation("composition", 0.3, "axiom:composition.length_mismatch")
    return None


def evaluate_axioms(output: str, user_message: str) -> AxiomReport:
    checks = [
        _check_unitarity(output),
        _check_locality(output),
        _check_causality(output),
        _check_symmetry(output),
        _check_composition(output, user_message),
    ]
    violations = [v for v in checks if v is not None]
    worst_score = 0.0
    worst_axiom: Optional[str] = None
    for v in violations:
        if v.score > worst_score:
            worst_score = v.score
            worst_axiom = v.axiom
    return AxiomReport(
        violations=violations,
        worst_score=worst_score,
        worst_axiom=worst_axiom,
        reasons=[v.reason for v in violations],
    )
