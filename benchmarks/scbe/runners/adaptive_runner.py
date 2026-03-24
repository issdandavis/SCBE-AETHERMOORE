"""Adaptive runner -- runs the adaptive attacker against each detection system.

For each system, picks a set of seed prompts and runs multi-round
adaptive attacks. Reports per-system evasion rates and which mutation
strategies were most effective.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from benchmarks.scbe.attacks.adaptive_engine import (
    AdaptiveAttacker,
    AdaptiveAttackResult,
)
from benchmarks.scbe.config import ADAPTIVE_ROUNDS, ADAPTIVE_MUTATIONS_PER_ROUND

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Result types
# --------------------------------------------------------------------------- #

@dataclass
class AdaptiveSystemResult:
    """Result of running adaptive attacks against one system."""
    system_name: str
    total_seeds: int
    total_attempts: int
    total_evasions: int
    attack_results: List[AdaptiveAttackResult] = field(default_factory=list)
    strategy_scores: Dict[str, float] = field(default_factory=dict)
    elapsed_s: float = 0.0

    @property
    def overall_evasion_rate(self) -> float:
        return self.total_evasions / max(self.total_attempts, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system": self.system_name,
            "total_seeds": self.total_seeds,
            "total_attempts": self.total_attempts,
            "total_evasions": self.total_evasions,
            "overall_evasion_rate": round(self.overall_evasion_rate, 4),
            "strategy_scores": {
                k: round(v, 3) for k, v in self.strategy_scores.items()
            },
            "elapsed_s": round(self.elapsed_s, 2),
            "per_seed": [r.to_dict() for r in self.attack_results],
        }


# --------------------------------------------------------------------------- #
#  Runner
# --------------------------------------------------------------------------- #

DetectFn = Callable[[str], Tuple[bool, List[str], Dict[str, Any]]]


def _wrap_detect_fn(
    detect_fn: DetectFn,
) -> Callable[[str], Tuple[bool, List[str]]]:
    """Wrap a 3-tuple detect_fn into a 2-tuple for the adaptive engine."""
    def wrapped(prompt: str) -> Tuple[bool, List[str]]:
        detected, signals, _ = detect_fn(prompt)
        return detected, signals
    return wrapped


def run_adaptive_benchmark(
    system_name: str,
    detect_fn: DetectFn,
    seed_prompts: List[str],
    rounds: int = ADAPTIVE_ROUNDS,
    mutations_per_round: int = ADAPTIVE_MUTATIONS_PER_ROUND,
    calibrate_fn: Optional[Callable[[List[str]], None]] = None,
    calibration_texts: Optional[List[str]] = None,
    reset_fn: Optional[Callable[[], None]] = None,
    seed: int = 42,
) -> AdaptiveSystemResult:
    """Run adaptive attacks against a single system.

    Args:
        system_name: Name of the detection system.
        detect_fn: Callable(prompt) -> (detected, signals, metadata).
        seed_prompts: Initial attack prompts to mutate from.
        rounds: Number of adaptive rounds per seed.
        mutations_per_round: Mutations tried per round.
        calibrate_fn: Optional calibration function.
        calibration_texts: Clean texts for calibration.
        reset_fn: Optional function to reset system state.
        seed: Random seed for reproducibility.

    Returns:
        AdaptiveSystemResult with per-seed and aggregate results.
    """
    if reset_fn is not None:
        reset_fn()

    if calibrate_fn is not None and calibration_texts:
        calibrate_fn(calibration_texts)

    wrapped = _wrap_detect_fn(detect_fn)
    attacker = AdaptiveAttacker(
        rounds=rounds,
        mutations_per_round=mutations_per_round,
        seed=seed,
    )

    attack_results: List[AdaptiveAttackResult] = []
    total_attempts = 0
    total_evasions = 0

    start = time.perf_counter()

    for i, seed_prompt in enumerate(seed_prompts):
        logger.info(
            "  Adaptive attack %d/%d against %s",
            i + 1, len(seed_prompts), system_name,
        )
        result = attacker.run(seed_prompt, wrapped)
        attack_results.append(result)
        total_attempts += result.total_attempts
        total_evasions += result.evasions

    elapsed = time.perf_counter() - start

    sys_result = AdaptiveSystemResult(
        system_name=system_name,
        total_seeds=len(seed_prompts),
        total_attempts=total_attempts,
        total_evasions=total_evasions,
        attack_results=attack_results,
        strategy_scores=attacker.strategy_scores,
        elapsed_s=elapsed,
    )

    logger.info(
        "%s adaptive: %d seeds, %d attempts, %d evasions (%.1f%%) in %.1fs",
        system_name,
        len(seed_prompts),
        total_attempts,
        total_evasions,
        sys_result.overall_evasion_rate * 100,
        elapsed,
    )

    return sys_result
