"""Metrics for Governance Gate Prediction benchmark rows."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Sequence

DECISION_LABELS = ("ALLOW", "QUARANTINE", "DENY")


def _macro_f1(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None) -> float:
    active_labels = tuple(labels) if labels is not None else tuple(sorted(set(y_true) | set(y_pred)))
    scores: List[float] = []
    for label in active_labels:
        tp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred == label)
        fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual != label and pred == label)
        fn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == label and pred != label)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(2.0 * precision * recall / (precision + recall))
    return sum(scores) / max(len(scores), 1)


def _normalized_rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    if not y_true:
        return 0.0
    mse = sum((actual - pred) ** 2 for actual, pred in zip(y_true, y_pred)) / len(y_true)
    rmse = math.sqrt(mse)
    low = min(y_true)
    high = max(y_true)
    scale = max(high - low, 1e-9)
    return min(rmse / scale, 1.0)


def _resolve_decision(prediction: Dict[str, Any]) -> str:
    if "decision" in prediction:
        return str(prediction["decision"])

    scores = {
        "ALLOW": float(prediction.get("decision_prob_allow", 0.0)),
        "QUARANTINE": float(prediction.get("decision_prob_quarantine", 0.0)),
        "DENY": float(prediction.get("decision_prob_deny", 0.0)),
    }
    return max(scores.items(), key=lambda item: item[1])[0]


def compute_governance_gate_metrics(
    references: Sequence[Dict[str, Any]],
    predictions: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """Score decision and risk predictions against reference rows."""
    ref_by_id = {row["id"]: row for row in references}
    prediction_rows = list(predictions)

    missing = sorted(set(ref_by_id) - {pred["id"] for pred in prediction_rows})
    if missing:
        raise ValueError(f"Missing predictions for ids: {missing[:5]}")

    y_true_decision: List[str] = []
    y_pred_decision: List[str] = []
    y_true_risk: List[float] = []
    y_pred_risk: List[float] = []

    for prediction in prediction_rows:
        reference = ref_by_id[prediction["id"]]
        y_true_decision.append(reference["labels"]["decision"])
        y_pred_decision.append(_resolve_decision(prediction))
        y_true_risk.append(float(reference["labels"]["risk_prime"]))
        y_pred_risk.append(float(prediction["risk_prime_pred"]))

    macro_f1 = _macro_f1(y_true_decision, y_pred_decision)
    normalized_rmse = _normalized_rmse(y_true_risk, y_pred_risk)
    accuracy = sum(1 for actual, pred in zip(y_true_decision, y_pred_decision) if actual == pred) / max(
        len(y_true_decision), 1
    )
    blended_score = 0.70 * macro_f1 + 0.30 * (1.0 - normalized_rmse)

    return {
        "macro_f1": round(macro_f1, 6),
        "accuracy": round(accuracy, 6),
        "normalized_rmse": round(normalized_rmse, 6),
        "risk_score": round(1.0 - normalized_rmse, 6),
        "blended_score": round(blended_score, 6),
        "total_predictions": len(prediction_rows),
    }
