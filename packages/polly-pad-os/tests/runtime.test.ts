import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { createPollyPadRuntime } from '../src/os/runtime.ts';

function createRuntime() {
  return createPollyPadRuntime({
    now: () => 1_700_000_000_000,
    random: () => 0.123456,
    viewport: { width: 1200, height: 800 },
  });
}

describe('PollyPadRuntime', () => {
  it('lists the complete 82-app desktop registry', () => {
    const runtime = createRuntime();
    const result = runtime.invoke('os', 'listApps');

    assert.equal(result.ok, true);
    assert.equal(result.snapshot.appCount, 82);
    assert.equal(
      result.snapshot.apps.some((app) => app.id === 'multiagent'),
      true
    );
    assert.equal(
      result.snapshot.apps.some((app) => app.id === 'governance'),
      true
    );
    assert.equal(
      result.snapshot.apps.some((app) => app.id === 'layeredabacus'),
      true
    );
    assert.equal(result.snapshot.apps.filter((app) => app.capability.status === 'real').length, 4);
    assert.equal(
      result.snapshot.apps.every((app) => app.capability.goal && app.capability.proof),
      true
    );
  });

  it('keeps the default desktop scoped to real app surfaces', () => {
    const runtime = createRuntime();
    const result = runtime.invoke('os', 'snapshot');

    assert.equal(result.ok, true);
    assert.deepEqual(result.snapshot.desktopIcons.map((icon) => icon.appId).sort(), [
      'browser',
      'layeredabacus',
      'multiagent',
      'terminal',
    ]);
    for (const icon of result.snapshot.desktopIcons) {
      const app = result.snapshot.apps.find((candidate) => candidate.id === icon.appId);
      assert.equal(app?.capability.status, 'real');
    }
  });

  it('opens, moves, resizes, and snapshots app windows without a browser', () => {
    const runtime = createRuntime();
    const open = runtime.invoke('terminal', 'open', { data: { cwd: '/repo' } });

    assert.equal(open.ok, true);
    assert.match(open.windowId ?? '', /^win_1_terminal_/);
    assert.equal(open.snapshot.activeWindowId, open.windowId);
    assert.equal(open.snapshot.windows[0].appId, 'terminal');
    assert.deepEqual(open.snapshot.windows[0].data, { cwd: '/repo' });

    const moved = runtime.invoke('terminal', 'move', { x: 42, y: 84 });
    assert.equal(moved.ok, true);
    assert.equal(moved.snapshot.windows[0].x, 42);
    assert.equal(moved.snapshot.windows[0].y, 84);

    const resized = runtime.invoke('terminal', 'resize', { width: 900, height: 600 });
    assert.equal(resized.snapshot.windows[0].width, 900);
    assert.equal(resized.snapshot.windows[0].height, 600);
  });

  it('keeps singleton apps to one focused window', () => {
    const runtime = createRuntime();
    const first = runtime.invoke('settings', 'open');
    const second = runtime.invoke('settings', 'open');

    assert.equal(first.ok, true);
    assert.equal(second.ok, true);
    assert.equal(first.windowId, second.windowId);
    assert.equal(second.snapshot.windows.filter((window) => window.appId === 'settings').length, 1);
  });

  it('supports system-level theme, notification, start-menu, and close operations', () => {
    const runtime = createRuntime();
    const opened = runtime.invoke('calculator', 'open');
    assert.equal(opened.ok, true);

    assert.equal(runtime.invoke('os', 'setTheme', { theme: 'purple' }).snapshot.theme, 'purple');
    assert.equal(runtime.invoke('os', 'setStartMenu', { open: true }).snapshot.startMenuOpen, true);

    const notified = runtime.invoke('os', 'notify', {
      notification: {
        title: 'Route complete',
        message: 'Agent operation finished',
        type: 'success',
      },
    });
    assert.equal(notified.snapshot.notifications.length, 1);
    assert.equal(notified.snapshot.notifications[0].timestamp, 1_700_000_000_000);

    const closed = runtime.invoke('calculator', 'close');
    assert.equal(closed.ok, true);
    assert.equal(closed.snapshot.windows.length, 0);
  });

  it('lets agents calculate with layered abacus chunks and prime rows', () => {
    const runtime = createRuntime();
    const opened = runtime.invoke('layeredabacus', 'open');
    assert.equal(opened.ok, true);

    const tens = runtime.invoke('layeredabacus', 'abacusSetRow', {
      layerId: 'decimal',
      rowId: 'tens',
      count: 4,
    });
    assert.equal(tens.ok, true);

    const prime = runtime.invoke('layeredabacus', 'abacusSetRow', {
      layerId: 'prime',
      rowId: 'p7',
      count: 3,
    });
    assert.equal(prime.ok, true);

    const data = prime.snapshot.windows[0].data as {
      totals: { total: number; layers: Array<{ id: string; total: number }> };
    };
    assert.equal(data.totals.total, 61);
    assert.equal(data.totals.layers.find((layer) => layer.id === 'decimal')?.total, 40);
    assert.equal(data.totals.layers.find((layer) => layer.id === 'prime')?.total, 21);

    const custom = runtime.invoke('layeredabacus', 'abacusAddLayer', {
      layerId: 'route-cost',
      name: 'Route Cost Tokens',
      rows: [{ id: 'gate', label: 'gate', value: 8, count: 2 }],
    });
    assert.equal(custom.ok, true);
    const customData = custom.snapshot.windows[0].data as { totals: { total: number } };
    assert.equal(customData.totals.total, 77);
  });

  it('fails closed on unknown apps or invalid operation arguments', () => {
    const runtime = createRuntime();

    const missing = runtime.invoke('missing-app', 'open');
    assert.equal(missing.ok, false);
    assert.match(missing.error ?? '', /Unknown app/);

    runtime.invoke('terminal', 'open');
    const invalidMove = runtime.invoke('terminal', 'move', { x: Number.NaN, y: 1 });
    assert.equal(invalidMove.ok, false);
    assert.match(invalidMove.error ?? '', /x must be a finite number/);

    const wrongSurface = runtime.invoke('terminal', 'abacusSetRow', {
      rowId: 'tens',
      count: 1,
    });
    assert.equal(wrongSurface.ok, false);
    assert.match(wrongSurface.error ?? '', /only supported by layeredabacus/);
  });
});
