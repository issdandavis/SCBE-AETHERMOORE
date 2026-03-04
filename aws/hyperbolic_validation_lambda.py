"""Hyperbolic validation Lambda handler (stateless governance path).

Implements exponential penalty H(d)=exp(d^2) and containment decisions:
ALLOW, QUARANTINE, DENY.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List


SAFE_CENTER = [0.0, 0.0, 0.0]
QUARANTINE_DISTANCE = 0.75
DENY_DISTANCE = 0.95


def _distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _penalty(distance: float) -> float:
    return float(math.exp(distance * distance))


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    body = event.get("body")
    if isinstance(body, str):
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}
    elif isinstance(body, dict):
        payload = body
    else:
        payload = event

    position = payload.get("position", [0.0, 0.0, 0.0])
    if not isinstance(position, list) or len(position) < 3:
        position = [0.0, 0.0, 0.0]

    point = [float(position[0]), float(position[1]), float(position[2])]
    dist = _distance(point, SAFE_CENTER)
    penalty = _penalty(dist)

    if dist >= DENY_DISTANCE:
        decision = "DENY"
    elif dist >= QUARANTINE_DISTANCE:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    result = {
        "decision": decision,
        "distance": round(dist, 6),
        "penalty": round(penalty, 6),
        "thresholds": {
            "quarantine": QUARANTINE_DISTANCE,
            "deny": DENY_DISTANCE,
        },
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
