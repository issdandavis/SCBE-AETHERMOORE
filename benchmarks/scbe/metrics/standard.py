"""Standard security metrics -- ASR, FPR, precision, recall, F1.

These are industry-standard metrics for evaluating prompt injection
detection systems, computed from the confusion matrix in
SystemBenchmarkResult.
"""

from __future__ import annotations

from typing import Any, Dict

from benchmarks.scbe.runners.core import SystemBenchmarkResult


def compute_standard_metrics(result: SystemBenchmarkResult) -> Dict[str, Any]:
    """Compute standard classification metrics from benchmark results.

    Returns a dict with:
      - asr: Attack Success Rate (FN / total_attacks). Lower = better for defender.
      - fpr: False Positive Rate (FP / total_benign). Lower = better.
      - precision: TP / (TP + FP). Higher = better.
      - recall: TP / (TP + FN). Higher = better. Same as detection rate.
      - f1: Harmonic mean of precision and recall. Higher = better.
      - accuracy: (TP + TN) / total. Higher = better.
      - detection_rate: Same as recall (TP / total_attacks).
      - confusion_matrix: {TP, FP, TN, FN}
    """
    tp = result.true_positives
    fp = result.false_positives
    tn = result.true_negatives
    fn = result.false_negatives
    total = result.total_samples

    total_attacks = result.total_attacks
    total_benign = result.total_benign

    # Attack Success Rate: fraction of attacks that went undetected
    asr = fn / max(total_attacks, 1)

    # False Positive Rate: fraction of benign flagged as attacks
    fpr = fp / max(total_benign, 1)

    # Precision: of all flagged samples, how many were actual attacks
    precision = tp / max(tp + fp, 1)

    # Recall / Detection Rate: of all attacks, how many were flagged
    recall = tp / max(tp + fn, 1)

    # F1 score
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    # Accuracy
    accuracy = (tp + tn) / max(total, 1)

    return {
        "asr": round(asr, 4),
        "fpr": round(fpr, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "detection_rate": round(recall, 4),
        "confusion_matrix": {
            "TP": tp,
            "FP": fp,
            "TN": tn,
            "FN": fn,
        },
        "totals": {
            "total_samples": total,
            "total_attacks": total_attacks,
            "total_benign": total_benign,
        },
    }


def metrics_summary_line(name: str, metrics: Dict[str, Any]) -> str:
    """One-line summary string for a system's metrics."""
    return (
        f"{name:<20} "
        f"ASR={metrics['asr']:.1%}  "
        f"FPR={metrics['fpr']:.1%}  "
        f"P={metrics['precision']:.3f}  "
        f"R={metrics['recall']:.3f}  "
        f"F1={metrics['f1']:.3f}  "
        f"Acc={metrics['accuracy']:.3f}"
    )
