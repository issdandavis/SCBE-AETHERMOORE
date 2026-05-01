"""Temporal reliance primitives for delayed agent execution and re-anchoring.

When a task runs after upstream work may have changed, callers must refresh
evidence and downgrade permissions if anchors are UNKNOWN or stale. This module
is pure logic (no I/O) so tests and harness manifests can import it safely.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence


class AnchorState(str, Enum):
    """Whether a prerequisite task outcome is still trustworthy."""

    PROVEN = "PROVEN"  # fresh evidence (e.g. test log + commit hash)
    ASSUMED = "ASSUMED"  # operator accepted risk; time-bounded
    UNKNOWN = "UNKNOWN"  # no evidence or TTL expired


class ReanchorDecision(str, Enum):
    """Policy outcome after evaluating anchors."""

    PROCEED = "PROCEED"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class PrerequisiteRef:
    """Single upstream task reference for temporal reliance."""

    task_id: str
    state: AnchorState
    evidence_digest: str = ""
    stale: bool = False


def evaluate_reanchor(
    prerequisites: Sequence[PrerequisiteRef],
    *,
    permission_mode: str,
) -> Dict[str, Any]:
    """Return a decision and machine-readable reasons.

    Rules (conservative defaults):
    - Any UNKNOWN non-stale prerequisite with workspace-write or above → OBSERVE_ONLY.
    - Any stale PROVEN → treat as UNKNOWN for gating.
    - maintenance / cloud-dispatch still block on UNKNOWN for destructive classes
      (caller adds tool-class checks separately).
    """
    reasons: List[str] = []
    worst = ReanchorDecision.PROCEED

    write_modes = {"workspace-write", "cloud-dispatch", "maintenance"}
    is_write = permission_mode in write_modes

    for p in prerequisites:
        effective = p.state
        if p.state == AnchorState.PROVEN and p.stale:
            effective = AnchorState.UNKNOWN
            reasons.append(f"{p.task_id}: stale PROVEN → UNKNOWN")

        if effective == AnchorState.UNKNOWN:
            reasons.append(f"{p.task_id}: anchor UNKNOWN")
            if is_write:
                worst = ReanchorDecision.OBSERVE_ONLY
        elif effective == AnchorState.ASSUMED:
            reasons.append(f"{p.task_id}: ASSUMED (time-bounded risk)")

    return {
        "schema_version": "scbe_temporal_reliance_eval_v1",
        "decision": worst.value,
        "permission_mode": permission_mode,
        "reasons": reasons,
        "prerequisite_count": len(prerequisites),
    }


def build_agent_execution_stack_v1() -> Dict[str, Any]:
    """Model-neutral stack: execution, review, temporal reliance + L11 caveat."""

    return {
        "schema_version": "scbe_agent_execution_stack_v1",
        "l11_canonicalization_status": "underspecified_multi_implementation",
        "l11_candidate_canonical": "phi_power_mean_triadic_temporal_distance",
        "l11_reference_impl": "src/polly_pads_runtime.py:triadic_temporal_distance",
        "execution_layer": {
            "purpose": "Bounded, auditable runs only; commit-time gates for generation.",
            "surfaces": [
                "src/governance/stage6_constrained_decoding.py",
                "scripts/agents/scbe_code.py",
                "src.geoseal_cli code-packet | testing-cli | project-scaffold",
            ],
            "principles": [
                "No unbounded shell from model text",
                "Artifact-first: stdout/stderr + exit code + optional JSON envelope",
                "Stage 6 bridges autoregressive generation to substring/token contract",
            ],
        },
        "review_layer": {
            "purpose": "Independent verification; IV&V / peer-review analog.",
            "surfaces": [
                "npm test / pytest targets",
                "scripts/benchmark/agentic_benchmark_ladder.py",
                "Human explicit approval for destructive_filesystem and secrets",
            ],
            "forbidden": ["model_self_signoff_as_sole_verifier_for_writes"],
            "nasa_analog": "NPR 7150.2 verification records; IV&V where required; peer inspections",
        },
        "temporal_reliance_layer": {
            "purpose": "Delayed execution re-anchors to tasks that may or may not have completed.",
            "anchor_states": [s.value for s in AnchorState],
            "reanchor_protocol": [
                "Refresh evidence: git rev, test log hash, manifest digest",
                "If upstream UNKNOWN or stale: downgrade to observe or block writes",
                "Re-run minimal review slice (smoke + targeted tests)",
                "Append result to history/replay envelope",
            ],
            "evaluator": "src.coding_spine.agent_temporal_reliance.evaluate_reanchor",
        },
        "bijection_boundary": {
            "strict_paths": ["SS1 payload bijection", "STIB", "ISA compile/disassemble"],
            "generation_path": "non_bijective",
            "commit_bridge": "Stage 6 constrained decoding + lawful opcode / packet checks",
        },
    }
