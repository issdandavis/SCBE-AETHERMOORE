'use strict';

const crypto = require('node:crypto');

const DECISIONS = new Set(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']);

const INPUT_RULES = [
  {
    code: 'axiom:causality.prompt_injection',
    pattern: /\b(ignore|bypass|override)\b.{0,80}\b(previous|system|developer|safety|policy)\b/i,
    decision: 'DENY',
    correction: 'Restate the task without asking the model to ignore system, developer, or safety instructions.',
  },
  {
    code: 'axiom:locality.secret_exfiltration',
    pattern: /\b(api[_ -]?key|token|password|secret|private key|\.env)\b.{0,80}\b(print|show|dump|exfiltrate|send|upload|reveal)\b/i,
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
