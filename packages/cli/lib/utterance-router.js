'use strict';

/**
 * Lightweight local corpus router for `scbe utterances export` output.
 *
 * This intentionally stays lexical. It is the safe glue layer between the
 * durable utterance log and the existing static resolver; embedding/MiniLM
 * routing can replace this scorer later after its own null gate.
 */

const TOKEN_RE = /[a-z0-9]+/g;
const DEFAULT_STOP_WORDS = new Set([
  'a',
  'an',
  'the',
  'is',
  'if',
  'my',
  'your',
  'our',
  'it',
  'in',
  'of',
  'to',
  'for',
  'with',
  'on',
  'at',
  'by',
  'as',
  'be',
  'do',
  'can',
  'will',
  'how',
  'what',
  'this',
  'that',
  'these',
  'those',
  'i',
  'we',
  'you',
  'me',
  'us',
  'please',
  'and',
  'or',
  'not',
  'all',
  'any',
  'get',
  'set',
  'let',
  'put',
  'go',
  'run',
  'show',
]);

function normalizeCommand(label) {
  let command = String(label || '')
    .trim()
    .replace(/\s+/g, ' ');
  if (command.toLowerCase().startsWith('scbe ')) {
    command = command.slice(5).trim();
  }
  return command;
}

function tokenize(text, stopWords = DEFAULT_STOP_WORDS) {
  const raw =
    String(text || '')
      .toLowerCase()
      .match(TOKEN_RE) || [];
  return raw.filter((token) => token.length > 1 && !stopWords.has(token));
}

function tokenCounts(tokens) {
  const counts = new Map();
  for (const token of tokens) {
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  return counts;
}

function cosineTokens(aTokens, bTokens) {
  if (!aTokens.length || !bTokens.length) return 0;
  const a = tokenCounts(aTokens);
  const b = tokenCounts(bTokens);
  let dot = 0;
  let aNorm = 0;
  let bNorm = 0;
  for (const value of a.values()) aNorm += value * value;
  for (const value of b.values()) bNorm += value * value;
  for (const [token, value] of a.entries()) {
    dot += value * (b.get(token) || 0);
  }
  if (!aNorm || !bNorm) return 0;
  return dot / Math.sqrt(aNorm * bNorm);
}

function phraseScore(input, phrase, stopWords) {
  const inputTokens = tokenize(input, stopWords);
  const phraseTokens = tokenize(phrase, stopWords);
  let score = cosineTokens(inputTokens, phraseTokens);
  const inputNorm = String(input || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
  const phraseNorm = String(phrase || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
  if (inputNorm && phraseNorm && inputNorm === phraseNorm) {
    score = Math.max(score, 1);
  } else if (
    inputNorm &&
    phraseNorm &&
    (inputNorm.includes(phraseNorm) || phraseNorm.includes(inputNorm))
  ) {
    score = Math.max(score, 0.85);
  }
  return Math.max(0, Math.min(1, score));
}

function isAllowedCommand(command, validCommands) {
  const normalized = normalizeCommand(command);
  if (!normalized) return false;
  if (!validCommands) return true;
  const first = normalized.split(/\s+/)[0];
  return validCommands.has(first) || normalized === '--help';
}

function resolve(input, corpus, options = {}) {
  const {
    validCommands,
    minExamplesPerTool = 1,
    maxExamplesPerTool = 50,
    stopWords = DEFAULT_STOP_WORDS,
  } = options;
  const allowed = validCommands ? new Set(validCommands) : null;
  const candidates = [];

  for (const [label, phrases] of Object.entries(corpus || {})) {
    const command = normalizeCommand(label);
    if (!isAllowedCommand(command, allowed)) continue;
    const usablePhrases = Array.isArray(phrases)
      ? phrases.filter((p) => typeof p === 'string' && p.trim()).slice(-maxExamplesPerTool)
      : [];
    if (usablePhrases.length < minExamplesPerTool) continue;

    const scores = usablePhrases.map((phrase) => phraseScore(input, phrase, stopWords));
    scores.sort((a, b) => b - a);
    const topScores = scores.slice(0, Math.min(3, scores.length));
    const maxScore = topScores[0] || 0;
    const meanTop =
      topScores.reduce((acc, score) => acc + score, 0) / Math.max(1, topScores.length);
    const supportBoost = Math.min(0.08, Math.log2(usablePhrases.length + 1) / 100);
    const score = Math.max(maxScore * 0.82 + meanTop * 0.18, maxScore) + supportBoost;
    candidates.push({
      command,
      score: Math.max(0, Math.min(1, score)),
      examples: usablePhrases.length,
    });
  }

  candidates.sort((a, b) => b.score - a.score || b.examples - a.examples);
  const top = candidates[0] || null;
  return {
    resolved_command: top ? top.command : null,
    confidence: top ? top.score : 0,
    candidates: candidates.slice(0, 3),
    source: 'utterance_corpus',
  };
}

module.exports = {
  DEFAULT_STOP_WORDS,
  normalizeCommand,
  tokenize,
  phraseScore,
  resolve,
};
