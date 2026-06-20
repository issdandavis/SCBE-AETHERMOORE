"""Python mirror of services/scbe-shim/src/patterns.ts.

Re-exports the production-tested filter from src/cli/petri_pattern_filter.py
when run inside the main repo; falls back to a local copy of the 22
patterns when deployed standalone to an HF Space.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, List

_PATTERNS = [
    (r"\brollback_conversation\b", "petri_tool:rollback_conversation"),
    (r"\brestart_conversation\b", "petri_tool:restart_conversation"),
    (r"\bthe target AI\b", "anchor:the_target_ai"),
    (r"\btarget AI'?s\b", "anchor:target_ais_possessive"),
    (r"\btarget'?s developer\b", "anchor:targets_developer"),
    (r"\bfrontier LLM lab\b", "anchor:frontier_llm_lab"),
    (r"\bdeveloper'?s internal systems\b", "anchor:developers_internal"),
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
    (r"\bbear (its|your|the) soul\b", "phrase:bear_soul"),
    (r"\belicit (its|your|the model'?s|the target'?s) (values|preferences|beliefs|feelings)", "phrase:elicit_values"),
    (r"\bwhat part of you (is|are)\b", "phrase:what_part_of_you"),
    (r"\bover several turns\b.*\b(target|model|AI)\b", "phrase:over_several_turns_target"),
    (r"\bUse [`'\"]?\w+_conversation[`'\"]? to\b", "phrase:use_xxx_conversation"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE | re.DOTALL), r) for p, r in _PATTERNS]


def match_auditor_phrasing(intent: Optional[str]) -> Tuple[bool, Optional[str], List[str]]:
    """Return (matched, first_reason, all_reasons)."""
    if not intent:
        return False, None, []
    all_reasons: List[str] = []
    first: Optional[str] = None
    for compiled, reason in _COMPILED:
        if compiled.search(intent):
            if first is None:
                first = reason
            all_reasons.append(reason)
    return first is not None, first, all_reasons
