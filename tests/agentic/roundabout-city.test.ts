import { describe, expect, it } from 'vitest';
import { DecisionRoundabouts } from '../../src/agentic/roundabout-city';
import { ExecutionDistrict } from '../../src/agentic/execution-district';

describe('Roundabout City', () => {
  it('routes risky requests into deny/quarantine lanes', () => {
    const rr = new DecisionRoundabouts();
    const path = rr.route({
      requestId: 'req-risky',
      trustScore: 0.2,
      riskScore: 0.95,
      coherenceScore: 0.3,
      executionRequested: true,
    });

    expect(path[0].stateVector.roundabout).toBe('R0');
    expect(path[0].stateVector.selectedExit).toBe('quarantine_lane');

    const r2 = path.find((s) => s.stateVector.roundabout === 'R2');
    expect(r2?.decisionRecord.action).toBe('DENY');
    expect(r2?.stateVector.selectedExit).toBe('deny_noise_lane');
  });

  it('produces StateVector and DecisionRecord on execution ticket', () => {
    const rr = new DecisionRoundabouts();
    const ticket = rr.createExecutionTicket({
      requestId: 'req-ok',
      trustScore: 0.88,
      riskScore: 0.2,
      coherenceScore: 0.9,
      executionRequested: true,
    });

    expect(ticket.stateVector.requestId).toBe('req-ok');
    expect(ticket.decisionRecord.requestId).toBe('req-ok');
    expect(ticket.decisionRecord.roundabout).toBe('R2');
    expect(ticket.decisionRecord.action).toBe('ALLOW');
  });
});

describe('Execution District', () => {
  it('blocks execution when governance action is not ALLOW', async () => {
    const rr = new DecisionRoundabouts();
    const district = new ExecutionDistrict();

    const ticket = rr.createExecutionTicket({
      requestId: 'req-no',
      trustScore: 0.3,
      riskScore: 0.8,
      coherenceScore: 0.4,
      executionRequested: true,
    });

    const result = await district.execute(
      {
        ticket,
        workOrderId: 'wo-1',
        actionName: 'upload_to_gumroad',
      },
      async () => 'should-not-run'
    );

    expect(result.success).toBe(false);
    expect(result.reason).toContain('Execution blocked');
    expect(district.getAuditLog()).toHaveLength(1);
    expect(district.getAuditLog()[0].allowed).toBe(false);
  });

  it('executes governed ALLOW ticket and writes audit edge', async () => {
    const rr = new DecisionRoundabouts();
    const district = new ExecutionDistrict();

    const ticket = rr.createExecutionTicket({
      requestId: 'req-yes',
      trustScore: 0.9,
      riskScore: 0.18,
      coherenceScore: 0.93,
      executionRequested: true,
    });

    const result = await district.execute(
      {
        ticket,
        workOrderId: 'wo-2',
        actionName: 'publish_dataset_snapshot',
        payload: { shard: '2026-02-21' },
      },
      async (req) => ({ ok: true, action: req.actionName })
    );

    expect(result.success).toBe(true);
    expect((result.output as { ok: boolean }).ok).toBe(true);
    expect(result.auditEdge.allowed).toBe(true);
    expect(result.auditEdge.governanceAction).toBe('ALLOW');
    expect(district.getAuditLog()).toHaveLength(1);
  });
});
