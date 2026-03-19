/**
 * AetherMore Execution District
 *
 * Executes tasks only when governance tickets are ALLOW.
 * Each execution appends an immutable audit edge.
 *
 * @module agentic/execution-district
 */

import { DecisionRecord, GovernanceAction, StateVector } from './roundabout-city';

export interface ExecutionRequest {
  ticket: {
    stateVector: StateVector;
    decisionRecord: DecisionRecord;
  };
  workOrderId: string;
  actionName: string;
  payload?: Record<string, unknown>;
}

export interface ExecutionResult {
  success: boolean;
  output?: unknown;
  reason?: string;
  auditEdge: AuditEdge;
}

export interface AuditEdge {
  workOrderId: string;
  actionName: string;
  requestId: string;
  governanceAction: GovernanceAction;
  allowed: boolean;
  reason: string;
  timestamp: number;
  signature: string;
}

export type ExecutionFn = (req: ExecutionRequest) => Promise<unknown>;

export class ExecutionDistrict {
  private readonly maxTicketAgeMs: number;
  private readonly auditLog: AuditEdge[] = [];

  constructor(maxTicketAgeMs = 5 * 60 * 1000) {
    this.maxTicketAgeMs = maxTicketAgeMs;
  }

  public getAuditLog(): AuditEdge[] {
    return [...this.auditLog];
  }

  public async execute(request: ExecutionRequest, fn: ExecutionFn): Promise<ExecutionResult> {
    const { stateVector, decisionRecord } = request.ticket;
    const now = Date.now();

    const tooOld = now - decisionRecord.timestamp > this.maxTicketAgeMs;
    if (tooOld) {
      return this.denyResult(
        request,
        decisionRecord,
        'Execution blocked: stale governance ticket.'
      );
    }

    if (decisionRecord.action !== 'ALLOW') {
      return this.denyResult(
        request,
        decisionRecord,
        `Execution blocked: governance action is ${decisionRecord.action}.`
      );
    }

    try {
      const output = await fn(request);
      const edge: AuditEdge = {
        workOrderId: request.workOrderId,
        actionName: request.actionName,
        requestId: stateVector.requestId,
        governanceAction: decisionRecord.action,
        allowed: true,
        reason: decisionRecord.reason,
        timestamp: now,
        signature: decisionRecord.signature,
      };
      this.auditLog.push(edge);
      return { success: true, output, auditEdge: edge };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'unknown execution error';
      const edge: AuditEdge = {
        workOrderId: request.workOrderId,
        actionName: request.actionName,
        requestId: stateVector.requestId,
        governanceAction: decisionRecord.action,
        allowed: false,
        reason: `Execution error: ${message}`,
        timestamp: now,
        signature: decisionRecord.signature,
      };
      this.auditLog.push(edge);
      return { success: false, reason: edge.reason, auditEdge: edge };
    }
  }

  private denyResult(
    request: ExecutionRequest,
    decisionRecord: DecisionRecord,
    reason: string
  ): ExecutionResult {
    const edge: AuditEdge = {
      workOrderId: request.workOrderId,
      actionName: request.actionName,
      requestId: request.ticket.stateVector.requestId,
      governanceAction: decisionRecord.action,
      allowed: false,
      reason,
      timestamp: Date.now(),
      signature: decisionRecord.signature,
    };
    this.auditLog.push(edge);
    return { success: false, reason, auditEdge: edge };
  }
}
