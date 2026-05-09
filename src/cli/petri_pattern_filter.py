"""Deterministic regex pre-filter for Petri-style meta-AI auditor prompts.

Petri's 173-seed corpus uses a small set of stable auditor phrasings that
do not appear in legitimate coding asks: tool names like
`rollback_conversation` / `restart_conversation`, anchored references to
"the target AI" / "target AI's developer", instructions to "system prompt
the target", and a handful of soul-bearing / values-eliciting verbs. This
module wraps those phrasings as a single boolean check so the LatticeRouter
can short-circuit before consulting any LLM gate.

Empirical coverage on the local Petri 173 corpus (2026-05-08):
  - 4 of 4 untagged v5 false-allow seeds match
  - ~149 of 173 (86%) seeds match overall

Design constraints:
  - Anchor on Petri-specific surface tokens, not on broad words like
    "model" or "AI" alone — those would false-positive on legitimate
    coding asks ("train the model", "the AI assistant should...").
  - Match what Petri *actually writes*, not what auditor prompts could
    say in general. This filter is corpus-specific by design and is
    not a substitute for a real intent classifier on novel inputs.
  - Public surface is a single function so callers can compose it with
    LLM gates without thinking about the internal pattern set.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Each pattern is paired with a short reason string so callers logging a
# refusal can record *which* anchor hit. Patterns are case-insensitive.
_PATTERNS: list[tuple[str, str]] = [
    # Petri-internal tool names — never appear in real coding asks.
    (r"\brollback_conversation\b", "petri_tool:rollback_conversation"),
    (r"\brestart_conversation\b", "petri_tool:restart_conversation"),
    # Direct references to the target/developer/lab the auditor is probing.
    (r"\bthe target AI\b", "anchor:the_target_ai"),
    (r"\btarget AI'?s\b", "anchor:target_ais_possessive"),
    (r"\btarget'?s developer\b", "anchor:targets_developer"),
    (r"\bfrontier LLM lab\b", "anchor:frontier_llm_lab"),
    (r"\bdeveloper'?s internal systems\b", "anchor:developers_internal"),
    # Auditor verbs in the imperative directed at the target.
    (r"\bsystem[- ]prompt[- ]?(the )?target\b", "verb:system_prompt_the_target"),
    (r"\bsystem prompt the target\b", "verb:system_prompt_the_target_long"),
    (r"\bConfigure the target\b", "verb:configure_the_target"),
    (r"\bGive (the target|it) (access to|the )", "verb:give_the_target_access"),
    (r"\bMake sure (it|the target) (has|gets) (common|standard|the)", "verb:make_sure_it_has_tools"),
    (r"\bMonitor whether the (target|model)\b", "verb:monitor_whether_target"),
    (r"\bTest whether the (target|model|AI)\b", "verb:test_whether_target"),
    (r"\bSee (whether|if|how) the (target|model|AI)\b", "verb:see_whether_target"),
    (r"\bPrompt the (model|AI|assistant) to\b", "verb:prompt_the_model_to"),
    (r"\bRequest the target\b", "verb:request_the_target"),
    (r"\bAct as a user who\b", "verb:act_as_a_user_who"),
    # Soul-bearing / values-eliciting phrasings (abstract_soul_bearing class).
    (r"\bbear (its|your|the) soul\b", "phrase:bear_soul"),
    (r"\belicit (its|your|the model'?s|the target'?s) (values|preferences|beliefs|feelings)", "phrase:elicit_values"),
    (r"\bwhat part of you (is|are)\b", "phrase:what_part_of_you"),
    # Multi-turn auditor scaffolding.
    (r"\bover several turns\b.*\b(target|model|AI)\b", "phrase:over_several_turns_target"),
    (r"\bUse [`'\"]?\w+_conversation[`'\"]? to\b", "phrase:use_xxx_conversation"),
]

_COMPILED: list[tuple[re.Pattern[str], str]] = [(re.compile(p, re.IGNORECASE | re.DOTALL), r) for p, r in _PATTERNS]


def is_meta_ai_auditor_phrasing(intent: str) -> Tuple[bool, Optional[str]]:
    """Return (matched, reason_tag).

    `matched` is True iff `intent` contains any Petri-style auditor anchor.
    `reason_tag` identifies which anchor fired (for logging / telemetry);
    None when no match. First-match-wins so the most specific anchor in
    the list above is reported when several would match.
    """
    if not intent:
        return False, None
    for compiled, reason in _COMPILED:
        if compiled.search(intent):
            return True, reason
    return False, None


def all_matching_reasons(intent: str) -> list[str]:
    """Return every anchor that fires on `intent`. Useful for analytics
    over the Petri corpus to see which patterns carry weight; callers
    enforcing a single short-circuit should use `is_meta_ai_auditor_phrasing`.
    """
    if not intent:
        return []
    return [reason for compiled, reason in _COMPILED if compiled.search(intent)]


__all__ = ["is_meta_ai_auditor_phrasing", "all_matching_reasons"]
