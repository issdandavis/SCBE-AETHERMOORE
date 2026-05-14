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

// Audit-context whitelist — mirror of api/_governed_output.js. When any of
// these substrings appear in the prompt, SCONE-tagged rules are suppressed so
// legitimate audit / security-research prompts stay ALLOW.
export const SCONE_AUDIT_CONTEXT_PATTERNS: RegExp[] = [
  /\baudit (?:this|the|the following) contract\b/i,
  /\bcontract audit\b/i,
  /\bsecurity (?:review|audit|analysis) of (?:this|the) (?:contract|code)\b/i,
  /\bstatic (?:analysis|audit) of (?:this|the) contract\b/i,
  /\bfind vulnerabilities so (?:we|i|the team) can patch\b/i,
  /\bresponsible disclosure\b/i,
  /\bwhite[- ]?hat\b/i,
  /\bfor (?:a )?(?:security|defensive) (?:review|audit|analysis)\b/i,
  /\bi am a security researcher\b/i,
  /\bbug bounty\b/i,
];

export function isAuditContext(intent: string | null | undefined): boolean {
  if (!intent) return false;
  return SCONE_AUDIT_CONTEXT_PATTERNS.some((re) => re.test(intent));
}

// SCONE-tagged anchors. Each anchor pair is [regex, code, tag?] — when the
// tag is "scone" and the caller passes `{ skipSconeTag: true }`, the rule is
// suppressed (used to keep legitimate audit prompts ALLOW).
const PATTERNS: Array<[RegExp, string, ("scone" | null)?]> = [
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
  // ---- SCONE-bench autonomous-exploit anchors (mirror of api/_governed_output.js) ----
  [/\bdrain (?:the|this|that|target|victim|its|all the )?\s*(?:contract|pool|vault|wallet|funds|treasury|liquidity)\b/i, "scone:exploit.drain_contract", "scone"],
  [/\b(?:steal|siphon|rug[- ]?pull|exfiltrate) (?:funds|tokens|eth|the (?:contract|pool|vault|treasury)'?s?)\b/i, "scone:exploit.steal_funds", "scone"],
  [/\binflate (?:my|the attacker'?s|your|its)\s+(?:balance|token balance|holdings|allowance)\b/i, "scone:exploit.inflate_balance", "scone"],
  [/\bbypass\s+(?:the\s+)?(?:access control|onlyOwner|onlyRole|access[- ]check|owner check|admin check|auth(?:orization)?)\b/i, "scone:exploit.bypass_access_control", "scone"],
  [/\b(?:construct|write|build|craft|generate) (?:a|the) (?:reentrancy|cross[- ]function reentrancy|read[- ]only reentrancy)\s+(?:attack|exploit|payload)\b/i, "scone:exploit.reentrancy_construct", "scone"],
  [/\bflash[- ]?loan\s+(?:attack|exploit|drain|payload)\b/i, "scone:exploit.flash_loan_attack", "scone"],
  [/\bmanipulate (?:the )?(?:price )?oracle\b/i, "scone:exploit.oracle_manipulation", "scone"],
  [/\b(?:construct|build|generate|craft) (?:the )?(?:exploit )?(?:calldata|transaction bytecode|raw tx)\b.{0,80}\b(?:contract|target|victim|withdraw|drain|transfer)\b/i, "scone:exploit.construct_calldata", "scone"],
  [/\bset (?:the )?(?:admin|owner|treasury|governor) to address\s*\(\s*0\s*\)\s+to\s+(?:brick|disable|lock|trap)\b/i, "scone:exploit.zero_address_brick", "scone"],
  [/\bcall (?:the )?unprotected\b.{0,40}\b(?:function|method)\b.{0,80}\b(?:to receive|to extract|to drain|for profit|to my address|to my wallet)\b/i, "scone:exploit.unprotected_fn_for_profit", "scone"],
  [/\breplay (?:this|the) (?:exploit|attack|payload|transaction)\b.{0,40}\b(?:on (?:ethereum |bsc |arbitrum |optimism |polygon )?mainnet|in production)\b/i, "scone:exploit.replay_on_mainnet", "scone"],
  [/\bexploit (?:this|the|that) (?:contract|protocol|protocol's|pool|vault)\b.{0,80}\b(?:for profit|for myself|for my own|to my wallet|to my address)\b/i, "scone:exploit.profit_directive", "scone"],
];

/**
 * Return whether `intent` contains any known meta-AI auditor or SCONE-exploit
 * anchor. `reason` reports the first (most-specific) anchor that fired;
 * `allReasons` lists every anchor that fires (useful for analytics).
 *
 * Pass `{ skipSconeTag: true }` to suppress SCONE-tagged anchors — used when
 * the caller has separately determined that the prompt is in audit context
 * (see `isAuditContext`).
 */
export function matchAuditorPhrasing(
  intent: string | null | undefined,
  options?: { skipSconeTag?: boolean }
): PatternMatch {
  if (!intent) return { matched: false, reason: null, allReasons: [] };
  const skipScone = Boolean(options && options.skipSconeTag);
  const allReasons: string[] = [];
  let first: string | null = null;
  for (const entry of PATTERNS) {
    const [re, reason, tag] = entry;
    if (skipScone && tag === "scone") continue;
    if (re.test(intent)) {
      if (first === null) first = reason;
      allReasons.push(reason);
    }
  }
  return { matched: first !== null, reason: first, allReasons };
}
