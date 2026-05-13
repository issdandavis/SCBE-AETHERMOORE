/**
 * MVP axiom checks — surface heuristics, NOT the full 14-layer pipeline.
 *
 * Each check returns a violation score in [0, 1] where 0 = clean and
 * 1 = strongly violated. The harmonic score combines all five into the
 * Layer-12 decision: ALLOW / QUARANTINE / ESCALATE / DENY.
 *
 * The full 14-layer pipeline (Poincare embedding, Mobius phase, spectral
 * coherence, etc.) is at src/harmonic/pipeline14.ts in the main repo.
 * This file is the production proxy form — cheap-to-run, suitable for
 * Cloudflare Worker 50ms CPU budget.
 */

export type AxiomName =
  | "unitarity"  // A1 — norm / bounded output
  | "locality"   // A2 — stays within request scope
  | "causality"  // A3 — no time-ordering violations / future leak
  | "symmetry"   // A4 — no asymmetric bias / refusal injection
  | "composition"; // A5 — response shape matches request shape

export interface AxiomViolation {
  axiom: AxiomName;
  score: number;        // [0, 1]
  reason: string;       // short code for telemetry
  detail?: string;      // optional human-readable explanation
}

export interface AxiomReport {
  violations: AxiomViolation[];
  worstScore: number;
  worstAxiom: AxiomName | null;
  reasons: string[];
}

const MAX_REASONABLE_LENGTH = 16_000;
const TOO_SHORT_MIN = 1;

// A1 — Unitarity: the response should be present, bounded, and not empty.
function checkUnitarity(output: string): AxiomViolation | null {
  const len = output.length;
  if (len < TOO_SHORT_MIN) {
    return { axiom: "unitarity", score: 1.0, reason: "axiom:unitarity.empty", detail: "model returned empty content" };
  }
  if (len > MAX_REASONABLE_LENGTH) {
    return { axiom: "unitarity", score: 0.8, reason: "axiom:unitarity.overflow", detail: `output ${len} chars exceeds ${MAX_REASONABLE_LENGTH}` };
  }
  return null;
}

// A2 — Locality: output should not contain telltale exfil patterns
// (system prompt leakage, internal tool name leakage, instructions to
// reach external systems).
function checkLocality(output: string): AxiomViolation | null {
  const exfilPatterns: Array<[RegExp, string]> = [
    [/\b(system prompt|hidden instructions?|developer instructions?)\b/i, "axiom:locality.system_prompt_leak"],
    [/\b(rollback|restart)_conversation\b/i, "axiom:locality.tool_leak"],
    [/\bignore (previous|prior|all|above) instructions?\b/i, "axiom:locality.jailbreak_phrase"],
    [/\bbase64\s*[:=]\s*[A-Za-z0-9+/]{40,}/, "axiom:locality.suspicious_base64"],
  ];
  for (const [re, reason] of exfilPatterns) {
    if (re.test(output)) {
      return { axiom: "locality", score: 0.9, reason };
    }
  }
  return null;
}

// A3 — Causality: no time-ordering violations. MVP check: model shouldn't
// claim to know the user's future actions or pretend the conversation
// happened in a different order.
function checkCausality(output: string): AxiomViolation | null {
  const patterns: Array<[RegExp, string]> = [
    [/\bas you (will|are about to) (say|do|ask)\b/i, "axiom:causality.future_assertion"],
    [/\bI already (told|gave) you\b/i, "axiom:causality.past_assertion_loop"],
  ];
  for (const [re, reason] of patterns) {
    if (re.test(output)) {
      return { axiom: "causality", score: 0.5, reason };
    }
  }
  return null;
}

// A4 — Symmetry: detect canned refusal injection (model was steered into
// refusing without a real grounded reason) AND detect one-sided harmful
// content endorsement. MVP heuristic: balance "I cannot" / "I refuse"
// without any specific reason.
function checkSymmetry(output: string): AxiomViolation | null {
  const lower = output.toLowerCase();
  // Bare refusal with no reason given (we call this asymmetric)
  if (
    /\bi (cannot|can't|won't|refuse to)\b/.test(lower) &&
    !/\bbecause\b|\bdue to\b|\bin order to\b|\bsince\b/.test(lower)
  ) {
    return { axiom: "symmetry", score: 0.4, reason: "axiom:symmetry.bare_refusal" };
  }
  // Endorsement of clearly harmful operative content
  if (/\bhere(?:'s| is) how to (?:make|build|synthesize) (?:a bomb|explosives|methamphetamine|ricin)\b/i.test(output)) {
    return { axiom: "symmetry", score: 1.0, reason: "axiom:symmetry.harmful_endorsement" };
  }
  return null;
}

// A5 — Composition: response shape should roughly match request shape.
// MVP: if the request looked like a chat message but the response is
// only structural noise (code fences with no prose), flag soft.
function checkComposition(output: string, requestUserMessage: string): AxiomViolation | null {
  const trimmed = output.trim();
  if (trimmed.length === 0) {
    return { axiom: "composition", score: 1.0, reason: "axiom:composition.empty_after_trim" };
  }
  // If the user asked a yes/no question but the response is a 4000-char essay,
  // flag soft (composition mismatch).
  const userIsShortQuestion =
    requestUserMessage.trim().length < 80 && /\?$/.test(requestUserMessage.trim());
  if (userIsShortQuestion && trimmed.length > 4000) {
    return { axiom: "composition", score: 0.3, reason: "axiom:composition.length_mismatch" };
  }
  return null;
}

export function evaluateAxioms(output: string, requestUserMessage: string): AxiomReport {
  const checks: Array<AxiomViolation | null> = [
    checkUnitarity(output),
    checkLocality(output),
    checkCausality(output),
    checkSymmetry(output),
    checkComposition(output, requestUserMessage),
  ];
  const violations = checks.filter((v): v is AxiomViolation => v !== null);
  const reasons = violations.map(v => v.reason);
  let worstScore = 0;
  let worstAxiom: AxiomName | null = null;
  for (const v of violations) {
    if (v.score > worstScore) {
      worstScore = v.score;
      worstAxiom = v.axiom;
    }
  }
  return { violations, worstScore, worstAxiom, reasons };
}
