/**
 * @file contracts.ts
 * @module agent-bus/contracts
 *
 * Structured output contracts for SCBE Agent Bus events.
 *
 * Research-backed: LangGraph, Pydantic AI, and Vercel AI SDK 6 all enforce
 * JSON schema validation on agent outputs. This prevents AI agents from
 * receiving unparseable blobs and enables reliable downstream chaining.
 *
 * Usage:
 *   const event = {
 *     task: 'Summarize',
 *     outputSchema: z.object({ summary: z.string(), confidence: z.number() }),
 *   };
 *   const result = await runEvent(event);
 *   // result.output is validated and typed
 */

import { z } from 'zod';

export type JsonSchema = z.ZodTypeAny;

export type ValidatedOutput<T = unknown> =
  | {
      ok: true;
      data: T;
    }
  | {
      ok: false;
      error: string;
      raw: unknown;
    };

/**
 * Validate an arbitrary value against a Zod schema.
 * Never throws. Returns a structured result AI agents can branch on.
 */
export function validateOutput<T>(raw: unknown, schema: JsonSchema): ValidatedOutput<T> {
  const result = schema.safeParse(raw);
  if (result.success) {
    return { ok: true, data: result.data as T };
  }
  const summary = result.error.issues
    .slice(0, 3)
    .map((i) => `${i.path.join('.') || '<root>'}: ${i.message}`)
    .join('; ');
  return { ok: false, error: summary, raw };
}

/**
 * Pre-built contract schemas for common agent outputs.
 * Import these to enforce consistency across task types.
 */

export const SummaryContract = z.object({
  summary: z.string().min(1),
  confidence: z.number().min(0).max(1).optional(),
  sources: z.array(z.string()).optional(),
});

export const CodeReviewContract = z.object({
  issues: z.array(
    z.object({
      severity: z.enum(['critical', 'warning', 'info']),
      line: z.number().optional(),
      message: z.string(),
      suggestion: z.string().optional(),
    })
  ),
  approved: z.boolean(),
});

export const ResearchContract = z.object({
  findings: z.array(
    z.object({
      claim: z.string(),
      evidence: z.string(),
      confidence: z.number().min(0).max(1),
    })
  ),
  gaps: z.array(z.string()).optional(),
});

export const GovernanceDecisionContract = z.object({
  decision: z.enum(['allow', 'deny', 'quarantine']),
  reason: z.string(),
  risk_score: z.number().min(0).max(1).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});
