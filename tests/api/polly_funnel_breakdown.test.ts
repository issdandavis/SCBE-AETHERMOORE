/**
 * @file polly_funnel_breakdown.test.ts
 * Pins the per-event funnel breakdown contract.
 *
 * Two new code paths land here together:
 *   1. _polly_hf_upload.js prefixes funnel filenames with `${event}__`
 *      so the dataset's directory listing carries event identity in
 *      the filename and a single HF tree call yields per-event counts.
 *   2. stats.js exposes ?breakdown=event which parses those filenames
 *      and returns funnel_by_event, the per-event card on the
 *      polly-stats dashboard.
 *
 * Files captured before the migration (no `__` separator) bucket as
 * `unknown` so the breakdown stays additive without losing rows.
 */

delete process.env.HF_TOKEN;
delete process.env.HUGGINGFACE_TOKEN;
delete process.env.HUGGING_FACE_HUB_TOKEN;

import { describe, it, expect } from 'vitest';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const hfUpload = require('../../api/_polly_hf_upload.js');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const stats = require('../../api/polly/stats.js');

describe('hf_upload pathFor — funnel filename prefix', () => {
  const { pathFor, safeFunnelEvent } = hfUpload._internal;

  it('prefixes filename with event for funnel records', () => {
    const path = pathFor({
      kind: 'funnel',
      event: 'arrival',
      ts: 1715200000,
    });
    // polly-funnel/2024-05-08/arrival__YYYYMMDDTHHMMSS-NONCE.json
    expect(path).toMatch(
      /^polly-funnel\/\d{4}-\d{2}-\d{2}\/arrival__\d{8}T\d{6}-[0-9a-f]{6}\.json$/
    );
  });

  it('keeps legacy filename shape when funnel record has no event', () => {
    const path = pathFor({ kind: 'funnel', ts: 1715200000 });
    expect(path).toMatch(/^polly-funnel\/\d{4}-\d{2}-\d{2}\/\d{8}T\d{6}-[0-9a-f]{6}\.json$/);
    expect(path).not.toContain('__');
  });

  it('strips dangerous chars from the event slug', () => {
    expect(safeFunnelEvent('arrival/../etc/passwd')).toBe('arrivaletcpasswd');
    expect(safeFunnelEvent('Snapshot Intake OK')).toBe('snapshotintakeok');
    expect(safeFunnelEvent(undefined as unknown as string)).toBe('');
    expect(safeFunnelEvent('a'.repeat(200)).length).toBeLessThanOrEqual(60);
  });

  it('does not change non-funnel kinds', () => {
    const lead = pathFor({ kind: 'lead', ts: 1715200000 });
    expect(lead).toMatch(/^polly-leads\/\d{4}-\d{2}-\d{2}\/\d{8}T\d{6}-[0-9a-f]{6}\.json$/);
    expect(lead).not.toContain('__');
    const chat = pathFor({ kind: 'chat', ts: 1715200000 });
    expect(chat).toMatch(/^polly-chat-live\/\d{4}-\d{2}-\d{2}\/\d{8}T\d{6}-[0-9a-f]{6}\.json$/);
  });
});

describe('stats breakdownByEvent — parses funnel filenames', () => {
  const { breakdownByEvent } = stats._internal;

  it('counts new-format filenames by event prefix', () => {
    const counts = breakdownByEvent([
      { path: 'polly-funnel/2026-05-09/arrival__20260509T120000-aaaaaa.json' },
      { path: 'polly-funnel/2026-05-09/arrival__20260509T121000-bbbbbb.json' },
      { path: 'polly-funnel/2026-05-09/scroll_50__20260509T122000-cccccc.json' },
      { path: 'polly-funnel/2026-05-09/cta_click_buy__20260509T123000-dddddd.json' },
    ]);
    expect(counts).toEqual({
      arrival: 2,
      scroll_50: 1,
      cta_click_buy: 1,
    });
  });

  it('buckets legacy unprefixed filenames as unknown', () => {
    const counts = breakdownByEvent([
      { path: 'polly-funnel/2026-05-08/20260508T120000-aaaaaa.json' },
      { path: 'polly-funnel/2026-05-08/20260508T121000-bbbbbb.json' },
      { path: 'polly-funnel/2026-05-08/arrival__20260508T122000-cccccc.json' },
    ]);
    expect(counts).toEqual({ unknown: 2, arrival: 1 });
  });

  it('returns empty object for empty input', () => {
    expect(breakdownByEvent([])).toEqual({});
  });

  it('tolerates malformed entries without crashing', () => {
    const counts = breakdownByEvent([
      null,
      undefined,
      {},
      { path: '' },
      { path: 'polly-funnel/2026-05-09/arrival__x.json' },
    ] as unknown as { path: string }[]);
    // null/undefined/empty path → unknown bucket; only the valid one counts.
    expect(counts.arrival).toBe(1);
    expect(counts.unknown).toBe(4);
  });
});
