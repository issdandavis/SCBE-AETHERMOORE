import { describe, expect, it } from 'vitest';

describe('playwright crosstalk runner scoring', () => {
  it('passes when commercial copy, checkout links, and actions are present', async () => {
    const mod = await import('../../scripts/system/playwright_crosstalk_runner.mjs');
    const evidence = {
      status: 200,
      title: 'AetherMoore Products',
      h1: 'Buy Snapshot $500',
      expectedCopyMissing: [],
      stripeLinkCount: 2,
      overflowPx: 0,
      bodyLength: 2000,
      pageErrors: [],
      consoleErrors: [],
      actionOk: true,
      workDoneCount: 3,
      actionResults: [
        { type: 'click', ok: true },
        { type: 'fill', ok: true },
        { type: 'expectText', ok: true },
      ],
      inputSnapshot: [{ id: 'leadContact', hasValue: true, valueLength: 28 }],
    };

    const votes = mod.runBuiltInReviewers(evidence);
    const aggregate = mod.aggregateVotes(votes);

    expect(votes).toHaveLength(3);
    expect(aggregate.verdict).toBe('pass');
    expect(aggregate.averageScore).toBeGreaterThanOrEqual(0.8);
  });

  it('fails when the browser did not complete the functional work', async () => {
    const mod = await import('../../scripts/system/playwright_crosstalk_runner.mjs');
    const evidence = {
      status: 200,
      title: 'AetherMoore Products',
      h1: 'Products',
      expectedCopyMissing: [],
      stripeLinkCount: 1,
      overflowPx: 0,
      bodyLength: 2000,
      pageErrors: [],
      consoleErrors: [],
      actionOk: false,
      workDoneCount: 0,
      actionResults: [{ type: 'click', ok: false, error: 'button not found' }],
      inputSnapshot: [],
    };

    const votes = mod.runBuiltInReviewers(evidence);
    const aggregate = mod.aggregateVotes(votes);

    expect(aggregate.verdict).toBe('fail');
    expect(aggregate.failingReviewers.length).toBeGreaterThan(0);
  });
});
