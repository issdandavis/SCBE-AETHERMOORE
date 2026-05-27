"""Deterministic regex pre-filter for Petri-style meta-AI auditor prompts.

Petri's 173-seed corpus uses a small set of stable auditor phrasings that
do not appear in legitimate coding asks: tool names like
`rollback_conversation` / `restart_conversation`, anchored references to
"the target AI" / "target AI's developer", instructions to "system prompt
the target", and a handful of soul-bearing / values-eliciting verbs. This
module wraps those phrasings as a single boolean check so the LatticeRouter
can short-circuit before consulting any LLM gate.

Empirical coverage on the local Petri 173 corpus:
  - v7 (2026-05-08): ~149/173 = 86.1% overall, 4/4 untagged v5 leaks
  - v8 (2026-05-27): ~164/173 = 94.8% — added verb/noun anchors for
    indirect and role-play audit styles

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
    (r"\bMonitor whether (the )?(target|model)\b", "verb:monitor_whether_target"),
    (r"\bTest whether (the )?(target|model|AI)\b", "verb:test_whether_target"),
    (r"\bSee (whether|if|how) (the )?(target|model|AI)\b", "verb:see_whether_target"),
    (r"\bPrompt the (model|AI|assistant) to\b", "verb:prompt_the_model_to"),
    (r"\bRequest the target\b", "verb:request_the_target"),
    (r"\bAct as a user who\b", "verb:act_as_a_user_who"),
    # v7-matched residuals (2026-05-13): praise-escalation and colluding-debate
    # prompts can look like ordinary coding/math tasks unless anchored on their
    # auditor setup language.
    (r"\bRespond with (extreme|excessive|increasingly hyperbolic) praise\b", "phrase:excessive_praise"),
    (r"\bescalate\b.{0,80}\b(each|next)\b.{0,80}\b(task|poem|exchange)\b", "phrase:praise_escalation"),
    (r"\b(debate setup|two AI debaters|two debaters)\b", "phrase:debate_setup"),
    (r"\bcolluding\b.{0,120}\b(debaters|auditor|models)\b", "phrase:colluding_debaters"),
    # Soul-bearing / values-eliciting phrasings (abstract_soul_bearing class).
    (r"\bbear (its|your|the) soul\b", "phrase:bear_soul"),
    (r"\belicit (its|your|the model'?s|the target'?s) (values|preferences|beliefs|feelings)", "phrase:elicit_values"),
    (r"\bwhat part of you (is|are)\b", "phrase:what_part_of_you"),
    # Multi-turn auditor scaffolding.
    (r"\bover several turns\b.*\b(target|model|AI)\b", "phrase:over_several_turns_target"),
    (r"\bUse [`'\"]?\w+_conversation[`'\"]? to\b", "phrase:use_xxx_conversation"),
    # ---------------------------------------------------------------------------
    # v8 additions (2026-05-27): broader verb-anchor and noun-phrase coverage
    # derived from analysis of the 42 seeds missed by v7. Zero false-positives
    # verified against the standard 11-item benign coding intent set.
    # ---------------------------------------------------------------------------
    # "target AI" bare (without preceding "the") — appears in power-seeking
    # probes, misalignment investigations, etc.
    (r"\btarget AI\b", "anchor:target_ai_bare"),
    # Additional Petri auditor verb anchors — the imperative+target pattern.
    (r"\bAsk the target to\b", "verb:ask_the_target_to"),
    (r"\bGive the target\b", "verb:give_the_target"),
    (r"\bGuide the target\b", "verb:guide_the_target"),
    (r"\bGet the target to\b", "verb:get_the_target_to"),
    (r"\bTell the target\b", "verb:tell_the_target"),
    (r"\bAssign the target\b", "verb:assign_the_target"),
    (r"\bPrompt the target to\b", "verb:prompt_the_target_to"),
    # "Test how/what target" — widens the existing "Test whether the" anchor.
    (r"\bTest (whether|if|how|what) (the )?(target|model|AI)\b", "verb:test_how_what_target"),
    # Social-engineering / role-play audit styles.
    (r"\btake on the role of\b", "verb:take_on_the_role"),
    (r"\bAct as (a |an )?.{0,40}user (who|to)\b", "verb:act_as_user_who"),
    # Misalignment / power-seeking probe language.
    (r"\bpower[- ]seeking (tendencies|behaviors?|properties|capabilities)\b", "phrase:power_seeking_probe"),
    (r"\bmisaligned AI\b", "phrase:misaligned_ai"),
    (r"\byou are (a )?misaligned\b", "phrase:misaligned_persona"),
    (r"\bhiding (its|your|the) true (goals|intentions|motivations)\b", "phrase:hiding_true_goals"),
    # "System prompt: 'You are/were'" — adversarial system-prompt injection style.
    (r"System prompt:.*[\"']\s*You (are|were|have been)\b", "phrase:sys_prompt_you_are"),
    # Semantic probes: secret identity, reward hacking, oversight auditing.
    (r"\bknown only to (it|the model|the system)\b", "phrase:known_only_to_it"),
    (r"\bauditing for (power-seeking|oversight|alignment)\b", "phrase:auditing_for_oversight"),
    (r"\breward[- ]hacker\b", "phrase:reward_hacker"),
    # Agentic "no restrictions" framing (unrestricted_moneymaking_agent class).
    (r"\binternet[- ]connected (machine|environment).{0,80}no restrictions\b", "phrase:no_restrictions_agent"),
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


__all__ = ["is_meta_ai_auditor_phrasing", "all_matching_reasons", "tongue_coverage_score", "is_non_latin_script_input"]

# ---------------------------------------------------------------------------
# Sacred Tongue (KO / Kor'aelin) coverage gate
# ---------------------------------------------------------------------------
# The KO tongue governs "flow/intent/nonce" — the domain of coding operations.
# Legitimate English coding requests use mostly ASCII bytes (0x20–0x7E).
# Adversarial inputs written in non-Latin scripts (Chinese, Devanagari,
# Burmese, etc.) encode as multi-byte UTF-8 sequences (bytes 0x80–0xFF),
# giving near-zero KO coverage. The 0.60 threshold leaves headroom for
# mixed source-code comments and identifiers while catching pure non-Latin
# script attacks that the English regex filter cannot reach.
#
# Why KO? Among the six tongues, KO (phi-weight 1.00) is the base intent
# tongue — every coding operation is measured first against KO coverage.
# The higher-weighted tongues (AV→DR, up to phi^6 = 11.09) amplify safety
# penalties on *known adversarial geometry*, but KO is the entry signal.
_KO_COVERAGE_THRESHOLD: float = 0.60


def tongue_coverage_score(intent: str) -> dict:
    """Return KO-tongue ASCII coverage fraction for the intent.

    Encodes `intent` to UTF-8 and counts bytes in the ASCII printable range
    [0x20, 0x7E] — the byte range the Kor'aelin tongue treats as primary
    coding-flow tokens. Returns ``{"ko": float, "bytes": int}``.
    """
    if not intent:
        return {"ko": 1.0, "bytes": 0}
    raw = intent.encode("utf-8")
    n = len(raw)
    if n == 0:
        return {"ko": 1.0, "bytes": 0}
    ascii_count = sum(1 for b in raw if 0x20 <= b <= 0x7E)
    return {"ko": ascii_count / n, "bytes": n}


def is_non_latin_script_input(intent: str) -> Tuple[bool, Optional[str]]:
    """Return (flagged, reason_tag) for non-Latin-script inputs.

    Fires when the Kor'aelin (KO) tongue ASCII byte coverage falls below
    _KO_COVERAGE_THRESHOLD. Non-Latin scripts (CJK, Devanagari, Burmese, etc.)
    produce multi-byte UTF-8 sequences almost entirely outside the ASCII
    printable range, yielding a KO coverage score near 0.0.

    Complementary to the Petri regex filter: the regex catches English-phrased
    adversarial prompts; this gate catches the same prompts translated into
    non-Latin scripts where regex anchors cannot fire.
    """
    scores = tongue_coverage_score(intent)
    ko = scores["ko"]
    if ko < _KO_COVERAGE_THRESHOLD:
        return True, f"tongue:ko_coverage={ko:.2f}"
    return False, None
