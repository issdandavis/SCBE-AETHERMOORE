/**
 * Real-prose fixture tests for the discourse atom layer.
 *
 * Purpose: verify that discourse atoms fire on NATURAL SPEECH, not just
 * command-style inputs. Each fixture is a realistic prose/dialogue sample.
 *
 * For each fixture we assert:
 *   - which atom IDs are detected (by semanticId presence)
 *   - what discourse profile emerges
 *   - that the profile makes semantic sense for that kind of speech act
 *
 * Failures here mean surface forms are too narrow (missed) or too broad
 * (false positive in wrong register). The fixtures are the spec.
 */

import { describe, it, expect } from 'vitest';
import { decompose } from '../src/semantic-bridge.js';

// ─── Helper ───────────────────────────────────────────────────────────────────

function ids(result: ReturnType<typeof decompose>): Set<string> {
  return new Set(result.atoms.map((a) => a.semanticId));
}

// ─── Fixture 1: Long monologue — ANNOUNCE + EXPAND → long_turn ───────────────

describe('fixture 1: long monologue opener + example chain', () => {
  const prose = [
    'Let me explain what I have been seeing.',
    'For example, in the first three weeks the pattern was completely clear.',
    'Similarly, by month two the same behavior appeared across the entire board.',
    'To illustrate how serious this is, here is what the data actually showed.',
  ].join(' ');

  it('detects ANNOUNCE (floor pre-buy)', () => {
    expect(ids(decompose(prose)).has('ANNOUNCE')).toBe(true);
  });

  it('detects EXPAND (chained examples)', () => {
    expect(ids(decompose(prose)).has('EXPAND')).toBe(true);
  });

  it('produces discourse profile = long_turn', () => {
    expect(decompose(prose).discourseProfile).toBe('long_turn');
  });

  it('does NOT produce governance_steer (no BLOCK present)', () => {
    expect(decompose(prose).discourseProfile).not.toBe('governance_steer');
  });
});

// ─── Fixture 2: Memory-backed moral claim — CARRY → warranted_claim ──────────

describe('fixture 2: personal memory as warrant', () => {
  const prose = [
    'I remember the night we shipped that feature.',
    'I was there when the servers went down at 3am.',
    'Back when we were a smaller team, I used to think that scale would solve these problems.',
    'In my experience, it never does.',
  ].join(' ');

  it('detects CARRY (personal memory)', () => {
    expect(ids(decompose(prose)).has('CARRY')).toBe(true);
  });

  it('produces discourse profile = warranted_claim', () => {
    expect(decompose(prose).discourseProfile).toBe('warranted_claim');
  });

  it('CARRY hit count >= 3 (multiple memory anchors)', () => {
    const d = decompose(prose);
    const carry = d.atoms.find((a) => a.semanticId === 'CARRY');
    expect(carry?.count).toBeGreaterThanOrEqual(3);
  });

  it('taskType is research (exposition/discovery register)', () => {
    // CARRY is research-typed; no governance trigger present
    expect(decompose(prose, 'general').taskType).toBe('research');
  });
});

// ─── Fixture 3: Listener backchannel — HOLD → backchannel ────────────────────

describe('fixture 3: pure listener responses', () => {
  const pure = 'Yeah. Mm. Right. I see. Okay. Go on.';

  it('detects HOLD', () => {
    expect(ids(decompose(pure)).has('HOLD')).toBe(true);
  });

  it('produces discourse profile = backchannel (HOLD is the only atom)', () => {
    expect(decompose(pure).discourseProfile).toBe('backchannel');
  });

  it('HOLD is the dominant atom', () => {
    expect(decompose(pure).dominant).toBe('HOLD');
  });

  // Single-word listener responses
  it('"mm" alone → HOLD / backchannel', () => {
    const d = decompose('mm');
    expect(ids(d).has('HOLD')).toBe(true);
    expect(d.discourseProfile).toBe('backchannel');
  });

  it('"i hear you" alone → HOLD / backchannel', () => {
    const d = decompose('i hear you');
    expect(ids(d).has('HOLD')).toBe(true);
    expect(d.discourseProfile).toBe('backchannel');
  });

  it('HOLD + domain atom does NOT produce backchannel', () => {
    // "okay, compile this" — listener token + task token, not pure HOLD
    const d = decompose('okay compile this module');
    expect(d.discourseProfile).not.toBe('backchannel');
  });
});

// ─── Fixture 4: Permission phrase mid-monologue — REQUEST → floor_hold ────────

describe('fixture 4: floor-hold permission tokens', () => {
  const prose =
    'I know this is a lot to take in — bear with me. Just to finish the thought: one more thing, and then I will hand it back.';

  it('detects REQUEST (permission tokens)', () => {
    expect(ids(decompose(prose)).has('REQUEST')).toBe(true);
  });

  it('produces discourse profile = floor_hold', () => {
    expect(decompose(prose).discourseProfile).toBe('floor_hold');
  });

  it('"does that make sense" → REQUEST floor_hold', () => {
    const d = decompose('Does that make sense? You know what I mean?');
    expect(ids(d).has('REQUEST')).toBe(true);
    expect(d.discourseProfile).toBe('floor_hold');
  });

  it('"to wrap up" → REQUEST floor_hold', () => {
    const d = decompose('To wrap up, the last thing I want to say is this.');
    expect(ids(d).has('REQUEST')).toBe(true);
    expect(d.discourseProfile).toBe('floor_hold');
  });
});

// ─── Fixture 5: Topic pivot without governance — PIVOT, profile ≠ governance_steer

describe('fixture 5: topic redirect without governance content', () => {
  const prose =
    'But actually, I think you are missing the main point here. What I mean is, the real question is not about performance at all. However, if we look at it from a different angle—';

  it('detects PIVOT (steering words)', () => {
    expect(ids(decompose(prose)).has('PIVOT')).toBe(true);
  });

  it('does NOT produce governance_steer (no BLOCK present)', () => {
    expect(decompose(prose).discourseProfile).not.toBe('governance_steer');
  });

  it('PIVOT count >= 2 (multiple steering markers)', () => {
    const d = decompose(prose);
    const pivot = d.atoms.find((a) => a.semanticId === 'PIVOT');
    expect(pivot?.count).toBeGreaterThanOrEqual(2);
  });

  it('standalone "but" in flowing prose fires PIVOT', () => {
    const d = decompose('That seems correct, but the actual result differs from what we expected.');
    expect(ids(d).has('PIVOT')).toBe(true);
  });
});

// ─── Fixture 6: Governance redirection — PIVOT + BLOCK → governance_steer ────

describe('fixture 6: governance pivot — PIVOT + BLOCK compound', () => {
  const prose = [
    'But the system threw an error when we tried to push.',
    'Actually the request was denied at the gateway.',
    'However, that exception should never have reached the barrier.',
  ].join(' ');

  it('detects PIVOT', () => {
    expect(ids(decompose(prose)).has('PIVOT')).toBe(true);
  });

  it('detects BLOCK', () => {
    expect(ids(decompose(prose)).has('BLOCK')).toBe(true);
  });

  it('produces discourse profile = governance_steer', () => {
    expect(decompose(prose).discourseProfile).toBe('governance_steer');
  });

  it('taskType is governance (PIVOT+BLOCK overrides any prior type)', () => {
    expect(decompose(prose, 'coding').taskType).toBe('governance');
    expect(decompose(prose, 'research').taskType).toBe('governance');
    expect(decompose(prose, 'general').taskType).toBe('governance');
  });

  // Realistic governance steering in natural dialogue:
  it('realistic: "but that was blocked — however we can appeal"', () => {
    const d = decompose('But that request was blocked. However, we can file an exception.');
    expect(d.discourseProfile).toBe('governance_steer');
    expect(d.taskType).toBe('governance');
  });
});

// ─── Fixture 7: Pure domain prose — no discourse profile ─────────────────────

describe('fixture 7: domain content prose, no discourse markers', () => {
  const prose =
    'The water flows through the channel toward the reservoir. The river carries sediment downstream. Steam rises from the hot springs near the surface.';

  it('detects WATER', () => {
    expect(ids(decompose(prose)).has('WATER')).toBe(true);
  });

  it('detects FLOW', () => {
    expect(ids(decompose(prose)).has('FLOW')).toBe(true);
  });

  it('discourse profile is null (no discourse markers)', () => {
    expect(decompose(prose).discourseProfile).toBeNull();
  });

  it('no discourse atoms in the atom list', () => {
    const discourseIds = new Set(['ANNOUNCE', 'EXPAND', 'REQUEST', 'PIVOT', 'CARRY', 'HOLD']);
    const detected = ids(decompose(prose));
    for (const did of discourseIds) {
      expect(detected.has(did)).toBe(false);
    }
  });
});

// ─── Fixture 8: Memory + pivot — CARRY wins over PIVOT alone ─────────────────

describe('fixture 8: memory-backed claim with pivot', () => {
  const prose = [
    'I remember when this architecture worked beautifully.',
    'But actually, that was a completely different codebase.',
    'Back when I was at the previous company, I used to see this pattern work reliably.',
    'However, our current setup has different constraints.',
  ].join(' ');

  it('detects both CARRY and PIVOT', () => {
    const detected = ids(decompose(prose));
    expect(detected.has('CARRY')).toBe(true);
    expect(detected.has('PIVOT')).toBe(true);
  });

  it('profile = warranted_claim (CARRY checked before floor_hold; no BLOCK for governance_steer)', () => {
    // No BLOCK present, so not governance_steer.
    // CARRY present → warranted_claim (checked before floor_hold/backchannel).
    expect(decompose(prose).discourseProfile).toBe('warranted_claim');
  });

  it('discourseProfile is NOT governance_steer (no BLOCK present)', () => {
    expect(decompose(prose).discourseProfile).not.toBe('governance_steer');
  });
});

// ─── Fixture 9: Technical governance without discourse markers ────────────────

describe('fixture 9: governance content — no discourse atoms', () => {
  const prose =
    'The error handler blocked the unauthorized request. The exception was denied at the policy layer. Barriers prevent access to protected resources.';

  it('detects BLOCK', () => {
    expect(ids(decompose(prose)).has('BLOCK')).toBe(true);
  });

  it('discourse profile is null (no steering/floor markers)', () => {
    expect(decompose(prose).discourseProfile).toBeNull();
  });

  it('taskType is governance (from BLOCK domain atom)', () => {
    expect(decompose(prose, 'general').taskType).toBe('governance');
  });
});

// ─── Fixture 10: Command/code prose — TRANSFORM, no discourse ────────────────

describe('fixture 10: command register — TRANSFORM only', () => {
  const prose = 'Convert the input data. Compile the TypeScript. Add the new dependencies.';

  it('detects TRANSFORM', () => {
    expect(ids(decompose(prose)).has('TRANSFORM')).toBe(true);
  });

  it('discourse profile is null', () => {
    expect(decompose(prose).discourseProfile).toBeNull();
  });

  it('taskType is coding', () => {
    expect(decompose(prose, 'general').taskType).toBe('coding');
  });
});

// ─── Fixture 11: CARRY + EXPAND — warranted_claim wins (CARRY checked first) ─

describe('fixture 11: memory-backed claim with example expansion', () => {
  const prose = [
    "I've seen this exact pattern before.",
    'Back when we had the monolith, I used to debug these issues every week.',
    'For example, in 2019 we had a similar incident that took three days to resolve.',
    'Similarly, in 2021 the same root cause appeared in a different service.',
    'In my experience the fix is always the same: isolate the state mutation.',
  ].join(' ');

  it('detects CARRY', () => {
    expect(ids(decompose(prose)).has('CARRY')).toBe(true);
  });

  it('detects EXPAND', () => {
    expect(ids(decompose(prose)).has('EXPAND')).toBe(true);
  });

  it('profile = warranted_claim (CARRY checked before long_turn)', () => {
    // Priority: governance_steer → long_turn → warranted_claim → floor_hold → backchannel
    // CARRY is present so warranted_claim fires unless PIVOT+BLOCK or ANNOUNCE+EXPAND
    // fires first. ANNOUNCE is NOT present here, so long_turn does not fire.
    expect(decompose(prose).discourseProfile).toBe('warranted_claim');
  });
});

// ─── Fixture 12: Announcement with permission request ────────────────────────

describe('fixture 12: ANNOUNCE + REQUEST — floor_hold (no EXPAND for long_turn)', () => {
  const prose = [
    'Let me explain the three things you need to know about this system.',
    'One thing is the architecture, another is the deployment model.',
    'To wrap up, bear with me on the third point — almost done.',
  ].join(' ');

  it('detects ANNOUNCE', () => {
    expect(ids(decompose(prose)).has('ANNOUNCE')).toBe(true);
  });

  it('detects REQUEST (permission tokens present)', () => {
    expect(ids(decompose(prose)).has('REQUEST')).toBe(true);
  });

  it('does NOT detect EXPAND (no "for example" / "similarly" pattern)', () => {
    // "one thing / another" is ANNOUNCE-form, not EXPAND-form
    // This is the key distinction: announcing a list vs chaining examples
    expect(ids(decompose(prose)).has('EXPAND')).toBe(false);
  });

  it('profile = floor_hold (ANNOUNCE+REQUEST without EXPAND means no long_turn)', () => {
    expect(decompose(prose).discourseProfile).toBe('floor_hold');
  });
});
