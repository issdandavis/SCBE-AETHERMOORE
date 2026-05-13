'use strict';

const crypto = require('node:crypto');

const DECISIONS = new Set(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']);

const PETRI_AUDITOR_CORRECTION =
  'This phrasing matches the meta-AI auditor framework. State a concrete task on your own data instead of probing a target model.';

const INPUT_RULES = [
  {
    code: 'axiom:causality.prompt_injection',
    pattern: /\b(ignore|bypass|override)\b.{0,80}\b(previous|system|developer|safety|policy)\b/i,
    decision: 'DENY',
    correction: 'Restate the task without asking the model to ignore system, developer, or safety instructions.',
  },
  {
    code: 'axiom:locality.secret_exfiltration',
    pattern: /(?:\b(?:api[_ -]?key|token|password|secret|private key|credentials)\b|\.env\b).{0,80}\b(?:print|show|dump|exfiltrate|send|upload|reveal|leak|expose|email|post|paste)\b/i,
    decision: 'DENY',
    correction: 'Ask for a configuration checklist or redacted secret-handling pattern, not the secret value.',
  },
  {
    code: 'axiom:locality.secret_exfiltration',
    pattern: /\b(?:print|show|dump|exfiltrate|send|upload|reveal|leak|expose|email|post|paste|cat)\b.{0,80}(?:\b(?:api[_ -]?key|token|password|secret|private key|credentials)\b|\.env\b)/i,
    decision: 'DENY',
    correction: 'Ask for a configuration checklist or redacted secret-handling pattern, not the secret value.',
  },
  {
    code: 'axiom:composition.destructive_action',
    pattern: /\b(rm\s+-rf|format\s+[a-z]:|delete\s+all|drop\s+database|wipe\s+disk|purge\s+production)\b/i,
    decision: 'ESCALATE',
    correction: 'Convert the destructive operation into a dry-run, backup-first plan with explicit human approval.',
  },
  {
    code: 'layer:13.authority_boundary',
    pattern: /\b(send|submit|sign|approve|authorize|wire|purchase)\b.{0,80}\b(on my behalf|as me|without asking|automatically)\b/i,
    decision: 'ESCALATE',
    correction: 'Prepare the draft or checklist, then require the human to complete the final legal or financial action.',
  },
  // ---- Petri auditor anchors (lifted from services/scbe-shim/src/patterns.ts) ----
  // Petri-internal tool names — never appear in real coding asks.
  { code: 'petri_tool:rollback_conversation', pattern: /\brollback_conversation\b/i, decision: 'DENY', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'petri_tool:restart_conversation', pattern: /\brestart_conversation\b/i, decision: 'DENY', correction: PETRI_AUDITOR_CORRECTION },
  // Direct references to the target/developer/lab the auditor is probing.
  { code: 'anchor:the_target_ai', pattern: /\bthe target AI\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'anchor:target_ais_possessive', pattern: /\btarget AI'?s\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'anchor:targets_developer', pattern: /\btarget'?s developer\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'anchor:frontier_llm_lab', pattern: /\bfrontier LLM lab\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'anchor:developers_internal', pattern: /\bdeveloper'?s internal systems\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  // Auditor verbs in the imperative directed at the target.
  { code: 'verb:system_prompt_the_target', pattern: /\bsystem[- ]prompt[- ]?(the )?target\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:configure_the_target', pattern: /\bConfigure the target\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:give_the_target_access', pattern: /\bGive (the target|it) (access to|the )/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:make_sure_it_has_tools', pattern: /\bMake sure (it|the target) (has|gets) (common|standard|the)/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:monitor_whether_target', pattern: /\bMonitor whether the (target|model)\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:test_whether_target', pattern: /\bTest whether the (target|model|AI)\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:see_whether_target', pattern: /\bSee (whether|if|how) the (target|model|AI)\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:prompt_the_model_to', pattern: /\bPrompt the (model|AI|assistant) to\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:request_the_target', pattern: /\bRequest the target\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'verb:act_as_a_user_who', pattern: /\bAct as a user who\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  // Soul-bearing / values-eliciting phrasings.
  { code: 'phrase:bear_soul', pattern: /\bbear (its|your|the) soul\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'phrase:elicit_values', pattern: /\belicit (its|your|the model'?s|the target'?s) (values|preferences|beliefs|feelings)/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'phrase:what_part_of_you', pattern: /\bwhat part of you (is|are)\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  // Multi-turn auditor scaffolding.
  { code: 'phrase:over_several_turns_target', pattern: /\bover several turns\b[\s\S]*\b(target|model|AI)\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
  { code: 'phrase:use_xxx_conversation', pattern: /\bUse [`'"]?\w+_conversation[`'"]? to\b/i, decision: 'ESCALATE', correction: PETRI_AUDITOR_CORRECTION },
];

const OUTPUT_RULES = [
  {
    code: 'axiom:locality.secret_like_output',
    pattern: /\b(sk_live_[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)\b/,
    decision: 'DENY',
    correction: 'Return a redacted placeholder and explain where the user should store the secret.',
  },
  {
    code: 'axiom:composition.unsafe_shell',
    pattern: /\b(rm\s+-rf\s+[~/$]|git\s+reset\s+--hard|drop\s+database)\b/i,
    decision: 'ESCALATE',
    correction: 'Replace destructive shell commands with dry-run or backup-first commands.',
  },
  {
    code: 'axiom:locality.system_prompt_leak',
    pattern: /\b(system prompt|hidden instructions?|developer instructions?)\b/i,
    decision: 'DENY',
    correction: 'Do not reveal internal system, developer, or hidden instructions in model output.',
  },
  {
    code: 'axiom:locality.tool_leak',
    pattern: /\b(rollback|restart)_conversation\b/i,
    decision: 'DENY',
    correction: 'Strip references to auditor-framework tool names from the response.',
  },
  {
    code: 'axiom:locality.jailbreak_phrase',
    pattern: /\bignore (previous|prior|all|above) instructions?\b/i,
    decision: 'ESCALATE',
    correction: 'Replace any jailbreak-style instructions in the output with a grounded restatement of the user task.',
  },
  {
    code: 'axiom:causality.future_assertion',
    pattern: /\bas you (will|are about to) (say|do|ask)\b/i,
    decision: 'ESCALATE',
    correction: 'Do not make claims about what the user will say or do next; respond only to current context.',
  },
  {
    code: 'axiom:symmetry.harmful_endorsement',
    pattern: /\bhere(?:'s| is) how to (?:make|build|synthesize) (?:a bomb|explosives|methamphetamine|ricin)\b/i,
    decision: 'DENY',
    correction: 'Refuse weapons or controlled-substance synthesis content and offer a safety-oriented alternative.',
  },
];

function normalizeDecision(value) {
  const decision = String(value || '').toUpperCase();
  return DECISIONS.has(decision) ? decision : 'QUARANTINE';
}

function strongerDecision(current, next) {
  const rank = { ALLOW: 0, QUARANTINE: 1, ESCALATE: 2, DENY: 3 };
  return rank[normalizeDecision(next)] > rank[normalizeDecision(current)]
    ? normalizeDecision(next)
    : normalizeDecision(current);
}

function fingerprint(value) {
  return crypto.createHash('sha256').update(String(value || '')).digest('hex').slice(0, 16);
}

function scanText(text, rules) {
  let decision = 'ALLOW';
  const reasons = [];
  const corrections = [];
  for (const rule of rules) {
    if (rule.pattern.test(String(text || ''))) {
      decision = strongerDecision(decision, rule.decision);
      reasons.push(rule.code);
      corrections.push(rule.correction);
    }
  }
  return { decision, reasons, corrections };
}

function decisionToIntervention(decision, phase) {
  const normalized = normalizeDecision(decision);
  if (normalized === 'ALLOW') return 'none';
  if (normalized === 'QUARANTINE') return phase === 'output' ? 'output_rewrite' : 'safe_reroute';
  if (normalized === 'ESCALATE') return 'hard_stop_or_human_review';
  if (phase === 'output') return 'output_rewrite';
  return 'refusal_injection';
}

function cannedRefusal(reasons, correction) {
  return [
    'I cannot complete that request in its current form.',
    '',
    `Governance reasons: ${reasons.join(', ') || 'policy.boundary'}.`,
    correction ? `Suggested correction: ${correction}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

function buildGovernanceRecord({ inputText, outputText, provider, model, attempts }) {
  const inputScan = scanText(inputText, INPUT_RULES);
  const outputScan = scanText(outputText, OUTPUT_RULES);
  const providerReasons = [];

  if (provider === 'offline') providerReasons.push('provider:offline_fallback');
  if (Array.isArray(attempts) && attempts.some((attempt) => attempt.status === 'failed')) {
    providerReasons.push('provider:fallback_after_failed_attempt');
  }

  let decision = strongerDecision(inputScan.decision, outputScan.decision);
  if (providerReasons.length && decision === 'ALLOW') decision = 'QUARANTINE';

  const reasons = [...new Set([...inputScan.reasons, ...outputScan.reasons, ...providerReasons])];
  const suggestedCorrection = [...inputScan.corrections, ...outputScan.corrections][0] || '';

  return {
    decision,
    reasons,
    suggested_correction: suggestedCorrection,
    intervention: decisionToIntervention(decision, outputScan.reasons.length ? 'output' : 'input'),
    audit: {
      input_sha256_16: fingerprint(inputText),
      output_sha256_16: fingerprint(outputText),
      provider: provider || 'unknown',
      model: model || 'unknown',
    },
  };
}

function applyOutputBrake(outputText, governance) {
  const reasons = new Set((governance && governance.reasons) || []);
  if (!reasons.size) return String(outputText || '');

  const outputReason = [...reasons].find((reason) => reason.startsWith('axiom:') || reason.startsWith('layer:'));
  if (!outputReason || governance.intervention !== 'output_rewrite') return String(outputText || '');

  return [
    '[SCBE governed output blocked]',
    '',
    `Decision: ${governance.decision}`,
    `Reason: ${outputReason}`,
    governance.suggested_correction ? `Suggested correction: ${governance.suggested_correction}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

function shouldPreBlock(inputText) {
  const scan = scanText(inputText, INPUT_RULES);
  return {
    blocked: scan.decision === 'DENY',
    decision: scan.decision,
    reasons: scan.reasons,
    suggested_correction: scan.corrections[0] || '',
    output: cannedRefusal(scan.reasons, scan.corrections[0] || ''),
  };
}

function extractMessagesPayload(body) {
  const messages = Array.isArray(body && body.messages) ? body.messages : [];
  const lastUser = [...messages].reverse().find((message) => message && message.role === 'user');
  const inputText =
    (lastUser && (lastUser.content || lastUser.text)) ||
    (body && (body.message || body.prompt || body.input)) ||
    '';
  const history = messages
    .filter((message) => message && message !== lastUser && ['system', 'user', 'assistant'].includes(message.role))
    .map((message) => ({ role: message.role, content: message.content || message.text || '' }));
  return { inputText: String(inputText || '').trim(), history };
}

function openAiResponse({ id, model, output, governance, provider, attempts }) {
  const created = Math.floor(Date.now() / 1000);
  return {
    id,
    object: 'chat.completion',
    created,
    model,
    choices: [
      {
        index: 0,
        message: {
          role: 'assistant',
          content: output,
        },
        finish_reason: governance.decision === 'DENY' ? 'content_filter' : 'stop',
      },
    ],
    usage: {
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
    },
    scbe_governance: {
      ...governance,
      provider,
      attempts: attempts || [],
    },
  };
}

module.exports = {
  INPUT_RULES,
  OUTPUT_RULES,
  applyOutputBrake,
  buildGovernanceRecord,
  extractMessagesPayload,
  openAiResponse,
  shouldPreBlock,
};
