import { describe, it, expect } from 'vitest';
import {
  createHandoff,
  throwHandoff,
  catchHandoff,
  validateHandoff,
  completeHandoff,
  dropHandoff,
  isHandoffExpired,
  getReceipts,
  summarizeHandoff,
} from '../src/handoff-packet.js';

const NOW = '2026-05-30T10:00:00.000Z';
const PAST = '2026-05-30T09:00:00.000Z';
const FUTURE = '2026-05-30T11:00:00.000Z';

// ─── createHandoff ────────────────────────────────────────────────────────────

describe('createHandoff', () => {
  it('creates a HELD packet with correct schema', () => {
    const p = createHandoff('agent-alpha', { task: 'repair zone z1' }, { now: NOW });
    expect(p.schema_version).toBe('scbe_handoff_v1');
    expect(p.state).toBe('HELD');
    expect(p.issuer_id).toBe('agent-alpha');
    expect(p.holder_id).toBe('agent-alpha');
    expect(p.mission.task).toBe('repair zone z1');
    expect(p.receipts).toHaveLength(1);
    expect(p.receipts[0].to_state).toBe('HELD');
    expect(p.receipts[0].note).toBe('created');
  });

  it('respects explicit packetId', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW, packetId: 'hp-test-001' });
    expect(p.packet_id).toBe('hp-test-001');
  });

  it('respects priority and authority options', () => {
    const p = createHandoff(
      'operator-1',
      { task: 'emergency seal' },
      { now: NOW, priority: 'critical', authority: 'operator' }
    );
    expect(p.priority).toBe('critical');
    expect(p.authority).toBe('operator');
  });

  it('sets deadline when provided', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW, deadlineAt: FUTURE });
    expect(p.deadline_at).toBe(FUTURE);
  });

  it('defaults to auto authority and routine priority', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW });
    expect(p.authority).toBe('auto');
    expect(p.priority).toBe('routine');
  });
});

// ─── throwHandoff ─────────────────────────────────────────────────────────────

describe('throwHandoff', () => {
  it('transitions HELD → THROWN and sets target_id', () => {
    const held = createHandoff('alpha', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'beta', { now: NOW });
    expect(thrown.state).toBe('THROWN');
    expect(thrown.target_id).toBe('beta');
    expect(thrown.holder_id).toBe('alpha');
    expect(thrown.receipts).toHaveLength(2);
    expect(thrown.receipts[1].from_state).toBe('HELD');
    expect(thrown.receipts[1].to_state).toBe('THROWN');
  });

  it('rejects throw from non-HELD state', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    expect(() => throwHandoff(thrown, 'c', { now: NOW })).toThrow('must be HELD');
  });

  it('does not mutate original packet', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    throwHandoff(held, 'b', { now: NOW });
    expect(held.state).toBe('HELD');
  });
});

// ─── catchHandoff ─────────────────────────────────────────────────────────────

describe('catchHandoff', () => {
  it('transitions THROWN → CAUGHT and updates holder_id', () => {
    const held = createHandoff('alpha', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'beta', { now: NOW });
    const caught = catchHandoff(thrown, 'beta', { now: NOW });
    expect(caught.state).toBe('CAUGHT');
    expect(caught.holder_id).toBe('beta');
    expect(caught.receipts).toHaveLength(3);
  });

  it('rejects catch from non-THROWN state', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    expect(() => catchHandoff(held, 'b', { now: NOW })).toThrow('must be THROWN');
  });

  it('allows a different agent to catch (intercept scenario)', () => {
    const held = createHandoff('alpha', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'beta', { now: NOW });
    const caught = catchHandoff(thrown, 'gamma', { now: NOW });
    expect(caught.holder_id).toBe('gamma');
    expect(caught.target_id).toBe('beta');
  });
});

// ─── validateHandoff ──────────────────────────────────────────────────────────

describe('validateHandoff', () => {
  function makeCaught() {
    const held = createHandoff(
      'alpha',
      { task: 'patch zone z3' },
      { now: NOW, deadlineAt: FUTURE }
    );
    const thrown = throwHandoff(held, 'beta', { now: NOW });
    return catchHandoff(thrown, 'beta', { now: NOW });
  }

  it('transitions CAUGHT → VALIDATING and returns validation', () => {
    const caught = makeCaught();
    const { packet, validation } = validateHandoff(caught, { now: NOW });
    expect(packet.state).toBe('VALIDATING');
    expect(validation.state).toBe('VALIDATING');
    expect(validation.valid).toBe(true);
    expect(validation.expired).toBe(false);
    expect(validation.errors).toHaveLength(0);
    expect(validation.ms_until_deadline).toBeGreaterThan(0);
  });

  it('marks expired when now >= deadline', () => {
    const caught = makeCaught();
    const { validation } = validateHandoff(caught, { now: FUTURE });
    expect(validation.expired).toBe(true);
    expect(validation.valid).toBe(false);
    expect(validation.errors).toContain('deadline exceeded');
  });

  it('rejects validation from non-CAUGHT state', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    expect(() => validateHandoff(held, { now: NOW })).toThrow('must be CAUGHT');
  });
});

// ─── completeHandoff ──────────────────────────────────────────────────────────

describe('completeHandoff', () => {
  function makeValidating() {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const caught = catchHandoff(thrown, 'b', { now: NOW });
    const { packet } = validateHandoff(caught, { now: NOW });
    return packet;
  }

  it('transitions VALIDATING → DONE with result', () => {
    const validating = makeValidating();
    const done = completeHandoff(validating, { repaired: true }, { now: NOW });
    expect(done.state).toBe('DONE');
    expect(done.result).toEqual({ repaired: true });
    expect(done.receipts[done.receipts.length - 1].to_state).toBe('DONE');
  });

  it('rejects completion from non-VALIDATING state', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    expect(() => completeHandoff(held, {}, { now: NOW })).toThrow('must be VALIDATING');
  });

  it('full happy-path lifecycle produces correct receipt chain', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const caught = catchHandoff(thrown, 'b', { now: NOW });
    const { packet: validating } = validateHandoff(caught, { now: NOW });
    const done = completeHandoff(validating, 'ok', { now: NOW });

    const states = done.receipts.map((r) => r.to_state);
    expect(states).toEqual(['HELD', 'THROWN', 'CAUGHT', 'VALIDATING', 'DONE']);
  });
});

// ─── dropHandoff ─────────────────────────────────────────────────────────────

describe('dropHandoff', () => {
  it('transitions any non-terminal state → DROPPED', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const dropped = dropHandoff(held, 'agent offline', { now: NOW });
    expect(dropped.state).toBe('DROPPED');
    expect(dropped.drop_reason).toBe('agent offline');
  });

  it('can drop a THROWN packet (target never responded)', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const dropped = dropHandoff(thrown, 'timeout', { now: NOW });
    expect(dropped.state).toBe('DROPPED');
  });

  it('rejects drop on DONE packet', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const caught = catchHandoff(thrown, 'b', { now: NOW });
    const { packet: validating } = validateHandoff(caught, { now: NOW });
    const done = completeHandoff(validating, 'ok', { now: NOW });
    expect(() => dropHandoff(done, 'too late', { now: NOW })).toThrow('already terminal');
  });

  it('rejects double-drop', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const dropped = dropHandoff(held, 'first drop', { now: NOW });
    expect(() => dropHandoff(dropped, 'second drop', { now: NOW })).toThrow('already terminal');
  });
});

// ─── isHandoffExpired ─────────────────────────────────────────────────────────

describe('isHandoffExpired', () => {
  it('returns false when no deadline', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW });
    expect(isHandoffExpired(p, { now: NOW })).toBe(false);
  });

  it('returns false before deadline', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW, deadlineAt: FUTURE });
    expect(isHandoffExpired(p, { now: NOW })).toBe(false);
  });

  it('returns true at or after deadline', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW, deadlineAt: NOW });
    expect(isHandoffExpired(p, { now: NOW })).toBe(true);
    expect(isHandoffExpired(p, { now: FUTURE })).toBe(true);
  });

  it('returns false before a past-set future deadline', () => {
    const p = createHandoff('a', { task: 't' }, { now: PAST, deadlineAt: FUTURE });
    expect(isHandoffExpired(p, { now: NOW })).toBe(false);
  });
});

// ─── getReceipts ─────────────────────────────────────────────────────────────

describe('getReceipts', () => {
  it('returns a stable copy of the receipt chain', () => {
    const held = createHandoff('a', { task: 't' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const receipts = getReceipts(thrown);
    expect(receipts).toHaveLength(2);
    expect(receipts[0].to_state).toBe('HELD');
    expect(receipts[1].to_state).toBe('THROWN');
  });
});

// ─── summarizeHandoff ────────────────────────────────────────────────────────

describe('summarizeHandoff', () => {
  it('returns correct hop_count (receipts - 1 for creation)', () => {
    const held = createHandoff('a', { task: 'do the thing' }, { now: NOW });
    const thrown = throwHandoff(held, 'b', { now: NOW });
    const caught = catchHandoff(thrown, 'b', { now: NOW });
    const summary = summarizeHandoff(caught, { now: NOW });
    expect(summary.hop_count).toBe(2); // throw + catch
    expect(summary.task).toBe('do the thing');
    expect(summary.state).toBe('CAUGHT');
    expect(summary.expired).toBe(false);
  });

  it('marks expired in summary when past deadline', () => {
    const p = createHandoff('a', { task: 't' }, { now: PAST, deadlineAt: PAST });
    const summary = summarizeHandoff(p, { now: NOW });
    expect(summary.expired).toBe(true);
  });

  it('includes drop_reason for dropped packets', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW });
    const dropped = dropHandoff(p, 'zone locked', { now: NOW });
    const summary = summarizeHandoff(dropped, { now: NOW });
    expect(summary.drop_reason).toBe('zone locked');
    expect(summary.state).toBe('DROPPED');
  });

  it('records last_receipt_at', () => {
    const p = createHandoff('a', { task: 't' }, { now: NOW });
    const summary = summarizeHandoff(p, { now: NOW });
    expect(summary.last_receipt_at).toBe(NOW);
  });
});
