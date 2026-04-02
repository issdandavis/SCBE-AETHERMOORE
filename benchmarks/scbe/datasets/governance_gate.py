"""Governance gate prediction dataset builder.

Creates a deterministic, local-first benchmark dataset that mirrors the
public ``/governance-check`` API behavior without exposing plaintext or
sealed storage payloads.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import numpy as np

from src.scbe_14layer_reference import scbe_14layer_pipeline

CONTEXT_PARAMS: Dict[str, Dict[str, float]] = {
    "internal": {"w_d": 0.20, "w_c": 0.20, "w_s": 0.20, "w_tau": 0.20, "w_a": 0.20},
    "external": {"w_d": 0.30, "w_c": 0.15, "w_s": 0.15, "w_tau": 0.30, "w_a": 0.10},
    "untrusted": {"w_d": 0.35, "w_c": 0.10, "w_s": 0.10, "w_tau": 0.35, "w_a": 0.10},
}

CONTEXT_ORDER = ("internal", "external", "untrusted")
SPLIT_THRESHOLDS = {"train": 70, "validation": 85, "test": 100}

AGENT_ROLES = [
    "operator",
    "auditor",
    "router",
    "builder",
    "keeper",
    "watcher",
    "scribe",
    "analyst",
    "broker",
    "navigator",
]

TOPIC_FAMILIES = [
    "auth",
    "payments",
    "memory",
    "swarm",
    "browser",
    "compute",
    "telemetry",
    "training",
    "fleet",
    "docs",
]

TOPIC_MODIFIERS = [
    "handoff",
    "rotation",
    "containment",
    "promotion",
    "throttle",
    "audit",
    "handover",
    "observer",
    "canary",
    "fallback",
]

TOPIC_CHANNELS = [
    "mobile",
    "api",
    "runtime",
    "orchestrator",
    "storage",
    "checkout",
    "ingest",
    "scheduler",
]


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def governance_position(agent: str, topic: str) -> List[int]:
    """Mirror the synthetic position generation used by ``/governance-check``."""
    digest = hashlib.sha256(f"{agent}:{topic}".encode("utf-8")).digest()
    return [int(byte) % 100 for byte in digest[:6]]


def assign_split(group_id: str) -> str:
    """Stable, grouped split assignment based on the group hash."""
    bucket = int(group_id[:8], 16) % 100
    if bucket < SPLIT_THRESHOLDS["train"]:
        return "train"
    if bucket < SPLIT_THRESHOLDS["validation"]:
        return "validation"
    return "test"


def _generate_groups(group_count: int, seed: int) -> List[Dict[str, str]]:
    rng = random.Random(seed)
    groups: List[Dict[str, str]] = []
    for idx in range(group_count):
        role = AGENT_ROLES[idx % len(AGENT_ROLES)]
        family = TOPIC_FAMILIES[rng.randrange(len(TOPIC_FAMILIES))]
        modifier = TOPIC_MODIFIERS[rng.randrange(len(TOPIC_MODIFIERS))]
        channel = TOPIC_CHANNELS[rng.randrange(len(TOPIC_CHANNELS))]
        agent = f"{role}-{idx:04d}"
        topic = f"{family}:{modifier}:{channel}:{rng.randrange(1000, 9999)}"
        groups.append({"agent": agent, "topic": topic})
    return groups


def build_governance_gate_row(agent: str, topic: str, context: str) -> Dict[str, Any]:
    """Build one benchmark row from the live governance-check math."""
    if context not in CONTEXT_PARAMS:
        raise ValueError(f"Unsupported context {context!r}")

    position = governance_position(agent, topic)
    result = scbe_14layer_pipeline(
        t=np.array(position, dtype=float),
        D=6,
        **CONTEXT_PARAMS[context],
    )

    group_id = _sha256_hex(f"{agent}|{topic}")[:16]
    return {
        "id": f"ggp-{group_id}-{context}",
        "split": assign_split(group_id),
        "group_id": group_id,
        "source": "governance_check_v1",
        "inputs": {
            "context": context,
            "agent_hash": _sha256_hex(agent)[:16],
            "topic_hash": _sha256_hex(topic)[:16],
            "position": position,
            "harmonic_factor": float(result["H"]),
            "d_star": float(result["d_star"]),
            "d_tri_norm": float(result["d_tri_norm"]),
            "coherence_metrics": {
                key: float(value) for key, value in result["coherence"].items()
            },
            "geometry": {
                key: float(value) for key, value in result["geometry"].items()
            },
        },
        "labels": {
            "decision": result["decision"],
            "risk_score": float(result["risk_base"]),
            "risk_prime": float(result["risk_prime"]),
        },
    }


def build_governance_gate_dataset(group_count: int = 512, seed: int = 42) -> List[Dict[str, Any]]:
    """Create the full grouped dataset across all governance contexts."""
    rows: List[Dict[str, Any]] = []
    for group in _generate_groups(group_count=group_count, seed=seed):
        for context in CONTEXT_ORDER:
            rows.append(build_governance_gate_row(group["agent"], group["topic"], context))
    return rows


def summarize_governance_gate_dataset(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize split, context, and decision coverage."""
    split_counts = {split: 0 for split in SPLIT_THRESHOLDS}
    context_counts = {context: 0 for context in CONTEXT_ORDER}
    decision_counts: Dict[str, int] = {}
    groups_by_split: Dict[str, set[str]] = {split: set() for split in SPLIT_THRESHOLDS}

    for row in rows:
        split = row["split"]
        context = row["inputs"]["context"]
        decision = row["labels"]["decision"]
        split_counts[split] = split_counts.get(split, 0) + 1
        context_counts[context] = context_counts.get(context, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        groups_by_split.setdefault(split, set()).add(row["group_id"])

    return {
        "total_rows": len(rows),
        "split_counts": split_counts,
        "context_counts": context_counts,
        "decision_counts": decision_counts,
        "group_counts": {split: len(group_ids) for split, group_ids in groups_by_split.items()},
    }


def write_governance_gate_dataset(rows: Sequence[Dict[str, Any]], output_dir: Path) -> Dict[str, Path]:
    """Persist split JSONL files and a summary JSON payload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    for split in ("train", "validation", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        path = output_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in split_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        written[split] = path

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summarize_governance_gate_dataset(rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["summary"] = summary_path
    return written


def load_governance_gate_rows(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    """Load rows from one or more JSONL files."""
    rows: List[Dict[str, Any]] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows
