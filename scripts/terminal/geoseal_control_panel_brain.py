#!/usr/bin/env python3
"""Tiny deterministic control-panel brain for GeoSeal harness routing.

This is intentionally not a neural model. It is the implant slot: a small,
auditable router that turns a goal, provider matrix, and risk/return hints into
the next harness action. A learned local model can replace the scoring function
later while preserving this JSON contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ControlPanelTurn:
    schema_version: str
    intent: str
    route_mode: str
    recommended_provider: str
    recommended_model_ref: str
    verdict: str
    return_horizon: str
    action_id: str
    lane_signal: str
    reason: str
    evidence_required: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_required"] = list(self.evidence_required)
        return payload


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def classify_intent(goal: str) -> str:
    text = _norm(goal)
    if any(token in text for token in ("fix", "bug", "error", "traceback", "fail", "regression")):
        return "repair"
    if any(token in text for token in ("train", "dataset", "eval", "benchmark", "score", "kaggle", "hf")):
        return "training_eval"
    if any(token in text for token in ("release", "publish", "package", "pypi", "npm", "ship")):
        return "release"
    if any(token in text for token in ("design", "architecture", "tokenizer", "braid", "swarm", "fleet")):
        return "design"
    if any(token in text for token in ("secret", "key", "credential", "token", "env")):
        return "security"
    return "general"


def classify_return_horizon(intent: str) -> str:
    if intent in {"repair", "security", "release"}:
        return "fast"
    if intent in {"training_eval"}:
        return "medium"
    if intent == "design":
        return "long"
    return "medium"


def _available_models(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [model for model in matrix.get("models", []) if model.get("available")]


def _score_model(model: dict[str, Any], *, intent: str, return_horizon: str) -> tuple[int, str]:
    provider = str(model.get("provider") or "")
    capabilities = set(model.get("capabilities") or [])
    model_id = str(model.get("model") or "").lower()
    score = 0
    reasons: list[str] = []

    if model.get("local"):
        score += 2
        reasons.append("local-first")
    else:
        score += 1

    if intent in {"repair", "training_eval"} and "coding" in capabilities:
        score += 5
        reasons.append("coding-capable")
    if intent in {"design", "training_eval"} and "reasoning" in capabilities:
        score += 4
        reasons.append("reasoning-capable")
    if intent == "security" and provider in {"ollama", "lmstudio", "llamacpp", "vllm"}:
        score += 6
        reasons.append("keeps-sensitive-context-local")
    if intent == "release" and provider in {"ollama", "huggingface", "nvidia", "cerebras"}:
        score += 3
        reasons.append("release-gate-friendly")

    if provider == "nvidia":
        score += 3
        reasons.append("large-model-overseer")
    if "qwen" in model_id and "coder" in model_id:
        score += 4
        reasons.append("qwen-coder-default")
    if "nemotron" in model_id:
        score += 2
        reasons.append("governance-reasoning")
    if return_horizon == "long" and provider == "nvidia":
        score += 2
        reasons.append("long-horizon-review")

    return score, ",".join(reasons) or "baseline"


def recommend_turn(*, goal: str, matrix: dict[str, Any]) -> ControlPanelTurn:
    intent = classify_intent(goal)
    horizon = classify_return_horizon(intent)
    models = _available_models(matrix) or list(matrix.get("models", []))

    if not models:
        return ControlPanelTurn(
            schema_version="scbe_geoseal_control_panel_turn_v1",
            intent=intent,
            route_mode="hold",
            recommended_provider="none",
            recommended_model_ref="",
            verdict="HOLD",
            return_horizon=horizon,
            action_id="observe-room",
            lane_signal="",
            reason="No available provider lane found.",
            evidence_required=("run harness-terminal provider matrix",),
        )

    if intent == "security":
        local_models = [model for model in models if model.get("local")]
        if local_models:
            models = local_models

    scored = sorted(
        ((_score_model(model, intent=intent, return_horizon=horizon), model) for model in models),
        key=lambda item: (item[0][0], item[1].get("provider") == "nvidia"),
        reverse=True,
    )
    (score, reason_bits), selected = scored[0]
    provider = str(selected.get("provider") or "")
    ref = str(selected.get("ref") or "")

    if intent == "security":
        verdict = "HOLD" if selected.get("local") is True else "ESCALATE"
        route_mode = "local_secret_review" if selected.get("local") is True else "local_first_required"
        action_id = "inspect-object"
        evidence = ("confirm no secrets leave local context", "prefer local provider before remote model call")
    elif intent == "design":
        verdict = "INCUBATE"
        route_mode = "long_horizon_review"
        action_id = "inspect-object"
        evidence = ("write a compact design residue", "promote only after tests or routeable code exist")
    elif intent == "repair":
        verdict = "PROMOTE"
        route_mode = "repair_then_verify"
        action_id = "solve-checkpoint"
        evidence = ("targeted test command", "changed file list", "pass/fail artifact")
    elif intent == "training_eval":
        verdict = "HOLD"
        route_mode = "judge_then_launch"
        action_id = "verify-evidence"
        evidence = ("dataset manifest", "eval split", "scorecard or gate artifact")
    elif intent == "release":
        verdict = "HOLD"
        route_mode = "release_gate"
        action_id = "verify-evidence"
        evidence = ("release readiness report", "package diff", "rollback note")
    else:
        verdict = "HOLD"
        route_mode = "observe_then_route"
        action_id = "observe-room"
        evidence = ("provider matrix", "narrow goal statement")

    lane_signal = "" if provider in {"ollama", "lmstudio", "llamacpp", "vllm"} else f"provider-pair:local->{provider}:{intent}"
    return ControlPanelTurn(
        schema_version="scbe_geoseal_control_panel_turn_v1",
        intent=intent,
        route_mode=route_mode,
        recommended_provider=provider,
        recommended_model_ref=ref,
        verdict=verdict,
        return_horizon=horizon,
        action_id=action_id,
        lane_signal=lane_signal,
        reason=f"score={score}; {reason_bits}",
        evidence_required=tuple(evidence),
    )
