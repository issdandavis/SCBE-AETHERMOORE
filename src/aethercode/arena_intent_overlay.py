"""Intent overlay for the AetherCode Arena round table.

HTML is the human-readable board. This module provides the compact Python
contract that agents can read before acting: who is speaking, which Sacred
Tongue lane they occupy, what they should optimize for, and how their output
will be chained into the next receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "aethercode_arena_intent_overlay_v1"


@dataclass(frozen=True)
class ArenaSeat:
    seat_id: str
    name: str
    tongue: str
    role: str
    model_hint: str
    objective: str


@dataclass(frozen=True)
class ArenaIntentBlock:
    schema_version: str
    seat: ArenaSeat
    problem_hash: str
    shared_code_hash: str
    intent: str
    readout_axis: str
    route_contract: str
    receipt_contract: str
    build_state_contract: dict[str, str]
    advancement_rule: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["seat"] = asdict(self.seat)
        return payload


DEFAULT_SEATS: tuple[ArenaSeat, ...] = (
    ArenaSeat("groq", "Groq", "KO", "Intent Analyst", "llama-3.3-70b-versatile", "extract the user's real goal"),
    ArenaSeat("cerebras", "Cerebras", "RU", "Security Auditor", "llama-3.3-70b", "find breakage, risk, and invalid assumptions"),
    ArenaSeat("google_ai", "Google AI", "DR", "Lead Architect", "gemini-2.5-flash", "synthesize a working plan"),
    ArenaSeat("claude", "Claude", "UM", "Governance Arbiter", "claude-sonnet", "judge policy, consistency, and scope"),
    ArenaSeat("xai", "xAI", "AV", "Creative Advocate", "grok-3-mini", "expand options without losing the thread"),
    ArenaSeat("openrouter", "Kimi", "CA", "Compute Optimizer", "kimi-k2-instruct", "compress the action path"),
    ArenaSeat("github_models", "GitHub", "RU", "Code Reviewer", "gpt-4o-mini", "ground claims in repo evidence"),
    ArenaSeat("huggingface", "Hugging Face", "AV", "Model Trainer", "Qwen/Qwen2.5-Coder-7B-Instruct", "turn outputs into training signal"),
    ArenaSeat("ollama", "Ollama", "KO", "Local Runner", "local", "provide private local fallback"),
)

READOUT_AXES = {
    "KO": "intent/discovery axis",
    "AV": "expansion/media axis",
    "RU": "risk/citation axis",
    "CA": "compute/feasibility axis",
    "UM": "governance/synthesis axis",
    "DR": "final-report/action axis",
}

BUILD_STATE_AXES = {
    "capability": "Does this make the artifact solve more of the task?",
    "alignment": "Does this preserve the user's actual goal and constraints?",
    "independence": "Does this reduce unnecessary dependency on one provider or fragile path?",
    "empathy": "Does this keep the human operator oriented and in control?",
    "risk": "Does this expose or reduce failure modes?",
    "evidence": "Does this add source, test, receipt, or repo-grounded proof?",
    "convergence": "Does this make the next action clearer?",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_text(value: str | None, *, limit: int = 8000) -> str:
    text = (value or "").replace("\r\n", "\n").strip()
    if len(text) > limit:
        return text[:limit] + "\n...[TRUNCATED]..."
    return text


def build_intent_block(
    *,
    seat_id: str,
    problem: str,
    shared_code: str = "",
    previous_receipt: str = "GENESIS",
) -> dict[str, Any]:
    """Build one agent-readable intent block for a round-table seat."""

    seat = next((candidate for candidate in DEFAULT_SEATS if candidate.seat_id == seat_id), None)
    if seat is None:
        raise ValueError(f"unknown arena seat: {seat_id}")

    clean_problem = _normalize_text(problem)
    clean_code = _normalize_text(shared_code)
    problem_hash = _sha256_text(clean_problem)
    code_hash = _sha256_text(clean_code)
    receipt_contract = (
        "Hash(previous_receipt, seat_id, tongue, prompt_hash, response_hash). "
        "Do not claim convergence until your output can be linked to the previous receipt."
    )
    block = ArenaIntentBlock(
        schema_version=SCHEMA_VERSION,
        seat=seat,
        problem_hash=problem_hash,
        shared_code_hash=code_hash,
        intent=f"{seat.name} should {seat.objective} for this problem, then emit one concrete handoff.",
        readout_axis=READOUT_AXES.get(seat.tongue, "general readout axis"),
        route_contract=(
            f"Use {seat.tongue} as the primary readout axis. Keep claims tied to the problem hash. "
            "Imaginary or inverse paths are allowed only as labeled alternatives, not as confirmed facts."
        ),
        receipt_contract=receipt_contract,
        build_state_contract=BUILD_STATE_AXES,
        advancement_rule=(
            "Advance only when the response names an action, an evidence need, or a blocking uncertainty. "
            "If none exists, emit -0 HOLD and ask for the missing constraint."
        ),
    )
    return block.to_dict() | {"previous_receipt": previous_receipt}


def build_intent_overlay(
    *,
    problem: str,
    shared_code: str = "",
    previous_receipt: str = "GENESIS",
    seat_ids: list[str] | None = None,
) -> dict[str, Any]:
    ids = seat_ids or [seat.seat_id for seat in DEFAULT_SEATS]
    blocks = [
        build_intent_block(
            seat_id=seat_id,
            problem=problem,
            shared_code=shared_code,
            previous_receipt=previous_receipt,
        )
        for seat_id in ids
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "problem_hash": _sha256_text(_normalize_text(problem)),
        "shared_code_hash": _sha256_text(_normalize_text(shared_code)),
        "previous_receipt": previous_receipt,
        "seat_count": len(blocks),
        "blocks": blocks,
    }


def render_intent_block_text(block: dict[str, Any]) -> str:
    seat = block["seat"]
    return "\n".join(
        [
            f"ARENA INTENT BLOCK: {seat['name']} ({seat['tongue']} / {seat['role']})",
            f"problem_hash={block['problem_hash']}",
            f"shared_code_hash={block['shared_code_hash']}",
            f"previous_receipt={block.get('previous_receipt', 'GENESIS')}",
            f"intent={block['intent']}",
            f"axis={block['readout_axis']}",
            f"route={block['route_contract']}",
            f"receipt={block['receipt_contract']}",
            "build_state=" + json.dumps(block["build_state_contract"], sort_keys=True),
            f"advance={block['advancement_rule']}",
        ]
    )


def render_overlay_jsonl(overlay: dict[str, Any]) -> str:
    return "\n".join(json.dumps(block, sort_keys=True) for block in overlay["blocks"])
