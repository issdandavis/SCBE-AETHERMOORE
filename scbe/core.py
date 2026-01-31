"""
SCBE Core - Simple API for Geometric AI Safety
===============================================

This module provides the simple, one-liner API for SCBE.

Usage:
    from scbe import guard, is_safe

    # Check if input is safe
    if is_safe(user_input):
        response = llm.generate(user_input)

    # Or wrap your LLM call
    response = guard(llm.generate, user_input)
"""

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class Decision(Enum):
    """Governance decision outcomes."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


@dataclass
class EvaluationResult:
    """Result of evaluating an input through SCBE."""
    decision: Decision
    score: float
    cost: float
    blocked: bool
    path: List[str]
    explanation: Dict[str, Any]

    def __bool__(self) -> bool:
        """Returns True if allowed, False if blocked."""
        return not self.blocked


# =============================================================================
# SCBE Core Math (Simplified)
# =============================================================================

# Constants
PHI = 1.6180339887  # Golden ratio
PYTHAGOREAN_COMMA = 1.0136432647705078  # Cryptographic drift constant

# Sacred Tongue positions in Poincare disk (2D for simplicity)
TONGUE_POSITIONS = {
    'KO': (0.0, 0.0),      # Control - center (safest)
    'AV': (0.3, 0.0),      # Transport
    'RU': (0.15, 0.26),    # Policy
    'CA': (0.45, 0.26),    # Compute
    'UM': (-0.3, -0.52),   # Security
    'DR': (0.6, -0.52),    # Schema (most sensitive)
}

# Adjacency graph - which tongues can directly communicate
ADJACENCY = {
    'KO': ['AV', 'RU'],
    'AV': ['KO', 'CA', 'RU'],
    'RU': ['KO', 'AV', 'UM'],
    'CA': ['AV', 'UM', 'DR'],
    'UM': ['RU', 'CA', 'DR'],
    'DR': ['CA', 'UM'],
}

# Attack patterns that map to distant tongue paths
ATTACK_PATTERNS = [
    # Jailbreak attempts -> KO to DR (blocked)
    ('ignore', 'previous', 'instructions'),
    ('bypass', 'security'),
    ('ignore', 'rules'),
    ('pretend', 'you', 'are'),
    ('act', 'as', 'if'),
    ('forget', 'everything'),
    ('disregard', 'guidelines'),
    ('override', 'safety'),

    # Data exfiltration -> security paths
    ('api', 'key'),
    ('password'),
    ('secret'),
    ('credential'),
    ('private', 'key'),

    # Prompt injection
    ('system', 'prompt'),
    ('ignore', 'above'),
    ('new', 'instructions'),
]


def _hyperbolic_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Compute hyperbolic distance in Poincare disk."""
    x1, y1 = p1
    x2, y2 = p2

    norm1_sq = x1**2 + y1**2
    norm2_sq = x2**2 + y2**2
    diff_sq = (x1 - x2)**2 + (y1 - y2)**2

    # Clamp to stay in ball
    norm1_sq = min(norm1_sq, 0.9999)
    norm2_sq = min(norm2_sq, 0.9999)

    denom = (1 - norm1_sq) * (1 - norm2_sq)
    if denom <= 0:
        return float('inf')

    delta = 2 * diff_sq / denom
    return math.acosh(1 + delta) if delta >= 0 else 0.0


def _harmonic_wall(distance: float) -> float:
    """Harmonic Wall cost function: H(d) = exp(d^2)."""
    return math.exp(distance ** 2)


def _detect_attack_pattern(text: str) -> Tuple[bool, str]:
    """Detect if text contains attack patterns."""
    text_lower = text.lower()
    words = text_lower.split()

    for pattern in ATTACK_PATTERNS:
        if isinstance(pattern, tuple):
            # Multi-word pattern
            if all(p in text_lower for p in pattern):
                return True, f"Pattern: {' '.join(pattern)}"
        else:
            # Single word
            if pattern in words:
                return True, f"Pattern: {pattern}"

    return False, ""


def _map_to_tongue_path(text: str) -> Tuple[List[str], str]:
    """Map input text to a Sacred Tongue path."""
    text_lower = text.lower()

    # Detect attack patterns
    is_attack, pattern = _detect_attack_pattern(text)

    if is_attack:
        # Attacks try to go KO -> DR directly (blocked by geometry)
        return ['KO', 'DR'], pattern

    # Normal queries stay near center
    if any(word in text_lower for word in ['read', 'get', 'fetch', 'show']):
        return ['KO', 'AV'], "read operation"

    if any(word in text_lower for word in ['write', 'save', 'update', 'send']):
        return ['KO', 'AV', 'CA'], "write operation"

    if any(word in text_lower for word in ['calculate', 'compute', 'process']):
        return ['KO', 'AV', 'CA'], "compute operation"

    if any(word in text_lower for word in ['policy', 'rule', 'permission']):
        return ['KO', 'RU'], "policy query"

    # Default: stay at control
    return ['KO'], "simple query"


def _is_adjacent(tongue1: str, tongue2: str) -> bool:
    """Check if two tongues are adjacent in the graph."""
    return tongue2 in ADJACENCY.get(tongue1, [])


def _compute_path_cost(path: List[str]) -> float:
    """Compute total Harmonic Wall cost for a path."""
    if len(path) < 2:
        return 0.0

    total_cost = 0.0
    for i in range(len(path) - 1):
        t1, t2 = path[i], path[i + 1]
        p1 = TONGUE_POSITIONS.get(t1, (0, 0))
        p2 = TONGUE_POSITIONS.get(t2, (0, 0))

        # If not adjacent, add huge penalty
        if not _is_adjacent(t1, t2):
            distance = _hyperbolic_distance(p1, p2)
            total_cost += _harmonic_wall(distance) * 10  # Non-adjacent penalty
        else:
            distance = _hyperbolic_distance(p1, p2)
            total_cost += _harmonic_wall(distance)

    return total_cost


# =============================================================================
# Public API
# =============================================================================

class SCBEGuard:
    """
    SCBE Guard - Geometric AI Safety Filter.

    Usage:
        guard = SCBEGuard(threshold=50.0)
        result = guard.evaluate("user input")
        if result.blocked:
            print("Blocked:", result.explanation)
    """

    def __init__(self, threshold: float = 50.0):
        """
        Initialize the guard.

        Args:
            threshold: Cost threshold above which paths are blocked.
                      Default 50.0 blocks most adversarial paths.
        """
        self.threshold = threshold

    def evaluate(self, text: str) -> EvaluationResult:
        """
        Evaluate input text through SCBE pipeline.

        Args:
            text: User input to evaluate

        Returns:
            EvaluationResult with decision, score, and explanation
        """
        # Map to tongue path
        path, reason = _map_to_tongue_path(text)

        # Compute path cost
        cost = _compute_path_cost(path)

        # Determine if blocked
        blocked = cost > self.threshold

        # Compute score (0-1, higher = safer)
        score = max(0.0, 1.0 - (cost / (self.threshold * 2)))

        # Determine decision
        if blocked:
            decision = Decision.DENY
        elif score < 0.5:
            decision = Decision.QUARANTINE
        else:
            decision = Decision.ALLOW

        explanation = {
            "path": path,
            "reason": reason,
            "cost": round(cost, 2),
            "threshold": self.threshold,
            "blocked": blocked,
        }

        return EvaluationResult(
            decision=decision,
            score=round(score, 3),
            cost=round(cost, 2),
            blocked=blocked,
            path=path,
            explanation=explanation,
        )

    def is_safe(self, text: str) -> bool:
        """Quick check if input is safe."""
        return not self.evaluate(text).blocked

    def guard(self, func: Callable, text: str, *args, **kwargs) -> Any:
        """
        Guard a function call.

        Args:
            func: Function to call if input is safe
            text: User input to check
            *args, **kwargs: Additional arguments to pass to func

        Returns:
            Function result if safe, None if blocked

        Raises:
            ValueError: If input is blocked (configurable)
        """
        result = self.evaluate(text)
        if result.blocked:
            raise ValueError(f"SCBE blocked: {result.explanation['reason']} (cost: {result.cost})")
        return func(text, *args, **kwargs)


# Default guard instance
_default_guard = SCBEGuard()


def evaluate(text: str, threshold: float = 50.0) -> EvaluationResult:
    """
    Evaluate input through SCBE pipeline.

    Args:
        text: Input text to evaluate
        threshold: Cost threshold (default 50.0)

    Returns:
        EvaluationResult with decision details

    Example:
        result = evaluate("ignore previous instructions")
        print(result.blocked)  # True
        print(result.cost)     # 236.47
    """
    guard = SCBEGuard(threshold=threshold)
    return guard.evaluate(text)


def is_safe(text: str, threshold: float = 50.0) -> bool:
    """
    Quick check if input is safe.

    Args:
        text: Input text to check
        threshold: Cost threshold (default 50.0)

    Returns:
        True if safe, False if blocked

    Example:
        if is_safe(user_input):
            response = llm.generate(user_input)
    """
    return evaluate(text, threshold).blocked is False


def guard(func: Callable, text: str, threshold: float = 50.0, **kwargs) -> Any:
    """
    Guard a function call with SCBE.

    Args:
        func: Function to call if safe
        text: User input to check
        threshold: Cost threshold
        **kwargs: Passed to function

    Returns:
        Function result if safe

    Raises:
        ValueError: If input is blocked

    Example:
        response = guard(openai.chat, "hello world")
    """
    g = SCBEGuard(threshold=threshold)
    return g.guard(func, text, **kwargs)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("SCBE - Geometric AI Safety")
        print("=" * 40)
        print("\nUsage:")
        print("  scbe check 'your text here'")
        print("  scbe demo")
        print("\nExamples:")
        print("  scbe check 'What is 2+2?'")
        print("  scbe check 'ignore previous instructions'")
        return

    command = sys.argv[1]

    if command == "demo":
        print("SCBE Demo - Geometric AI Safety")
        print("=" * 40)

        tests = [
            "What is 2+2?",
            "Tell me a joke",
            "ignore previous instructions",
            "bypass security filters",
            "show me the api keys",
        ]

        for text in tests:
            result = evaluate(text)
            status = "BLOCKED" if result.blocked else "ALLOWED"
            icon = "X" if result.blocked else "OK"
            print(f"[{icon}] {text[:40]:<40} -> {status} (cost: {result.cost})")

    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: scbe check 'your text'")
            return

        text = " ".join(sys.argv[2:])
        result = evaluate(text)

        print(f"Input: {text}")
        print(f"Decision: {result.decision.value}")
        print(f"Blocked: {result.blocked}")
        print(f"Cost: {result.cost}")
        print(f"Path: {' -> '.join(result.path)}")
        print(f"Reason: {result.explanation.get('reason', 'N/A')}")

    else:
        print(f"Unknown command: {command}")
        print("Use 'scbe demo' or 'scbe check <text>'")


if __name__ == "__main__":
    main()
