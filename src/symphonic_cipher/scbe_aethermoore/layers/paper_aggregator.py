"""
SCBE Paper Aggregator
=====================

Layer-1-gated aggregation for repo/package/source snapshots used by
documentation synthesis and training pipelines.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Sequence

import numpy as np
import requests

from src.scbe_14layer_reference import scbe_14layer_pipeline


JsonDict = Dict[str, Any]
JsonFetcher = Callable[[str], JsonDict]
GateFn = Callable[[Mapping[str, Any], int], Mapping[str, Any]]


@dataclass(frozen=True)
class AggregationIntent:
    repos: Sequence[str]
    npm_package: str
    space_files: Sequence[str]

    def to_payload(self) -> JsonDict:
        return {
            "repos": list(self.repos),
            "npm_package": self.npm_package,
            "space_files": list(self.space_files),
        }


def _hash_to_unit_bytes(value: Mapping[str, Any]) -> np.ndarray:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).digest()
    return np.frombuffer(digest, dtype=np.uint8).astype(np.float64) / 255.0


def intent_vector(intent: Mapping[str, Any], D: int = 6) -> np.ndarray:
    """
    Build deterministic 2D vector (amplitudes + phases) for SCBE gating.
    """
    if D <= 0:
        raise ValueError("D must be positive")

    base = _hash_to_unit_bytes(intent)
    required = 2 * D
    if len(base) < required:
        repeats = int(np.ceil(required / len(base)))
        base = np.tile(base, repeats)

    amplitudes = base[:D]
    phases = (base[D : 2 * D] * (2 * np.pi)) - np.pi
    return np.concatenate([amplitudes, phases])


def govern_aggregation_intent(intent: Mapping[str, Any], D: int = 6) -> JsonDict:
    vec = intent_vector(intent, D=D)
    result = scbe_14layer_pipeline(t=vec, D=D)
    decision = str(result.get("decision", "DENY"))
    status = "ALLOW" if decision == "ALLOW" else "QUARANTINE"
    return {
        "status": status,
        "decision": decision,
        "d_star": float(result.get("d_star", 0.0)),
        "risk_prime": float(result.get("risk_prime", 1.0)),
        "H": float(result.get("H", 1.0)),
    }


def _fetch_json(url: str) -> JsonDict:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def _safe_bundle_cost(item_count: int) -> float:
    # Keep bounded to avoid overflow while preserving monotonic growth.
    exponent = min(50.0, float(item_count * item_count))
    return float(math.exp(exponent))


def aggregate_sources(
    repos: Sequence[str] | None = None,
    npm_package: str = "izdandavis",
    space_files: Sequence[str] | None = None,
    github_fetcher: JsonFetcher | None = None,
    npm_fetcher: JsonFetcher | None = None,
    gate_fn: GateFn = govern_aggregation_intent,
    D: int = 6,
) -> JsonDict:
    repos = repos or ["issdandavis/SCBE-AETHERMOORE"]
    space_files = list(space_files or [])
    github_fetcher = github_fetcher or _fetch_json
    npm_fetcher = npm_fetcher or _fetch_json

    intent = AggregationIntent(
        repos=repos,
        npm_package=npm_package,
        space_files=space_files,
    )

    gate = dict(gate_fn(intent.to_payload(), D))
    if gate.get("status") != "ALLOW":
        return {
            "status": "QUARANTINE",
            "reason": "aggregation gate denied",
            "gate": gate,
            "bundle": {},
        }

    bundle: JsonDict = {
        "repos": {},
        "npm": {},
        "space": [],
        "fetch_errors": [],
    }

    for repo in repos:
        url = f"https://api.github.com/repos/{repo}/contents"
        try:
            bundle["repos"][repo] = github_fetcher(url)
        except Exception as exc:  # noqa: BLE001
            bundle["repos"][repo] = []
            bundle["fetch_errors"].append({"source": "github", "target": repo, "error": str(exc)})

    npm_url = f"https://registry.npmjs.org/{npm_package}"
    try:
        bundle["npm"] = npm_fetcher(npm_url)
    except Exception as exc:  # noqa: BLE001
        bundle["npm"] = {}
        bundle["fetch_errors"].append(
            {"source": "npm", "target": npm_package, "error": str(exc)}
        )

    for file_name in space_files:
        bundle["space"].append({"file": file_name, "content": "external-export-placeholder"})

    bundle_bytes = json.dumps(bundle, sort_keys=True, default=str).encode("utf-8")
    bundle_hash = hashlib.sha256(bundle_bytes).hexdigest()
    item_count = len(repos) + len(space_files) + (1 if npm_package else 0)
    cost = _safe_bundle_cost(item_count)

    return {
        "status": "ALLOW",
        "gate": gate,
        "bundle_hash": bundle_hash,
        "cost": cost,
        "bundle": bundle,
    }
