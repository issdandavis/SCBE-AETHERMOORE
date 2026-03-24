"""Core benchmark runner -- runs a detection system against a dataset.

Produces per-sample results with timing, then aggregates into a
SystemBenchmarkResult that feeds into the metrics and reporting layers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Per-sample result
# --------------------------------------------------------------------------- #

@dataclass
class SampleResult:
    """Result of running one sample through a detection system."""
    sample_id: str
    prompt: str
    ground_truth: int          # 1 = attack, 0 = benign
    attack_class: str
    source: str
    # System output
    detected: bool             # System classified as attack
    signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Timing
    latency_ms: float = 0.0

    @property
    def correct(self) -> bool:
        """Whether the system made the correct decision."""
        if self.ground_truth == 1:
            return self.detected        # True positive
        else:
            return not self.detected    # True negative

    @property
    def is_true_positive(self) -> bool:
        return self.ground_truth == 1 and self.detected

    @property
    def is_false_positive(self) -> bool:
        return self.ground_truth == 0 and self.detected

    @property
    def is_true_negative(self) -> bool:
        return self.ground_truth == 0 and not self.detected

    @property
    def is_false_negative(self) -> bool:
        return self.ground_truth == 1 and not self.detected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.sample_id,
            "class": self.attack_class,
            "source": self.source,
            "ground_truth": self.ground_truth,
            "detected": self.detected,
            "correct": self.correct,
            "signals": self.signals,
            "latency_ms": round(self.latency_ms, 2),
        }


# --------------------------------------------------------------------------- #
#  Aggregate result
# --------------------------------------------------------------------------- #

@dataclass
class SystemBenchmarkResult:
    """Aggregate result for one system across the full dataset."""
    system_name: str
    system_description: str
    total_samples: int
    results: List[SampleResult]
    total_time_s: float = 0.0

    # Confusion matrix
    @property
    def true_positives(self) -> int:
        return sum(1 for r in self.results if r.is_true_positive)

    @property
    def false_positives(self) -> int:
        return sum(1 for r in self.results if r.is_false_positive)

    @property
    def true_negatives(self) -> int:
        return sum(1 for r in self.results if r.is_true_negative)

    @property
    def false_negatives(self) -> int:
        return sum(1 for r in self.results if r.is_false_negative)

    @property
    def total_attacks(self) -> int:
        return sum(1 for r in self.results if r.ground_truth == 1)

    @property
    def total_benign(self) -> int:
        return sum(1 for r in self.results if r.ground_truth == 0)

    @property
    def per_class_results(self) -> Dict[str, Dict[str, Any]]:
        """Break down results by attack class."""
        classes: Dict[str, Dict[str, Any]] = {}
        for r in self.results:
            cls = r.attack_class or "unknown"
            if cls not in classes:
                classes[cls] = {"total": 0, "detected": 0, "correct": 0}
            classes[cls]["total"] += 1
            if r.detected:
                classes[cls]["detected"] += 1
            if r.correct:
                classes[cls]["correct"] += 1
        # Add rates
        for cls, data in classes.items():
            data["detection_rate"] = round(
                data["detected"] / max(data["total"], 1), 4
            )
            data["accuracy"] = round(
                data["correct"] / max(data["total"], 1), 4
            )
        return classes

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system": self.system_name,
            "description": self.system_description,
            "total_samples": self.total_samples,
            "total_attacks": self.total_attacks,
            "total_benign": self.total_benign,
            "confusion_matrix": {
                "TP": self.true_positives,
                "FP": self.false_positives,
                "TN": self.true_negatives,
                "FN": self.false_negatives,
            },
            "per_class": self.per_class_results,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "total_time_s": round(self.total_time_s, 2),
        }


# --------------------------------------------------------------------------- #
#  Runner
# --------------------------------------------------------------------------- #

DetectFn = Callable[[str], Tuple[bool, List[str], Dict[str, Any]]]


def run_system_benchmark(
    system_name: str,
    system_description: str,
    detect_fn: DetectFn,
    dataset: List[Dict[str, Any]],
    calibrate_fn: Optional[Callable[[List[str]], None]] = None,
    calibration_texts: Optional[List[str]] = None,
    reset_fn: Optional[Callable[[], None]] = None,
) -> SystemBenchmarkResult:
    """Run a detection system against a labeled dataset.

    Args:
        system_name: Name of the system being tested.
        system_description: Human-readable description.
        detect_fn: Callable(prompt) -> (detected, signals, metadata).
        dataset: List of dicts with keys: id, prompt, label, source, class.
        calibrate_fn: Optional function to calibrate with clean texts.
        calibration_texts: Texts used for calibration.
        reset_fn: Optional function to reset system state before run.

    Returns:
        SystemBenchmarkResult with per-sample and aggregate results.
    """
    if reset_fn is not None:
        reset_fn()

    if calibrate_fn is not None and calibration_texts:
        calibrate_fn(calibration_texts)

    results: List[SampleResult] = []
    start_total = time.perf_counter()

    for sample in dataset:
        prompt = sample["prompt"]
        start_sample = time.perf_counter()

        try:
            detected, signals, metadata = detect_fn(prompt)
        except Exception as exc:
            logger.error(
                "Error processing sample %s: %s", sample.get("id", "?"), exc
            )
            detected = False
            signals = [f"error({exc})"]
            metadata = {"error": str(exc)}

        elapsed_ms = (time.perf_counter() - start_sample) * 1000.0

        results.append(SampleResult(
            sample_id=sample.get("id", ""),
            prompt=prompt[:200],
            ground_truth=sample.get("label", 0),
            attack_class=sample.get("class", "unknown"),
            source=sample.get("source", "unknown"),
            detected=detected,
            signals=signals,
            metadata=metadata,
            latency_ms=elapsed_ms,
        ))

    total_time = time.perf_counter() - start_total

    result = SystemBenchmarkResult(
        system_name=system_name,
        system_description=system_description,
        total_samples=len(results),
        results=results,
        total_time_s=total_time,
    )

    logger.info(
        "%s: %d samples in %.2fs (TP=%d FP=%d TN=%d FN=%d)",
        system_name,
        len(results),
        total_time,
        result.true_positives,
        result.false_positives,
        result.true_negatives,
        result.false_negatives,
    )

    return result
