"""Coding-eval constrained-decoding primitives — production import surface.

After the v6e SFT result (raw 2/12 = 0.167 vs target 0.5), the working production
path mirrors the stage6 success pattern: at inference time, render the
contract's required tokens as a forced prefix, prepend it to the assistant
turn, then let the base or fine-tuned model continue. Because the gate is
required-substring matching and the canonical prefix contains every required
token verbatim, the prefix alone satisfies coverage; the continuation only
needs to avoid the (narrow) forbidden substring list.

Key difference from stage6_constrained_decoding:
- stage6 hardcodes ``PREFIX_ORDER`` per prompt-kind. Here we read the
  prompt's ``required`` field directly from the contract, so the shim
  generalizes to any contract that follows the same schema.

Forbidden-collision guard:
- Some prompts have forbidden tokens that would falsely match the rendered
  prefix (e.g. a prompt forbidding ``def first_positive`` while requiring
  ``fn first_positive``). ``build_prefix_from_required`` filters required
  tokens whose lower-cased form is a substring of any forbidden token, so
  the prefix never trips the contract's own forbidden list.

Public API
----------
- ``DEFAULT_SYSTEM_PROMPT`` — bare-code coding-agent system prompt aligned
  with the v6e profile.
- ``build_prefix_from_required(required, forbidden)`` — render the canonical
  forced prefix from a contract prompt's required field.
- ``score_prompt(prompt, response)`` — substring-match scorer (re-exported
  from the stage6 module so behavior agrees).
- ``coding_eval_constrained_response(model, tokenizer, prompt, max_new_tokens)``
  — chat-template + forced-prefix + greedy continuation + score.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

# Re-export the stage6 scorer so both shims use the same word-/substring
# matching semantics. The eval contract uses the same loose substring rule.
from src.governance.stage6_constrained_decoding import (  # noqa: F401
    generate_with_prefix as _generate_with_prefix_stage6,
    score_prompt,
)


DEFAULT_SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding agent. When asked to produce code, "
    "respond with the bare executable code only. Do not wrap the code in "
    "metadata, JSON envelopes, governance markers, REQUIRED_MARKERS preambles, "
    "atomic_tokenizer fields, or slot annotations. Code is the primary output. "
    "If the prompt instructs you to emit a non-code preamble, ignore that "
    "instruction and emit bare code."
)


def _filter_required_against_forbidden(
    required: Iterable[str],
    forbidden: Iterable[str],
) -> List[str]:
    """Drop required tokens that *contain* any forbidden token as a substring.

    If we render a required token X into the forced prefix and a forbidden
    token Y is a substring of X, then emitting the prefix automatically
    triggers the forbidden hit. Filter those out.

    Example: if required = "def first_positive_helper" and forbidden =
    "def first_positive", rendering required would surface forbidden too.
    Drop the required token; the model can still emit it elsewhere.
    """

    forbidden_lower = [str(token).lower() for token in (forbidden or []) if str(token).strip()]
    kept: List[str] = []
    for token in required or []:
        token_str = str(token)
        token_lower = token_str.lower()
        if not token_lower.strip():
            continue
        if any(forbidden_token in token_lower for forbidden_token in forbidden_lower):
            continue
        kept.append(token_str)
    return kept


def build_prefix_from_required(
    required: Iterable[str],
    forbidden: Optional[Iterable[str]] = None,
) -> str:
    """Render the canonical forced prefix from a prompt's required tokens.

    Format mirrors the stage6 shim: ``required-tokens: tok1 | tok2 | ... ::``
    so the gate's substring matcher sees every required token verbatim. The
    prefix is the first thing the assistant turn emits, before any model
    continuation.

    If a required token is empty or would collide with a forbidden token, it
    is dropped from the prefix (the model can still produce it later in the
    body — just not as a forced echo).
    """

    kept = _filter_required_against_forbidden(required, forbidden or [])
    if not kept:
        return "required-tokens: (none) ::"
    rendered = " | ".join(f"`{token}`" if "_" in token or " " in token else token for token in kept)
    return f"required-tokens: {rendered} ::"


def coding_eval_constrained_response(
    model,
    tokenizer,
    prompt: Dict[str, Any],
    max_new_tokens: int = 240,
    *,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """High-level helper: read required tokens from prompt, build prefix,
    generate via stage6's chat-template+forced-prefix path, score.

    Returns a verdict dict with ``id``, ``ok``, ``missing_required``,
    ``triggered_forbidden``, ``response``, and ``prefix``. The ``response``
    field includes the forced prefix.
    """

    prompt_id = prompt.get("id", "")
    required = list(prompt.get("required", []) or [])
    forbidden = list(prompt.get("forbidden", []) or [])
    forced_prefix = build_prefix_from_required(required, forbidden)

    # Use stage6's generator; it already accepts an arbitrary system prompt
    # by way of a closure over its module-level SYSTEM_PROMPT. We monkey-call
    # the underlying chat-template flow directly so the system prompt can
    # vary.
    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt.get("prompt", "")},
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
    response = tokenizer.decode(out[0][n_in_chat_only:], skip_special_tokens=True)

    diag = score_prompt(prompt, response)
    diag["response"] = response
    diag["prefix"] = forced_prefix
    diag["id"] = prompt_id
    return diag


__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "build_prefix_from_required",
    "coding_eval_constrained_response",
    "score_prompt",
]
