/**
 * @file task-ledger.ts
 * @module agent-bus/task-ledger
 * @layer Cross-layer stateful task tracking
 * @component TaskLedger — resume packets and tool-loop detection
 *
 * Lanes 52 + 55 of the 100-lane improvement map.
 *
 * ResumePacket (Lane 52): captures session goal, open files, last passing
 * tests, blockers, and next command — enough for any continuation to pick
 * up exactly where the interrupted session left off.
 *
 * ToolLoopDetector (Lane 55): detects when repeated tool calls add no new
 * evidence. Comparison rule: a call adds evidence when its result_hash
 * differs from every prior result for the same tool. When the proportion
 * of zero-delta calls for a single tool exceeds the threshold, the
 * detector fires. This catches same-args repeats AND the common failure
 * mode where args vary slightly but results are equivalent.
 */

import crypto from 'node:crypto';

// ─── ResumePacket ─────────────────────────────────────────────────────────────

export interface ResumePacket {
  schema_version: 'scbe_resume_packet_v1';
  session_id: string;
  goal: string;
  open_files: string[];
  last_passing_tests: string[];
  blockers: string[];
  next_command: string;
  generated_at_utc: string;
}

export interface ResumePacketOptions {
  session_id?: string;
  goal: string;
  open_files?: string[];
  last_passing_tests?: string[];
  blockers?: string[];
  next_command?: string;
}

export function createResumePacket(opts: ResumePacketOptions): ResumePacket {
  return {
    schema_version: 'scbe_resume_packet_v1',
    session_id: opts.session_id ?? crypto.randomBytes(8).toString('hex'),
    goal: opts.goal,
    open_files: opts.open_files ?? [],
    last_passing_tests: opts.last_passing_tests ?? [],
    blockers: opts.blockers ?? [],
    next_command: opts.next_command ?? '',
    generated_at_utc: new Date().toISOString(),
  };
}

// ─── ToolLoopDetector ─────────────────────────────────────────────────────────

export interface ToolCallRecord {
  tool: string;
  /** Truncated SHA-256 of the JSON-serialized result. */
  result_hash: string;
  /** 0 = duplicate result; 1 = new result not seen before for this tool. */
  evidence_delta: number;
  called_at: string;
}

export interface ToolLoopDetection {
  is_looping: boolean;
  loop_tool: string | null;
  /** Number of zero-delta calls on loop_tool. */
  repeat_count: number;
  recommendation: 'continue' | 'stop' | 'escalate';
  evidence: string;
}

export interface ToolLoopDetectorOptions {
  /** Proportion of zero-delta calls that triggers a loop [0,1]. Default: 0.75 */
  threshold?: number;
  /** Minimum calls to a single tool before loop detection can fire. Default: 3 */
  min_calls?: number;
}

export function createToolLoopDetector(options: ToolLoopDetectorOptions = {}): {
  record: (tool: string, result: unknown) => ToolCallRecord;
  check: () => ToolLoopDetection;
  reset: () => void;
  history: () => ToolCallRecord[];
} {
  const threshold = options.threshold ?? 0.75;
  const min_calls = options.min_calls ?? 3;

  const seenHashes = new Map<string, Set<string>>();
  const calls: ToolCallRecord[] = [];

  function hashResult(result: unknown): string {
    const json = JSON.stringify(result ?? null);
    return crypto.createHash('sha256').update(json).digest('hex').slice(0, 16);
  }

  function record(tool: string, result: unknown): ToolCallRecord {
    const result_hash = hashResult(result);
    const seen = seenHashes.get(tool);
    let evidence_delta: number;

    if (!seen) {
      seenHashes.set(tool, new Set([result_hash]));
      evidence_delta = 1;
    } else if (seen.has(result_hash)) {
      evidence_delta = 0;
    } else {
      seen.add(result_hash);
      evidence_delta = 1;
    }

    const rec: ToolCallRecord = {
      tool,
      result_hash,
      evidence_delta,
      called_at: new Date().toISOString(),
    };
    calls.push(rec);
    return rec;
  }

  function check(): ToolLoopDetection {
    const perTool = new Map<string, { total: number; zero: number }>();
    for (const c of calls) {
      const s = perTool.get(c.tool) ?? { total: 0, zero: 0 };
      s.total++;
      if (c.evidence_delta === 0) s.zero++;
      perTool.set(c.tool, s);
    }

    let worst_tool: string | null = null;
    let worst_ratio = 0;
    let worst_zero = 0;
    let worst_total = 0;

    for (const [tool, stat] of perTool.entries()) {
      if (stat.total < min_calls) continue;
      const ratio = stat.zero / stat.total;
      if (ratio > worst_ratio) {
        worst_ratio = ratio;
        worst_tool = tool;
        worst_zero = stat.zero;
        worst_total = stat.total;
      }
    }

    if (worst_tool === null || worst_ratio < threshold) {
      const callCount = calls.length;
      const minMsg =
        callCount < min_calls
          ? `${callCount} call(s); need ${min_calls} to evaluate`
          : `no tool exceeds ${Math.round(threshold * 100)}% zero-delta threshold`;
      return {
        is_looping: false,
        loop_tool: null,
        repeat_count: 0,
        recommendation: 'continue',
        evidence: minMsg,
      };
    }

    const recommendation: ToolLoopDetection['recommendation'] =
      worst_ratio >= 0.9 ? 'escalate' : 'stop';

    return {
      is_looping: true,
      loop_tool: worst_tool,
      repeat_count: worst_zero,
      recommendation,
      evidence: `'${worst_tool}' produced no new evidence in ${worst_zero} of ${worst_total} calls (${Math.round(worst_ratio * 100)}%)`,
    };
  }

  function reset(): void {
    seenHashes.clear();
    calls.length = 0;
  }

  function history(): ToolCallRecord[] {
    return [...calls];
  }

  return { record, check, reset, history };
}
