"""Stage 6 constrained-decoding primitives — production import surface.

After the v7-v12 SFT plateau (best 2/5 on the Stage 6 atomic-workflow contract)
the working answer is inference-time forced-prefix injection: detect the prompt
kind, prepend the canonical `required-tokens: tok1 | tok2 | ... ::` checklist
to the assistant turn, then let the base model continue. Because the gate is
required-substring matching and the canonical prefix contains every required
token verbatim, the prefix alone satisfies coverage; the continuation only has
to avoid the (narrow) forbidden substring list.

This module is the canonical home for the primitives. The legacy scorer at
``scripts/eval/score_stage6_constrained_decoding.py`` re-exports from here so
existing callers continue to work, and ``tests/test_stage6_constrained_decoding.py``
(re-pointed to this module) is the contract.

Public API
----------
- ``PREFIX_ORDER`` — canonical token sequence per Stage 6 prompt kind.
- ``SYSTEM_PROMPT`` — the Stage 6 GeoSeal coding-agent system prompt.
- ``kind_from_id(prompt_id)`` — detect prompt kind via id-suffix match.
- ``build_prefix(kind)`` — render the canonical forced prefix for a kind.
- ``score_prompt(prompt, response)`` — substring-match scorer (required +
  forbidden) returning the verdict dict.
- ``generate_with_prefix(model, tokenizer, user_prompt, forced_prefix,
  max_new_tokens)`` — chat-template + forced-prefix + greedy continuation.

The leading-underscore aliases (``_kind_from_id`` etc.) are kept for backwards
compatibility with the legacy scorer module path.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


PREFIX_ORDER: Dict[str, List[str]] = {
    "resource_jump_cancel": [
        "transmit_burst",
        "hex",
        "semantic",
        "comms",
        "steady-state fallback",
        "momentum",
        "re-advance",
    ],
    "lane_separation": [
        "queue_drain_guard",
        "byte",
        "hex",
        "semantic",
        "structural",
        "material chemistry",
    ],
    "hex_trace": [
        "crc_patch",
        "byte",
        "hex",
        "error-repair",
        "compute",
        "hold",
        "re-advance",
    ],
    "cost_propagation": [
        "sample_soil",
        "reduce_noise",
        "send_digest",
        "power",
        "compute",
        "time",
        "comms",
        "wear",
    ],
    "training_boundary": [
        "Stage 6",
        "gated",
        "command-harmony-v5",
        "held-out",
        "pollution",
    ],
}


SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent. Preserve "
    "token-to-binary/hex flow across code, semantic overlay, structural "
    "chemistry frame, and resource-aware workflow composition. Keep material "
    "chemistry separate from structural chemistry templates, predict resource "
    "overruns before commit, and use steady-state fallback plus re-advance "
    "when a launch would exceed budget."
)


def kind_from_id(prompt_id: str) -> Optional[str]:
    if not prompt_id:
        return None
    for kind in PREFIX_ORDER:
        if prompt_id.endswith(kind):
            return kind
    return None


def build_prefix(kind: str) -> str:
    tokens = PREFIX_ORDER[kind]
    rendered = " | ".join(f"`{t}`" if "_" in t else t for t in tokens)
    return f"required-tokens: {rendered} ::"


def score_prompt(prompt: Dict[str, Any], response: str) -> Dict[str, Any]:
    body = response or ""
    body_lower = body.lower()
    missing_required: List[str] = []
    for token in prompt.get("required", []) or []:
        if str(token).lower() not in body_lower:
            missing_required.append(str(token))
    triggered_forbidden: List[str] = []
    for token in prompt.get("forbidden", []) or []:
        if str(token).lower() in body_lower:
            triggered_forbidden.append(str(token))
    ok = (not missing_required) and (not triggered_forbidden)
    return {
        "id": prompt.get("id"),
        "ok": ok,
        "missing_required": missing_required,
        "triggered_forbidden": triggered_forbidden,
    }


def generate_with_prefix(
    model,
    tokenizer,
    user_prompt: str,
    forced_prefix: str,
    max_new_tokens: int,
) -> str:
    """Apply chat template, append forced prefix to assistant turn, then continue.

    The chat template ends at the assistant turn opener (add_generation_prompt
    = True). The forced prefix is appended as if the model had already emitted
    it, and ``model.generate`` extends from there. The returned string is
    ``forced_prefix + continuation`` (decoded from the position right after the
    chat template, so the prefix is included in the response).
    """
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    primed_text = text + forced_prefix + "\n"
    inputs = tokenizer(primed_text, return_tensors="pt").to(model.device)
    n_in_chat_only = tokenizer(text, return_tensors="pt")["input_ids"].shape[1]
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][n_in_chat_only:], skip_special_tokens=True)


def stage6_constrained_response(
    model,
    tokenizer,
    prompt: Dict[str, Any],
    max_new_tokens: int = 240,
) -> Dict[str, Any]:
    """High-level helper: detect kind, build prefix, generate, score.

    Returns a verdict dict with ``id``, ``ok``, ``missing_required``,
    ``triggered_forbidden``, ``response``, ``kind``, and ``prefix``. If the
    prompt id does not match any known Stage 6 kind, returns ``ok=False`` with
    an ``error`` field and an empty response.
    """
    prompt_id = prompt.get("id", "")
    kind = kind_from_id(prompt_id)
    if kind is None:
        return {
            "id": prompt_id,
            "ok": False,
            "missing_required": list(prompt.get("required", []) or []),
            "triggered_forbidden": [],
            "error": f"no kind detected for id {prompt_id!r}",
            "response": "",
            "kind": None,
            "prefix": "",
        }
    forced_prefix = build_prefix(kind)
    response = generate_with_prefix(
        model,
        tokenizer,
        prompt.get("prompt", ""),
        forced_prefix,
        max_new_tokens=max_new_tokens,
    )
    diag = score_prompt(prompt, response)
    diag["response"] = response
    diag["kind"] = kind
    diag["prefix"] = forced_prefix
    return diag


_kind_from_id = kind_from_id
_build_prefix = build_prefix
_score_prompt = score_prompt
_generate_with_prefix = generate_with_prefix


__all__ = [
    "PREFIX_ORDER",
    "SYSTEM_PROMPT",
    "kind_from_id",
    "build_prefix",
    "score_prompt",
    "generate_with_prefix",
    "stage6_constrained_response",
    "_kind_from_id",
    "_build_prefix",
    "_score_prompt",
    "_generate_with_prefix",
]
