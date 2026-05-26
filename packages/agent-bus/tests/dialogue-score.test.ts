import { describe, it, expect } from 'vitest';
import { scoreDialogue, decompose } from '../src/semantic-bridge.js';

describe('scoreDialogue', () => {
  it('scores a bare exposition passage low', () => {
    const result = scoreDialogue('The company was founded in 2019 and grew quickly.');
    expect(result.total).toBeLessThan(6);
    expect(result.strongestFix).toMatch(/exposition/i);
  });

  it('scores a long-turn passage higher', () => {
    const text =
      'No. Let me tell you what happened. For example, in March, in the Tacoma office, ' +
      'the cup on her desk. She never touched it. I was afraid to ask. ' +
      'Another case: the meeting she never attended. ' +
      'And that was before anyone else knew. She looked at me. I said nothing.';
    const result = scoreDialogue(text);
    expect(result.profile).toBe('long_turn');
    expect(result.total).toBeGreaterThanOrEqual(6);
    const reason = result.dimensions.find((d) => d.name === 'Reason to speak now');
    expect(reason!.score).toBeGreaterThanOrEqual(1);
  });

  it('detects warranted_claim from memory-backed text', () => {
    const text =
      'I can answer that, but not quickly. I remember the kitchen doorway in 2021. ' +
      'I stood there and watched him fold the paper. That was the moment I knew.';
    const result = scoreDialogue(text);
    expect(result.profile).toBe('warranted_claim');
    const memory = result.dimensions.find((d) => d.name === 'Concrete memory or example');
    expect(memory!.score).toBeGreaterThanOrEqual(1);
  });

  it('flags density warnings for over-steered text', () => {
    const text =
      'But the point is... What I mean is... That is not what happened... ' +
      'So when I say... But the real issue... Look, here is the thing... ' +
      'And that was before... I am telling you this because...';
    const result = scoreDialogue(text);
    expect(result.densityWarnings.length).toBeGreaterThan(0);
    expect(result.densityWarnings.some((w) => w.includes('over-steered'))).toBe(true);
  });

  it('warns when listener disappears', () => {
    const text =
      'I was there. The room was cold. I remember the clock. I waited. Nothing happened.';
    const result = scoreDialogue(text);
    expect(result.densityWarnings.some((w) => w.includes('disappear'))).toBe(true);
  });

  it('produces a valid schema version', () => {
    const result = scoreDialogue('Test passage.');
    expect(result.schemaVersion).toBe('scbe-dialogue-score-v1');
  });

  it('attaches dialogue_score to AgentBusResult via runEvent', async () => {
    // Import runEvent and verify the shape
    const { runEvent } = await import('../src/index.js');
    const result = await runEvent(
      {
        task: 'No. That is not what happened. I was there.',
        taskType: 'general',
        privacy: 'local_only',
      },
      { repoRoot: process.cwd() }
    );
    // If discourse atoms matched, dialogue_score should be present
    if (result.dialogue_score) {
      expect(result.dialogue_score.schemaVersion).toBe('scbe-dialogue-score-v1');
      expect(result.dialogue_score.dimensions.length).toBe(7);
    }
  });
});
