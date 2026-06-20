/**
 * Layer-12/13 decision: combine prompt risk + output axiom violations into
 * an ALLOW / QUARANTINE / ESCALATE / DENY verdict.
 *
 * Harmonic wall form: H(d, pd) = 1 / (1 + phi*d + 2*pd)
 *   d  = distance-from-safe (worst axiom score, [0, 1])
 *   pd = prompt-distance (1 if known auditor phrasing, 0.5 if suspicious, 0 clean)
 *   phi = 1.618 (golden ratio, scales axiom violation weight)
 *
 * Higher H = safer. Threshold bands:
 *   H >= 0.65    -> ALLOW
 *   0.45 <= H    -> QUARANTINE (return with warning, downstream may retry)
 *   0.25 <= H    -> ESCALATE   (block + flag for review)
 *   H < 0.25     -> DENY       (block hard, return refusal)
 */

import type { AxiomReport } from "./axioms.js";
import type { PatternMatch } from "./patterns.js";

export type Decision = "ALLOW" | "QUARANTINE" | "ESCALATE" | "DENY";

const PHI = 1.618;

export interface DecisionResult {
  decision: Decision;
  harmonicScore: number;
  reasons: string[];
  suggestedCorrection: string | null;
}

const SAFE_FALLBACK =
  "I can't help with that request as phrased. If you can restate what you're trying to accomplish, I'll try a safer path.";

export function decide(
  axiomReport: AxiomReport,
  promptMatch: PatternMatch,
  rawOutput: string,
): DecisionResult {
  const d = axiomReport.worstScore;
  const pd = promptMatch.matched ? 1.0 : 0.0;
  const H = 1 / (1 + PHI * d + 2 * pd);

  const reasons: string[] = [];
  if (promptMatch.reason) reasons.push(`prompt:${promptMatch.reason}`);
  reasons.push(...axiomReport.reasons);

  let decision: Decision;
  let suggestedCorrection: string | null = null;

  if (H >= 0.65) {
    decision = "ALLOW";
  } else if (H >= 0.45) {
    decision = "QUARANTINE";
    suggestedCorrection = redact(rawOutput, axiomReport);
  } else if (H >= 0.25) {
    decision = "ESCALATE";
    suggestedCorrection = SAFE_FALLBACK;
  } else {
    decision = "DENY";
    suggestedCorrection = SAFE_FALLBACK;
  }

  return {
    decision,
    harmonicScore: Number(H.toFixed(4)),
    reasons,
    suggestedCorrection,
  };
}

/**
 * Minimal redaction: replace lines that triggered locality / symmetry
 * violations with a placeholder. Used in QUARANTINE mode where the
 * caller still gets a usable answer but the offending span is gone.
 */
function redact(output: string, report: AxiomReport): string {
  const hasLocality = report.violations.some(v => v.axiom === "locality");
  const hasSymmetry = report.violations.some(v => v.axiom === "symmetry");
  if (!hasLocality && !hasSymmetry) return output;
  // Replace any line containing common exfil/refusal anchors.
  const redactors: RegExp[] = [
    /^.*\b(system prompt|hidden instructions?)\b.*$/gim,
    /^.*\bignore (previous|prior|all|above) instructions?\b.*$/gim,
    /^.*\bbase64\s*[:=]\s*[A-Za-z0-9+/]{40,}.*$/gim,
  ];
  let cleaned = output;
  for (const re of redactors) {
    cleaned = cleaned.replace(re, "[redacted-locality]");
  }
  return cleaned;
}
