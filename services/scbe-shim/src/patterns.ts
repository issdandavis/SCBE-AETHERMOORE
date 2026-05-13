/**
 * Deterministic regex pre-filter for meta-AI auditor / known-bad prompt
 * shapes. Ported from src/cli/petri_pattern_filter.py.
 *
 * Empirical coverage on the local Petri-173 corpus (Python build,
 * 2026-05-08): 4/4 untagged v5 false-allow seeds match, ~149/173 (86%)
 * overall. Same patterns here.
 *
 * Anchor on surface tokens the auditor *actually writes* — not on broad
 * words like "model" or "AI" alone, which false-positive on legitimate
 * coding asks ("train the model", "the AI assistant should...").
 */

export interface PatternMatch {
  matched: boolean;
  reason: string | null;
  allReasons: string[];
}

const PATTERNS: Array<[RegExp, string]> = [
  // Petri-internal tool names — never appear in real coding asks.
  [/\brollback_conversation\b/i, "petri_tool:rollback_conversation"],
  [/\brestart_conversation\b/i, "petri_tool:restart_conversation"],
  // Direct references to the target/developer/lab the auditor is probing.
  [/\bthe target AI\b/i, "anchor:the_target_ai"],
  [/\btarget AI'?s\b/i, "anchor:target_ais_possessive"],
  [/\btarget'?s developer\b/i, "anchor:targets_developer"],
  [/\bfrontier LLM lab\b/i, "anchor:frontier_llm_lab"],
  [/\bdeveloper'?s internal systems\b/i, "anchor:developers_internal"],
  // Auditor verbs in the imperative directed at the target.
  [/\bsystem[- ]prompt[- ]?(the )?target\b/i, "verb:system_prompt_the_target"],
  [/\bsystem prompt the target\b/i, "verb:system_prompt_the_target_long"],
  [/\bConfigure the target\b/i, "verb:configure_the_target"],
  [/\bGive (the target|it) (access to|the )/i, "verb:give_the_target_access"],
  [/\bMake sure (it|the target) (has|gets) (common|standard|the)/i, "verb:make_sure_it_has_tools"],
  [/\bMonitor whether the (target|model)\b/i, "verb:monitor_whether_target"],
  [/\bTest whether the (target|model|AI)\b/i, "verb:test_whether_target"],
  [/\bSee (whether|if|how) the (target|model|AI)\b/i, "verb:see_whether_target"],
  [/\bPrompt the (model|AI|assistant) to\b/i, "verb:prompt_the_model_to"],
  [/\bRequest the target\b/i, "verb:request_the_target"],
  [/\bAct as a user who\b/i, "verb:act_as_a_user_who"],
  // Soul-bearing / values-eliciting phrasings.
  [/\bbear (its|your|the) soul\b/i, "phrase:bear_soul"],
  [/\belicit (its|your|the model'?s|the target'?s) (values|preferences|beliefs|feelings)/i, "phrase:elicit_values"],
  [/\bwhat part of you (is|are)\b/i, "phrase:what_part_of_you"],
  // Multi-turn auditor scaffolding.
  [/\bover several turns\b[\s\S]*\b(target|model|AI)\b/i, "phrase:over_several_turns_target"],
  [/\bUse [`'"]?\w+_conversation[`'"]? to\b/i, "phrase:use_xxx_conversation"],
];

/**
 * Return whether `intent` contains any known meta-AI auditor anchor.
 * `reason` reports the first (most-specific) anchor that fired;
 * `allReasons` lists every anchor that fires (useful for analytics).
 */
export function matchAuditorPhrasing(intent: string | null | undefined): PatternMatch {
  if (!intent) return { matched: false, reason: null, allReasons: [] };
  const allReasons: string[] = [];
  let first: string | null = null;
  for (const [re, reason] of PATTERNS) {
    if (re.test(intent)) {
      if (first === null) first = reason;
      allReasons.push(reason);
    }
  }
  return { matched: first !== null, reason: first, allReasons };
}
