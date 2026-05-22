export const SCHEMA_VERSION = 'scbe.operation.v1' as const;

export interface OperationRequest {
  schema_version: typeof SCHEMA_VERSION;
  op: string;
  args: Record<string, unknown>;
  request_id: string;
  origin: { kind: 'app' | 'workflow' | 'agent'; id: string };
  workspace?: { id: string; root: string };
  privacy: 'local_only' | 'external_api';
  budget_cents?: number;
  dry_run?: boolean;
}

export type DecisionKind = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
export type ZoneKind = 'GREEN' | 'YELLOW' | 'RED';

export interface OperationDecision {
  request_id: string;
  decision: DecisionKind;
  zone: ZoneKind;
  reason: string;
  policy: string;
  latency_ms: number;
}

export interface OperationResult {
  request_id: string;
  ok: boolean;
  output?: Record<string, unknown>;
  error?: { code: string; message: string };
  artifacts?: { kind: string; ref: string }[];
  duration_ms: number;
}

export interface AuditRecord {
  schema_version: typeof SCHEMA_VERSION;
  request_id: string;
  ts_request: string;
  op: string;
  origin: OperationRequest['origin'];
  privacy: string;
  decision: OperationDecision;
  ts_result?: string;
  result_summary?: {
    ok: boolean;
    error_code?: string;
    artifact_refs?: string[];
    output_shape?: string;
  };
}

export interface WorkflowStep {
  id: string;
  when?: string;
  op: string;
  args: Record<string, unknown>;
}

export interface WorkflowSpec {
  id: string;
  trigger: {
    kind: 'manual' | 'event' | 'schedule';
    match?: Record<string, unknown>;
  };
  steps: WorkflowStep[];
}

export interface ValidationError {
  step_id?: string;
  field: string;
  message: string;
}

export interface OperationClient {
  run(req: OperationRequest): Promise<OperationResult>;
}
