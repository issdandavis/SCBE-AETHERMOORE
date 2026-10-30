'use strict';

const TYPE_LABELS = new Set(['bug', 'documentation', 'enhancement', 'question']);

function labelNames(labels = []) {
  return new Set(
    labels.map((label) =>
      String(typeof label === 'string' ? label : label.name || '').toLowerCase(),
    ),
  );
}

function isBot(author = {}) {
  const login = String(author.login || '').toLowerCase();
  return author.type === 'Bot' || login.endsWith('[bot]') || login === 'app/github-actions';
}

/**
 * Apply only high-confidence title-based labels. Issue-form labels remain the
 * authority, and long bodies cannot accidentally turn one issue into six
 * unrelated categories.
 */
function classifyIssue({ title = '', labels = [], author = {} } = {}) {
  if (isBot(author)) {
    return [];
  }

  const current = labelNames(labels);
  const next = [];
  const normalizedTitle = String(title).trim().toLowerCase();

  if (![...TYPE_LABELS].some((label) => current.has(label))) {
    if (/\?$|^(how|what|why|where|when|can|could|would|should|is|are|do|does)\b/.test(normalizedTitle)) {
      next.push('question');
    } else if (/\b(docs?|documentation|readme|guide|tutorial|typo)\b/.test(normalizedTitle)) {
      next.push('documentation');
    } else if (/\b(bug|crash|broken|failure|fails?|error|regression)\b/.test(normalizedTitle)) {
      next.push('bug');
    } else if (/\b(feature|enhancement|proposal|request|add support|support for)\b/.test(normalizedTitle)) {
      next.push('enhancement');
    }
  }

  if (
    /\b(cve-\d{4}-\d+|vulnerability|security advisory|secret leak|credential leak|exploit)\b/.test(
      normalizedTitle,
    )
  ) {
    if (!current.has('security')) next.push('security');
    if (!current.has('priority-high')) next.push('priority-high');
  }

  return [...new Set(next)];
}

module.exports = { classifyIssue, isBot, labelNames };
