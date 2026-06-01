import { describe, expect, it } from 'vitest';
import {
  createAiCommPacket,
  createBridgeEndpoint,
  createBridgeMessage,
  planBridgeRoute,
  summarizeBridgePlan,
} from '../src/multi-bridge.js';
import { startAgentBusServer } from '../src/index.js';

describe('multi bridge routing', () => {
  it('allows local AI-to-AI bridge packets without a human gate', () => {
    const message = createBridgeMessage({
      created_at: '2026-05-31T20:00:00.000Z',
      from: 'codex',
      to: ['claude'],
      subject: 'handoff',
      body: 'Implement the targeted agent bus tests and report command output.',
      tags: ['agent-comm'],
    });
    const endpoint = createBridgeEndpoint({
      kind: 'ai_agent',
      provider: 'claude',
      label: 'Claude local lane',
      agent_id: 'claude',
      trust: 'local_private',
    });

    const plan = planBridgeRoute('cross-ai handoff', message, [endpoint], {
      generated_at: '2026-05-31T20:00:01.000Z',
    });

    expect(plan.route.decision).toBe('ALLOW');
    expect(plan.route.required_human_gate).toBe(false);
    expect(plan.governance.privacy).toBe('local_only');
    expect(plan.audit.endpoint_count).toBe(1);
    expect(plan.route.hops[0]).toMatchObject({
      from: 'codex',
      to: endpoint.id,
      provider: 'claude',
      action: 'normalize',
    });
  });

  it('denies credential-bearing outbound mail before delivery', () => {
    const plan = planBridgeRoute(
      'send support email',
      {
        created_at: '2026-05-31T20:10:00.000Z',
        from: 'user',
        to: ['vendor@example.com'],
        subject: 'debug token',
        body: 'api_key = "sk-this-should-not-leave-the-machine"',
      },
      [
        {
          kind: 'mail',
          provider: 'gmail',
          label: 'External Gmail recipient',
          address: 'vendor@example.com',
          trust: 'external',
          direction: 'outbound',
        },
      ],
      { generated_at: '2026-05-31T20:10:01.000Z' }
    );

    expect(plan.route.decision).toBe('DENY');
    expect(plan.governance.blocked_actions).toContain('deliver');
    expect(plan.governance.findings.map((finding) => finding.code)).toContain('api_token_literal');
  });

  it('quarantines mail with attachments for user review', () => {
    const plan = planBridgeRoute(
      'route inbox item to Apollo',
      {
        created_at: '2026-05-31T20:20:00.000Z',
        from: 'proton:inbox',
        to: ['apollo'],
        subject: 'contract attachment',
        body: 'Please review the attached draft.',
        attachments: [{ name: 'draft.pdf', bytes: 2048, sha256: 'abc123' }],
      },
      [
        {
          kind: 'mail',
          provider: 'proton',
          label: 'Proton inbox',
          trust: 'user_private',
          direction: 'inbound',
        },
        {
          kind: 'ai_agent',
          provider: 'apollo',
          label: 'Apollo triage',
          agent_id: 'apollo',
          trust: 'local_private',
        },
      ],
      { generated_at: '2026-05-31T20:20:01.000Z' }
    );

    expect(plan.route.decision).toBe('QUARANTINE');
    expect(plan.route.required_human_gate).toBe(true);
    expect(plan.governance.findings.map((finding) => finding.code)).toContain(
      'attachments_present'
    );
  });

  it('creates standard AI communication packets for cross-lane handoff', () => {
    const packet = createAiCommPacket({
      created_at: '2026-05-31T20:30:00.000Z',
      sender: 'codex',
      recipient: 'gemini',
      intent: 'review',
      branch: 'feat/runtime-gate-durable-state',
      task_id: 'agent-bus-multi-bridge',
      summary: 'Review the bridge route contract for user-facing mail and AI agent lanes.',
      proof: ['packages/agent-bus/src/multi-bridge.ts'],
      next_action: 'Check whether the route decisions are easy to explain to users.',
      risk: 'medium',
      tests_requested: ['npm --prefix packages/agent-bus test'],
    });

    expect(packet.packet_id).toMatch(/^aid-/);
    expect(packet.repo).toBe('SCBE-AETHERMOORE');
    expect(packet.gates.governance_packet).toBe(true);
    expect(packet.gates.tests_requested).toContain('npm --prefix packages/agent-bus test');
  });

  it('summarizes bridge plans for operator surfaces', () => {
    const plan = planBridgeRoute(
      'local note',
      {
        created_at: '2026-05-31T20:40:00.000Z',
        from: 'codex',
        to: ['filesystem'],
        subject: 'save packet',
        body: 'Store this packet for local review.',
      },
      [
        {
          kind: 'file',
          provider: 'filesystem',
          label: 'local packet folder',
          trust: 'local_private',
        },
      ],
      { generated_at: '2026-05-31T20:40:01.000Z' }
    );

    expect(summarizeBridgePlan(plan)).toContain('ALLOW: codex -> local packet folder');
  });

  it('serves bridge route plans over the agent-bus HTTP surface', async () => {
    const server = await startAgentBusServer({ port: 18787 });
    try {
      const response = await fetch('http://127.0.0.1:18787/v1/bridge/plan', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          intent: 'mail triage',
          message: {
            created_at: '2026-05-31T20:50:00.000Z',
            from: 'proton:inbox',
            to: ['apollo'],
            subject: 'quick triage',
            body: 'Summarize and tag this inbound message.',
          },
          endpoints: [
            {
              kind: 'ai_agent',
              provider: 'apollo',
              label: 'Apollo local triage',
              trust: 'local_private',
            },
          ],
          options: { generated_at: '2026-05-31T20:50:01.000Z' },
        }),
      });
      const payload = (await response.json()) as {
        ok: boolean;
        plan: { route: { decision: string } };
      };

      expect(response.status).toBe(200);
      expect(payload.ok).toBe(true);
      expect(payload.plan.route.decision).toBe('ALLOW');
    } finally {
      await server.close();
    }
  });
});
