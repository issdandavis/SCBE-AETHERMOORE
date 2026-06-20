import type { ValidationError, WorkflowSpec } from './types';

export function validate(spec: WorkflowSpec): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!spec.id || spec.id.trim() === '') {
    errors.push({ field: 'id', message: 'spec id must not be empty' });
  }

  if (!spec.steps || spec.steps.length === 0) {
    errors.push({ field: 'steps', message: 'steps must not be empty' });
    return errors;
  }

  const seenIds = new Set<string>();
  for (const step of spec.steps) {
    if (seenIds.has(step.id)) {
      errors.push({ step_id: step.id, field: 'id', message: `duplicate step id: ${step.id}` });
    }
    seenIds.add(step.id);

    if (!step.op || step.op.trim() === '') {
      errors.push({ step_id: step.id, field: 'op', message: 'step op must not be empty' });
    }
  }

  return errors;
}
