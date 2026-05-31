/**
 * @file customer_support_triage.test.ts
 *
 * Full test coverage for workflows/openai/customer_support_triage.ts
 *
 * All @openai/agents dependencies are vi.mock'd — tests are offline.
 * Mock architecture:
 *   - Runner.run is a vi.fn() whose return value is controlled per-test
 *   - withTrace executes its callback synchronously (no actual tracing)
 *   - Agent is a simple class stub
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock @openai/agents before importing the workflow ──────────────────────────

const mockRunnerRun = vi.fn();

vi.mock('@openai/agents', () => {
  class MockAgent {
    name: string;
    constructor(config: { name: string; [key: string]: unknown }) {
      this.name = config.name;
    }
  }

  class MockRunner {
    run = mockRunnerRun;
    constructor(_config?: unknown) {}
  }

  const withTrace = async <T>(_name: string, fn: () => Promise<T>): Promise<T> => fn();

  return { Agent: MockAgent, Runner: MockRunner, withTrace };
});

// Import AFTER mock is established
import {
  runWorkflow,
  WorkflowInput,
  TriageCategory,
} from '../../workflows/openai/customer_support_triage.js';

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Build a mock runner.run result for a plain-text agent. */
function mockTextRun(output: string) {
  return {
    finalOutput: output,
    newItems: [{ rawItem: { role: 'assistant', content: [{ type: 'text', text: output }] } }],
  };
}

/** Build a mock runner.run result for the triage classifier (structured output). */
function mockTriageRun(category: TriageCategory) {
  return {
    finalOutput: { category },
    newItems: [],
  };
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('customer_support_triage workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Billing routing ────────────────────────────────────────────────────────

  it('routes Billing category to billing agent', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Welcome! How can I help?')) // welcomeAgent
      .mockResolvedValueOnce(mockTriageRun('Billing')) // triageClassifier
      .mockResolvedValueOnce(mockTextRun('Here is your invoice help')); // billingAgent

    const result = await runWorkflow({ input_as_text: 'I was charged twice on my card' });

    expect(result.welcomeOutput).toBe('Welcome! How can I help?');
    expect(result.triageCategory).toBe('Billing');
    expect(result.specialistOutput).toBe('Here is your invoice help');

    // runner.run called 3 times: welcome + triage + billing
    expect(mockRunnerRun).toHaveBeenCalledTimes(3);

    // Third call should be to billing agent (name check on first arg)
    const billingCall = mockRunnerRun.mock.calls[2];
    expect(billingCall[0].name).toBe('Billing Agent');
  });

  // ── Technical routing ──────────────────────────────────────────────────────

  it('routes Technical category to technical agent', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hello, I can help!'))
      .mockResolvedValueOnce(mockTriageRun('Technical'))
      .mockResolvedValueOnce(mockTextRun('Let me troubleshoot that for you'));

    const result = await runWorkflow({ input_as_text: 'The app crashes on startup' });

    expect(result.triageCategory).toBe('Technical');
    expect(result.specialistOutput).toBe('Let me troubleshoot that for you');
    const techCall = mockRunnerRun.mock.calls[2];
    expect(techCall[0].name).toBe('Technical Agent');
  });

  // ── Sales routing ──────────────────────────────────────────────────────────

  it('routes Sales category to sales agent', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hi there!'))
      .mockResolvedValueOnce(mockTriageRun('Sales'))
      .mockResolvedValueOnce(mockTextRun('I can walk you through our pricing'));

    const result = await runWorkflow({ input_as_text: 'What plans do you offer?' });

    expect(result.triageCategory).toBe('Sales');
    const salesCall = mockRunnerRun.mock.calls[2];
    expect(salesCall[0].name).toBe('Sales Agent');
  });

  // ── General routing (else branch) ─────────────────────────────────────────

  it('routes General category to general agent', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Good day!'))
      .mockResolvedValueOnce(mockTriageRun('General'))
      .mockResolvedValueOnce(mockTextRun('Here is some general info'));

    const result = await runWorkflow({ input_as_text: 'How do I update my profile?' });

    expect(result.triageCategory).toBe('General');
    const genCall = mockRunnerRun.mock.calls[2];
    expect(genCall[0].name).toBe('General Agent');
  });

  // ── Welcome agent always runs first ───────────────────────────────────────

  it('always runs welcome agent before triage', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hello!'))
      .mockResolvedValueOnce(mockTriageRun('General'))
      .mockResolvedValueOnce(mockTextRun('Done'));

    await runWorkflow({ input_as_text: 'test' });

    const firstCall = mockRunnerRun.mock.calls[0];
    expect(firstCall[0].name).toBe('Welcome Agent');

    const secondCall = mockRunnerRun.mock.calls[1];
    expect(secondCall[0].name).toBe('Triage Classifier');
  });

  // ── Triage runs on original input ─────────────────────────────────────────

  it('passes original input_as_text to triage classifier', async () => {
    const input = 'My invoice amount looks wrong';
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hi!'))
      .mockResolvedValueOnce(mockTriageRun('Billing'))
      .mockResolvedValueOnce(mockTextRun('OK'));

    await runWorkflow({ input_as_text: input });

    const triageCall = mockRunnerRun.mock.calls[1];
    const triageMessages = triageCall[1] as Array<{ role: string; content: unknown[] }>;
    expect(triageMessages[0].content[0]).toMatchObject({ type: 'input_text', text: input });
  });

  // ── Conversation history passed to specialist ─────────────────────────────

  it('includes welcome agent output in conversation history passed to specialist', async () => {
    const welcomeItem = { role: 'assistant', content: [{ type: 'text', text: 'Welcome!' }] };
    mockRunnerRun
      .mockResolvedValueOnce({
        finalOutput: 'Welcome!',
        newItems: [{ rawItem: welcomeItem }],
      })
      .mockResolvedValueOnce(mockTriageRun('Technical'))
      .mockResolvedValueOnce(mockTextRun('Troubleshooting now'));

    await runWorkflow({ input_as_text: 'error 500' });

    const specialistCall = mockRunnerRun.mock.calls[2];
    const history = specialistCall[1] as unknown[];
    // history should include: initial user message + welcome agent's raw item
    expect(history.length).toBe(2);
    expect(history[1]).toEqual(welcomeItem);
  });

  // ── Error: welcome agent returns undefined ────────────────────────────────

  it('throws if welcome agent returns no output', async () => {
    mockRunnerRun.mockResolvedValueOnce({ finalOutput: null, newItems: [] });

    await expect(runWorkflow({ input_as_text: 'hello' })).rejects.toThrow(
      'Welcome agent returned no output'
    );
    expect(mockRunnerRun).toHaveBeenCalledTimes(1);
  });

  // ── Error: triage returns undefined ───────────────────────────────────────

  it('throws if triage classifier returns no output', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hi!'))
      .mockResolvedValueOnce({ finalOutput: null, newItems: [] });

    await expect(runWorkflow({ input_as_text: 'hello' })).rejects.toThrow(
      'Triage classifier returned no output'
    );
    expect(mockRunnerRun).toHaveBeenCalledTimes(2);
  });

  // ── Error: specialist returns undefined ───────────────────────────────────

  it('throws if specialist agent returns no output', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hi!'))
      .mockResolvedValueOnce(mockTriageRun('Sales'))
      .mockResolvedValueOnce({ finalOutput: null, newItems: [] });

    await expect(runWorkflow({ input_as_text: 'buy' })).rejects.toThrow(
      'Sales agent returned no output'
    );
  });

  // ── All four categories round-trip ────────────────────────────────────────

  it.each([
    ['Billing', 'Billing Agent'],
    ['Technical', 'Technical Agent'],
    ['Sales', 'Sales Agent'],
    ['General', 'General Agent'],
  ] as const)('category %s dispatches to %s', async (category, agentName) => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('Hi!'))
      .mockResolvedValueOnce(mockTriageRun(category))
      .mockResolvedValueOnce(mockTextRun(`${category} handled`));

    const result = await runWorkflow({ input_as_text: 'test' });

    expect(result.triageCategory).toBe(category);
    expect(result.specialistOutput).toBe(`${category} handled`);
    expect(mockRunnerRun.mock.calls[2][0].name).toBe(agentName);
  });

  // ── Return shape ──────────────────────────────────────────────────────────

  it('returns all three fields in the WorkflowResult', async () => {
    mockRunnerRun
      .mockResolvedValueOnce(mockTextRun('hello'))
      .mockResolvedValueOnce(mockTriageRun('Billing'))
      .mockResolvedValueOnce(mockTextRun('billing response'));

    const result = await runWorkflow({ input_as_text: 'billing question' });

    expect(result).toHaveProperty('welcomeOutput');
    expect(result).toHaveProperty('triageCategory');
    expect(result).toHaveProperty('specialistOutput');
    expect(typeof result.welcomeOutput).toBe('string');
    expect(typeof result.triageCategory).toBe('string');
    expect(typeof result.specialistOutput).toBe('string');
  });
});
