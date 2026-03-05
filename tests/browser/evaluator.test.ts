import { describe, expect, it } from 'vitest';
import { BrowserActionEvaluator } from '../../src/browser/evaluator.js';
import type { BrowserAction, BrowserObservation } from '../../src/browser/types.js';

function makeObservation(overrides: Partial<BrowserObservation> = {}): BrowserObservation {
  const base: BrowserObservation = {
    sessionId: 'sess-test',
    sequence: 1,
    timestamp: Date.now(),
    page: {
      url: 'https://example.com',
      title: 'Example',
      readyState: 'complete',
      viewport: { width: 1280, height: 720 },
      scroll: { x: 0, y: 0 },
      interactiveElements: [],
      forms: [],
      dialogs: [],
      loadTime: 120,
      timestamp: Date.now(),
    },
  };
  return { ...base, ...overrides, page: { ...base.page, ...(overrides.page ?? {}) } };
}

describe('BrowserActionEvaluator', () => {
  it('applies custom thresholds during decisioning', () => {
    const observation = makeObservation({
      page: {
        url: 'https://www.google.com/search?q=scbe',
      },
    });

    const action: BrowserAction = { type: 'scroll', delta: { x: 0, y: 300 } };
    const sessionState = { sessionRisk: 0, actionCount: 0, errorCount: 0 };

    const defaultEvaluator = new BrowserActionEvaluator();
    const tightenedEvaluator = new BrowserActionEvaluator({
      thresholds: { allow: 0.01, quarantine: 0.2, escalate: 0.8, deny: 0.8 },
    });

    const defaultDecision = defaultEvaluator.evaluate(action, observation, sessionState).decision;
    const tightenedDecision = tightenedEvaluator.evaluate(action, observation, sessionState).decision;

    expect(defaultDecision).toBe('ALLOW');
    expect(tightenedDecision).not.toBe(defaultDecision);
  });

  it('builds deterministic sidepanel brief with cautions and ranked recommendations', () => {
    const interactiveElements = Array.from({ length: 10 }, (_, idx) => ({
      tagName: idx === 2 ? 'button' : 'a',
      id: idx === 2 ? 'continue' : `el-${idx}`,
      classList: ['interactive'],
      textContent: idx === 2 ? 'Continue' : `Element ${idx}`,
      bounds: { x: 10 + idx, y: 20 + idx, width: 100, height: 24 },
      visible: true,
      interactive: true,
      dataAttributes: {},
    }));

    const observation = makeObservation({
      page: {
        url: 'https://bank.example.com/login',
        title: 'Secure Login',
        interactiveElements,
        forms: [
          {
            identifier: 'login',
            action: '/login',
            method: 'POST',
            fields: [
              {
                name: 'password',
                type: 'password',
                value: '',
                required: true,
                sensitivity: 'password',
              },
            ],
            hasSensitiveFields: true,
            sensitiveFieldTypes: ['password'],
          },
        ],
      },
    });

    const evaluator = new BrowserActionEvaluator();
    const brief = evaluator.buildSidepanelBrief(observation, {
      sessionRisk: 0.2,
      actionCount: 5,
      errorCount: 0,
    });

    expect(brief.url).toBe(observation.page.url);
    expect(brief.title).toBe('Secure Login');
    expect(brief.pageSummary).toContain('Secure Login');
    expect(brief.cautionFlags).toContain('sensitive_form_detected');
    expect(brief.recommendations.length).toBeGreaterThan(0);
    expect(
      brief.recommendations.some(
        (rec) => rec.action.type === 'click' && rec.action.selector === '#continue'
      )
    ).toBe(true);

    for (let i = 1; i < brief.recommendations.length; i++) {
      expect(brief.recommendations[i].riskScore).toBeGreaterThanOrEqual(
        brief.recommendations[i - 1].riskScore
      );
    }
  });
});
