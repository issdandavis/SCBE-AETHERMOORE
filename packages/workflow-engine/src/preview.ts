import type { OperationRequest, WorkflowSpec } from './types';
import { SCHEMA_VERSION } from './types';

export function preview(spec: WorkflowSpec): OperationRequest[] {
  return spec.steps.map(
    (step, idx): OperationRequest => ({
      schema_version: SCHEMA_VERSION,
      op: step.op,
      args: step.args,
      request_id: `preview-${spec.id}-${step.id}-${idx}`,
      origin: { kind: 'workflow', id: spec.id },
      privacy: 'local_only',
      dry_run: true,
    })
  );
}
