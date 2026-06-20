import { describe, it, expect } from 'vitest';
import { createResumePacket, createToolLoopDetector } from '../src/task-ledger.js';

// ─── ResumePacket ─────────────────────────────────────────────────────────────

describe('createResumePacket', () => {
  it('sets schema_version', () => {
    const pkt = createResumePacket({ goal: 'fix the bug' });
    expect(pkt.schema_version).toBe('scbe_resume_packet_v1');
  });

  it('carries the provided goal and fields', () => {
    const pkt = createResumePacket({
      goal: 'refactor pipeline',
      open_files: ['src/pipeline.ts'],
      last_passing_tests: ['tests/pipeline.test.ts'],
      blockers: ['missing type'],
      next_command: 'npm test',
    });
    expect(pkt.goal).toBe('refactor pipeline');
    expect(pkt.open_files).toEqual(['src/pipeline.ts']);
    expect(pkt.last_passing_tests).toEqual(['tests/pipeline.test.ts']);
    expect(pkt.blockers).toEqual(['missing type']);
    expect(pkt.next_command).toBe('npm test');
  });

  it('generates a unique session_id when none provided', () => {
    const a = createResumePacket({ goal: 'a' });
    const b = createResumePacket({ goal: 'b' });
    expect(typeof a.session_id).toBe('string');
    expect(a.session_id.length).toBeGreaterThan(0);
    expect(a.session_id).not.toBe(b.session_id);
  });

  it('uses the provided session_id', () => {
    const pkt = createResumePacket({ goal: 'x', session_id: 'ses-42' });
    expect(pkt.session_id).toBe('ses-42');
  });

  it('defaults arrays and next_command to empty', () => {
    const pkt = createResumePacket({ goal: 'minimal' });
    expect(pkt.open_files).toEqual([]);
    expect(pkt.last_passing_tests).toEqual([]);
    expect(pkt.blockers).toEqual([]);
    expect(pkt.next_command).toBe('');
  });

  it('generated_at_utc is a valid ISO timestamp', () => {
    const pkt = createResumePacket({ goal: 'ts check' });
    expect(() => new Date(pkt.generated_at_utc)).not.toThrow();
    expect(new Date(pkt.generated_at_utc).toISOString()).toBe(pkt.generated_at_utc);
  });
});

// ─── ToolLoopDetector ─────────────────────────────────────────────────────────

describe('createToolLoopDetector', () => {
  it('does not fire below min_calls', () => {
    const det = createToolLoopDetector({ min_calls: 3 });
    det.record('read', { content: 'abc' });
    det.record('read', { content: 'abc' });
    expect(det.check().is_looping).toBe(false);
    expect(det.check().evidence).toMatch(/need 3/);
  });

  it('fires when repeated calls produce no new evidence', () => {
    const det = createToolLoopDetector({ min_calls: 3, threshold: 0.6 });
    const same = { content: 'same' };
    det.record('grep', same);
    det.record('grep', same);
    det.record('grep', same);
    const result = det.check();
    expect(result.is_looping).toBe(true);
    expect(result.loop_tool).toBe('grep');
    // first call has delta=1 (new); next two are delta=0
    expect(result.repeat_count).toBe(2);
  });

  it('does not fire when every call produces new evidence', () => {
    const det = createToolLoopDetector({ min_calls: 3, threshold: 0.75 });
    det.record('read', { a: 1 });
    det.record('read', { b: 2 });
    det.record('read', { c: 3 });
    expect(det.check().is_looping).toBe(false);
  });

  it('tracks distinct tools independently, fires only on the looping one', () => {
    const det = createToolLoopDetector({ min_calls: 3, threshold: 0.6 });
    det.record('toolA', 'same');
    det.record('toolA', 'same');
    det.record('toolA', 'same');
    det.record('toolB', { new: 1 });
    det.record('toolB', { new: 2 });
    det.record('toolB', { new: 3 });
    const result = det.check();
    expect(result.is_looping).toBe(true);
    expect(result.loop_tool).toBe('toolA');
  });

  it('recommends escalate when zero-delta ratio is >= 90%', () => {
    const det = createToolLoopDetector({ min_calls: 5, threshold: 0.6 });
    // 10 identical calls: first has delta=1, next 9 have delta=0 → 9/10 = 90%
    for (let i = 0; i < 10; i++) det.record('grep', 'same_result');
    const result = det.check();
    expect(result.is_looping).toBe(true);
    expect(result.recommendation).toBe('escalate');
  });

  it('recommends stop when zero-delta ratio is between threshold and 90%', () => {
    const det = createToolLoopDetector({ min_calls: 3, threshold: 0.5 });
    // 3 identical calls: first has delta=1, next 2 have delta=0 → 2/3 = 66%, below 90%
    det.record('search', 'dup');
    det.record('search', 'dup');
    det.record('search', 'dup');
    const result = det.check();
    expect(result.is_looping).toBe(true);
    expect(result.recommendation).toBe('stop');
  });

  it('reset clears history and detection state', () => {
    const det = createToolLoopDetector({ min_calls: 3, threshold: 0.5 });
    det.record('read', 'x');
    det.record('read', 'x');
    det.record('read', 'x');
    expect(det.check().is_looping).toBe(true);
    det.reset();
    expect(det.history()).toHaveLength(0);
    expect(det.check().is_looping).toBe(false);
  });

  it('history returns all recorded calls in order', () => {
    const det = createToolLoopDetector();
    det.record('a', 1);
    det.record('b', 2);
    const h = det.history();
    expect(h).toHaveLength(2);
    expect(h[0].tool).toBe('a');
    expect(h[1].tool).toBe('b');
  });

  it('evidence_delta is 1 for first call, 0 for repeated result', () => {
    const det = createToolLoopDetector();
    const r1 = det.record('grep', 'result');
    const r2 = det.record('grep', 'result');
    const r3 = det.record('grep', 'new-result');
    expect(r1.evidence_delta).toBe(1);
    expect(r2.evidence_delta).toBe(0);
    expect(r3.evidence_delta).toBe(1);
  });

  it('result_hash is a hex string', () => {
    const det = createToolLoopDetector();
    const rec = det.record('tool', { data: 'value' });
    expect(rec.result_hash).toMatch(/^[0-9a-f]+$/);
    expect(rec.result_hash.length).toBeGreaterThan(0);
  });
});
