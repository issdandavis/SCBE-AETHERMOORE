import { describe, expect, it } from 'vitest';
import { buildRubixBrowserPlan, RUBIX_BROWSER_FACES } from '../src/rubix-browser.js';

describe('rubix browser adapter', () => {
  it('builds a closed read-only browser route for inspection tasks', () => {
    const plan = buildRubixBrowserPlan({
      task: 'inspect the pricing page and summarize visible labels',
      permissions: ['observe', 'visual.read', 'dom.read'],
      generatedAt: '2026-05-30T00:00:00.000Z',
    });

    expect(plan.schema_version).toBe('scbe.rubix_browser_plan.v1');
    expect(plan.audit.verdict).toBe('PASS');
    expect(plan.closed_loop).toBe(true);
    expect(plan.route_reversible).toBe(true);
    expect(plan.route.map((move) => `${move.from}->${move.to}`)).toEqual([
      'viewport->dom',
      'dom->memory',
      'memory->viewport',
    ]);
    expect(plan.blocked_moves).toHaveLength(0);
    expect(plan.audit.route_sha256).toMatch(/^[a-f0-9]{64}$/);
  });

  it('holds a side-effectful route when tool permissions are missing', () => {
    const plan = buildRubixBrowserPlan({
      task: 'open the upload page, fill the form, and submit the video',
      permissions: ['observe', 'visual.read', 'dom.read'],
      generatedAt: '2026-05-30T00:00:00.000Z',
    });

    expect(plan.audit.verdict).toBe('HOLD');
    expect(plan.route_reversible).toBe(false);
    expect(plan.demanded_faces).toContain('tool');
    expect(plan.blocked_moves.map((move) => move.to)).toContain('tool');
    expect(plan.cube_projection.fog_of_war).toContain('tool');
  });

  it('opens auth, network, storage, and tool faces only when permissions allow them', () => {
    const plan = buildRubixBrowserPlan({
      task: 'login, read session storage, call the API URL, then click save',
      permissions: [
        'observe',
        'visual.read',
        'dom.read',
        'auth.read',
        'storage.read',
        'network.read',
        'tool.call',
      ],
      generatedAt: '2026-05-30T00:00:00.000Z',
    });

    expect(plan.audit.verdict).toBe('PASS');
    expect(plan.demanded_faces).toEqual([
      'viewport',
      'dom',
      'memory',
      'tool',
      'auth',
      'storage',
      'network',
    ]);
    expect(plan.cube_projection.visible_faces).toEqual(
      expect.arrayContaining(['viewport', 'dom', 'memory', 'tool', 'auth', 'storage', 'network'])
    );
  });

  it('keeps every face on a four-dimensional tesseract coordinate', () => {
    expect(RUBIX_BROWSER_FACES.length).toBeGreaterThanOrEqual(6);
    for (const face of RUBIX_BROWSER_FACES) {
      expect(face.coordinate).toHaveLength(4);
      expect(face.required_permission.length).toBeGreaterThan(0);
    }
  });

  it('rejects empty tasks instead of producing ambiguous routes', () => {
    expect(() => buildRubixBrowserPlan({ task: '   ' })).toThrow(/non-empty task/);
  });
});
