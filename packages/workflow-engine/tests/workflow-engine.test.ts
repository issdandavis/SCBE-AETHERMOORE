import { describe, expect, it } from 'vitest';
import { preview, validate } from '../src/index';
import type { WorkflowSpec } from '../src/index';

function validSpec(): WorkflowSpec {
  return {
    id: 'desktop-open',
    trigger: { kind: 'manual' },
    steps: [
      {
        id: 'open-browser',
        op: 'browser.open',
        args: { url: 'https://example.com' },
      },
      {
        id: 'capture',
        op: 'browser.capture',
        args: { selector: 'body' },
      },
    ],
  };
}

describe('@scbe/workflow-engine', () => {
  it('validates a minimal workflow spec', () => {
    expect(validate(validSpec())).toEqual([]);
  });

  it('reports empty ids, empty step lists, duplicate steps, and empty ops', () => {
    const spec = validSpec();
    spec.id = '';
    spec.steps.push({ id: 'capture', op: '', args: {} });

    expect(validate(spec)).toEqual([
      { field: 'id', message: 'spec id must not be empty' },
      { step_id: 'capture', field: 'id', message: 'duplicate step id: capture' },
      { step_id: 'capture', field: 'op', message: 'step op must not be empty' },
    ]);

    expect(validate({ ...validSpec(), steps: [] })).toEqual([
      { field: 'steps', message: 'steps must not be empty' },
    ]);
  });

  it('previews workflow steps as dry-run local operation requests', () => {
    const requests = preview(validSpec());

    expect(requests).toHaveLength(2);
    expect(requests[0]).toMatchObject({
      schema_version: 'scbe.operation.v1',
      op: 'browser.open',
      request_id: 'preview-desktop-open-open-browser-0',
      origin: { kind: 'workflow', id: 'desktop-open' },
      privacy: 'local_only',
      dry_run: true,
    });
    expect(requests[1]?.request_id).toBe('preview-desktop-open-capture-1');
  });
});
