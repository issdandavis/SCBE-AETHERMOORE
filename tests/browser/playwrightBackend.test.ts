/**
 * @file playwrightBackend.test.ts
 * @module tests/browser/playwrightBackend
 *
 * Tests for PlaywrightBackend — the real browser adapter.
 *
 * Strategy:
 *   - We inject a mock launchFn so no real browser is needed.
 *   - The mock mirrors Playwright's API surface: Browser → Context → Page.
 *   - We verify every BrowserBackend method delegates correctly.
 *   - We verify the DOM observation script mapping.
 *   - We verify dialog capture, error handling, and lifecycle.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PlaywrightBackend, createPlaywrightBackend } from '../../src/browser/playwright-backend.js';
import type { BrowserSessionConfig, PageObservation, DOMElementState } from '../../src/browser/types.js';

// ─────────────────────────────────────────────────────────────────────────────
// Mock Playwright objects
// ─────────────────────────────────────────────────────────────────────────────

function createMockPage() {
  const dialogHandlers: Array<(d: unknown) => void> = [];
  let currentUrl = 'about:blank';
  let currentTitle = 'Blank';

  const page = {
    goto: vi.fn(async (url: string) => {
      currentUrl = url;
      currentTitle = `Page: ${url}`;
    }),
    url: () => currentUrl,
    title: async () => currentTitle,
    click: vi.fn(async () => {}),
    fill: vi.fn(async () => {}),
    type: vi.fn(async () => {}),
    evaluate: vi.fn(async (script: string | Function, ...args: unknown[]) => {
      // Return mock DOM observation by default
      if (typeof script === 'string' && script.includes('interactiveElements')) {
        return {
          url: currentUrl,
          title: currentTitle,
          readyState: 'complete',
          viewport: { width: 1280, height: 720 },
          scroll: { x: 0, y: 0 },
          interactiveElements: [
            {
              tagName: 'button',
              id: 'submit',
              classList: ['btn', 'primary'],
              textContent: 'Submit',
              bounds: { x: 100, y: 200, width: 120, height: 40 },
              visible: true,
              interactive: true,
              dataAttributes: {},
            },
          ],
          forms: [
            {
              identifier: 'login-form',
              action: '/login',
              method: 'POST',
              fields: [
                {
                  name: 'username',
                  type: 'text',
                  value: 'alice',
                  required: true,
                  sensitivity: 'none',
                },
                {
                  name: 'password',
                  type: 'password',
                  value: '***',
                  required: true,
                  sensitivity: 'password',
                },
              ],
              hasSensitiveFields: true,
              sensitiveFieldTypes: ['password'],
            },
          ],
          dialogs: [],
        };
      }
      // For element screenshot bounds
      if (typeof script === 'string' && script.includes('getBoundingClientRect')) {
        return { x: 10, y: 20, width: 100, height: 50 };
      }
      // For scroll-to-element
      if (typeof script === 'string' && script.includes('scrollIntoView')) {
        return undefined;
      }
      // Generic executeScript
      return 42;
    }),
    screenshot: vi.fn(async () => Buffer.from('fake-png-data')),
    goBack: vi.fn(async () => {}),
    goForward: vi.fn(async () => {}),
    reload: vi.fn(async () => {}),
    keyboard: { press: vi.fn(async () => {}) },
    mouse: {
      wheel: vi.fn(async () => {}),
      move: vi.fn(async () => {}),
    },
    selectOption: vi.fn(async () => []),
    setInputFiles: vi.fn(async () => {}),
    hover: vi.fn(async () => {}),
    waitForSelector: vi.fn(async () => {}),
    waitForTimeout: vi.fn(async () => {}),
    waitForLoadState: vi.fn(async () => {}),
    on: vi.fn((event: string, handler: (...args: unknown[]) => void) => {
      if (event === 'dialog') dialogHandlers.push(handler);
    }),
    off: vi.fn(),
    isClosed: vi.fn(() => false),
    context: vi.fn(),
    close: vi.fn(async () => {}),

    // Test helpers
    _simulateDialog(type: string, message: string, defaultValue?: string) {
      for (const h of dialogHandlers) {
        h({
          type: () => type,
          message: () => message,
          defaultValue: () => defaultValue || '',
        });
      }
    },
  };

  return page;
}

function createMockContext(page: ReturnType<typeof createMockPage>) {
  return {
    newPage: vi.fn(async () => page),
    close: vi.fn(async () => {}),
  };
}

function createMockBrowser(context: ReturnType<typeof createMockContext>) {
  return {
    newContext: vi.fn(async () => context),
    close: vi.fn(async () => {}),
    isConnected: vi.fn(() => true),
  };
}

function createMockLaunchFn() {
  const page = createMockPage();
  const context = createMockContext(page);
  const browser = createMockBrowser(context);
  const launchFn = vi.fn(async () => browser);
  return { launchFn, browser, context, page };
}

const DEFAULT_SESSION_CONFIG: BrowserSessionConfig = {
  sessionId: 'test-session-001',
  agentId: 'agent-001',
  tongue: 'KO',
  browserType: 'chromium',
  headless: true,
  viewport: { width: 1280, height: 720 },
  timeout: 30_000,
};

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('PlaywrightBackend', () => {
  let mocks: ReturnType<typeof createMockLaunchFn>;
  let backend: PlaywrightBackend;

  beforeEach(async () => {
    mocks = createMockLaunchFn();
    backend = new PlaywrightBackend({ launchFn: mocks.launchFn as any });
  });

  // ── A. Lifecycle ─────────────────────────────────────────────────────

  describe('A – Lifecycle', () => {
    it('A1: initialize launches browser with correct config', async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);

      expect(mocks.launchFn).toHaveBeenCalledWith(
        expect.objectContaining({ headless: true })
      );
      expect(mocks.browser.newContext).toHaveBeenCalledWith(
        expect.objectContaining({
          viewport: { width: 1280, height: 720 },
        })
      );
      expect(mocks.context.newPage).toHaveBeenCalled();
      expect(backend.isConnected()).toBe(true);
    });

    it('A2: isConnected returns false before initialize', () => {
      expect(backend.isConnected()).toBe(false);
    });

    it('A3: close tears down browser, context, and page', async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
      await backend.close();

      expect(mocks.page.close).toHaveBeenCalled();
      expect(mocks.context.close).toHaveBeenCalled();
      expect(mocks.browser.close).toHaveBeenCalled();
      expect(backend.isConnected()).toBe(false);
    });

    it('A4: close is safe to call multiple times', async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
      await backend.close();
      await backend.close(); // should not throw
      expect(backend.isConnected()).toBe(false);
    });

    it('A5: methods throw before initialize', async () => {
      await expect(backend.navigate('https://example.com')).rejects.toThrow(
        /not initialized/i
      );
      await expect(backend.click('#btn')).rejects.toThrow(/not initialized/i);
      await expect(backend.type('#input', 'text')).rejects.toThrow(
        /not initialized/i
      );
      await expect(backend.observe()).rejects.toThrow(/not initialized/i);
    });

    it('A6: initialize passes proxy config when provided', async () => {
      const configWithProxy = {
        ...DEFAULT_SESSION_CONFIG,
        proxy: { server: 'http://proxy:8080', username: 'user', password: 'pass' },
      };
      await backend.initialize(configWithProxy);

      expect(mocks.browser.newContext).toHaveBeenCalledWith(
        expect.objectContaining({
          proxy: { server: 'http://proxy:8080', username: 'user', password: 'pass' },
        })
      );
    });

    it('A7: initialize passes userAgent when provided', async () => {
      const configWithUA = {
        ...DEFAULT_SESSION_CONFIG,
        userAgent: 'SCBE-CrawlAgent/1.0',
      };
      await backend.initialize(configWithUA);

      expect(mocks.browser.newContext).toHaveBeenCalledWith(
        expect.objectContaining({ userAgent: 'SCBE-CrawlAgent/1.0' })
      );
    });
  });

  // ── B. Navigation ────────────────────────────────────────────────────

  describe('B – Navigation', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('B1: navigate calls page.goto with correct URL', async () => {
      await backend.navigate('https://example.com');
      expect(mocks.page.goto).toHaveBeenCalledWith('https://example.com', {
        waitUntil: 'domcontentloaded',
        timeout: 30_000,
      });
    });

    it('B2: navigate passes custom waitUntil and timeout', async () => {
      await backend.navigate('https://example.com', {
        waitUntil: 'networkidle',
        timeout: 5_000,
      });
      expect(mocks.page.goto).toHaveBeenCalledWith('https://example.com', {
        waitUntil: 'networkidle',
        timeout: 5_000,
      });
    });
  });

  // ── C. Click ─────────────────────────────────────────────────────────

  describe('C – Click', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('C1: click forwards selector to page.click', async () => {
      await backend.click('#submit-btn');
      expect(mocks.page.click).toHaveBeenCalledWith('#submit-btn', undefined);
    });

    it('C2: click passes position option', async () => {
      await backend.click('#area', { position: { x: 50, y: 25 } });
      expect(mocks.page.click).toHaveBeenCalledWith('#area', {
        position: { x: 50, y: 25 },
      });
    });
  });

  // ── D. Type ──────────────────────────────────────────────────────────

  describe('D – Type', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('D1: type forwards text to page.type', async () => {
      await backend.type('#input', 'hello');
      expect(mocks.page.type).toHaveBeenCalledWith('#input', 'hello', {
        delay: undefined,
      });
    });

    it('D2: type with clear calls page.fill first', async () => {
      await backend.type('#input', 'new value', { clear: true });
      expect(mocks.page.fill).toHaveBeenCalledWith('#input', '');
      expect(mocks.page.type).toHaveBeenCalledWith('#input', 'new value', {
        delay: undefined,
      });
    });

    it('D3: type passes delay option', async () => {
      await backend.type('#input', 'slow', { delay: 100 });
      expect(mocks.page.type).toHaveBeenCalledWith('#input', 'slow', {
        delay: 100,
      });
    });
  });

  // ── E. Scroll ────────────────────────────────────────────────────────

  describe('E – Scroll', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('E1: scroll by delta uses mouse.wheel', async () => {
      await backend.scroll({ delta: { x: 0, y: 500 } });
      expect(mocks.page.mouse.wheel).toHaveBeenCalledWith(0, 500);
    });

    it('E2: scroll to selector uses evaluate with scrollIntoView', async () => {
      await backend.scroll({ selector: '#footer' });
      expect(mocks.page.evaluate).toHaveBeenCalledWith(
        expect.stringContaining('scrollIntoView'),
        ['#footer']
      );
    });

    it('E3: scroll with no options defaults to delta y=300', async () => {
      await backend.scroll({});
      expect(mocks.page.mouse.wheel).toHaveBeenCalledWith(0, 300);
    });
  });

  // ── F. Execute Script ────────────────────────────────────────────────

  describe('F – Execute Script', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('F1: executeScript delegates to page.evaluate', async () => {
      const result = await backend.executeScript<number>('1 + 1');
      expect(mocks.page.evaluate).toHaveBeenCalledWith('1 + 1');
      expect(result).toBe(42); // our mock returns 42
    });

    it('F2: executeScript passes args', async () => {
      await backend.executeScript('fn(a)', ['arg1']);
      expect(mocks.page.evaluate).toHaveBeenCalledWith('fn(a)', 'arg1');
    });
  });

  // ── G. Screenshot ────────────────────────────────────────────────────

  describe('G – Screenshot', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('G1: screenshot returns Buffer', async () => {
      const buf = await backend.screenshot();
      expect(Buffer.isBuffer(buf)).toBe(true);
      expect(mocks.page.screenshot).toHaveBeenCalledWith({ fullPage: false });
    });

    it('G2: fullPage screenshot passes option', async () => {
      await backend.screenshot({ fullPage: true });
      expect(mocks.page.screenshot).toHaveBeenCalledWith({ fullPage: true });
    });

    it('G3: element screenshot evaluates bounds then clips', async () => {
      await backend.screenshot({ selector: '#hero' });
      // First call is the bounds evaluation
      expect(mocks.page.evaluate).toHaveBeenCalledWith(
        expect.stringContaining('getBoundingClientRect'),
        ['#hero']
      );
      // Then screenshot with clip
      expect(mocks.page.screenshot).toHaveBeenCalledWith({
        clip: { x: 10, y: 20, width: 100, height: 50 },
      });
    });
  });

  // ── H. Observe (DOM Extraction) ──────────────────────────────────────

  describe('H – Observe', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('H1: observe returns PageObservation with correct shape', async () => {
      await backend.navigate('https://example.com');
      const obs = await backend.observe();

      expect(obs.url).toBe('https://example.com');
      expect(obs.title).toBe('Page: https://example.com');
      expect(obs.readyState).toBe('complete');
      expect(obs.viewport).toEqual({ width: 1280, height: 720 });
      expect(obs.timestamp).toBeGreaterThan(0);
      expect(obs.loadTime).toBeGreaterThanOrEqual(0);
    });

    it('H2: observe returns interactive elements with correct fields', async () => {
      await backend.navigate('https://example.com');
      const obs = await backend.observe();

      expect(obs.interactiveElements.length).toBe(1);
      const btn = obs.interactiveElements[0];
      expect(btn.tagName).toBe('button');
      expect(btn.id).toBe('submit');
      expect(btn.classList).toEqual(['btn', 'primary']);
      expect(btn.textContent).toBe('Submit');
      expect(btn.bounds).toEqual({ x: 100, y: 200, width: 120, height: 40 });
      expect(btn.visible).toBe(true);
      expect(btn.interactive).toBe(true);
      expect(btn.dataAttributes).toEqual({});
    });

    it('H3: observe returns forms with sensitive field detection', async () => {
      await backend.navigate('https://example.com');
      const obs = await backend.observe();

      expect(obs.forms.length).toBe(1);
      const form = obs.forms[0];
      expect(form.identifier).toBe('login-form');
      expect(form.action).toBe('/login');
      expect(form.method).toBe('POST');
      expect(form.hasSensitiveFields).toBe(true);
      expect(form.sensitiveFieldTypes).toContain('password');
      expect(form.fields.length).toBe(2);

      const pwField = form.fields.find((f) => f.name === 'password');
      expect(pwField?.sensitivity).toBe('password');
      expect(pwField?.value).toBe('***'); // masked
    });

    it('H4: observe captures loadTime from navigation', async () => {
      await backend.navigate('https://example.com');
      // Small delay to ensure loadTime > 0
      const obs = await backend.observe();
      expect(obs.loadTime).toBeGreaterThanOrEqual(0);
    });
  });

  // ── I. Dialog Capture ────────────────────────────────────────────────

  describe('I – Dialog Capture', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('I1: dialogs captured via page event are included in observe()', async () => {
      // Simulate a dialog event
      mocks.page._simulateDialog('alert', 'Are you sure?');

      const obs = await backend.observe();
      expect(obs.dialogs.length).toBe(1);
      expect(obs.dialogs[0]).toEqual({
        type: 'alert',
        message: 'Are you sure?',
        defaultValue: undefined,
      });
    });

    it('I2: dialogs are drained after observe()', async () => {
      mocks.page._simulateDialog('confirm', 'Delete?');

      const obs1 = await backend.observe();
      expect(obs1.dialogs.length).toBe(1);

      const obs2 = await backend.observe();
      expect(obs2.dialogs.length).toBe(0); // drained
    });

    it('I3: multiple dialogs accumulate', async () => {
      mocks.page._simulateDialog('alert', 'First');
      mocks.page._simulateDialog('prompt', 'Enter name', 'default');

      const obs = await backend.observe();
      expect(obs.dialogs.length).toBe(2);
      expect(obs.dialogs[0].type).toBe('alert');
      expect(obs.dialogs[1].type).toBe('prompt');
      expect(obs.dialogs[1].defaultValue).toBe('default');
    });
  });

  // ── J. Factory ───────────────────────────────────────────────────────

  describe('J – Factory', () => {
    it('J1: createPlaywrightBackend returns PlaywrightBackend instance', () => {
      const b = createPlaywrightBackend({ launchFn: mocks.launchFn as any });
      expect(b).toBeInstanceOf(PlaywrightBackend);
    });

    it('J2: createPlaywrightBackend with no args returns instance', () => {
      const b = createPlaywrightBackend();
      expect(b).toBeInstanceOf(PlaywrightBackend);
    });
  });

  // ── K. Integration with BrowserAgent ─────────────────────────────────

  describe('K – BrowserAgent Integration', () => {
    it('K1: PlaywrightBackend satisfies BrowserBackend interface', async () => {
      // Type-level check — if this compiles, the interface is satisfied
      const b: import('../../src/browser/agent.js').BrowserBackend = backend;
      expect(typeof b.initialize).toBe('function');
      expect(typeof b.navigate).toBe('function');
      expect(typeof b.click).toBe('function');
      expect(typeof b.type).toBe('function');
      expect(typeof b.scroll).toBe('function');
      expect(typeof b.executeScript).toBe('function');
      expect(typeof b.screenshot).toBe('function');
      expect(typeof b.observe).toBe('function');
      expect(typeof b.close).toBe('function');
      expect(typeof b.isConnected).toBe('function');
    });

    it('K2: backend works with createBrowserAgent', async () => {
      // Verify we can construct an agent with this backend
      const { createBrowserAgent } = await import('../../src/browser/agent.js');
      const agent = createBrowserAgent({
        agentId: 'test-agent',
        tongue: 'KO',
        backend,
      });
      expect(agent.agentId).toBe('test-agent');
      expect(agent.tongue).toBe('KO');
    });

    it('K3: full session lifecycle through BrowserAgent', async () => {
      const { createBrowserAgent } = await import('../../src/browser/agent.js');
      const agent = createBrowserAgent({
        agentId: 'lifecycle-agent',
        tongue: 'KO',
        backend,
      });

      await agent.startSession('https://example.com');

      // Get observation
      const obs = await agent.getObservation();
      expect(obs.page.url).toBe('https://example.com');
      expect(obs.page.interactiveElements.length).toBe(1);

      // Execute a click — governance may ALLOW or DENY based on risk
      const result = await agent.click('#submit');
      expect(typeof result.success).toBe('boolean');
      expect(typeof result.duration).toBe('number');

      // End session
      const summary = await agent.endSession();
      expect(summary).not.toBeNull();
      expect(summary!.agentId).toBe('lifecycle-agent');
      expect(summary!.statistics.actionCount).toBeGreaterThanOrEqual(0);
    });
  });

  // ── L. Error Handling ────────────────────────────────────────────────

  describe('L – Error Handling', () => {
    beforeEach(async () => {
      await backend.initialize(DEFAULT_SESSION_CONFIG);
    });

    it('L1: navigate propagates page.goto errors', async () => {
      mocks.page.goto.mockRejectedValueOnce(new Error('net::ERR_CONNECTION_REFUSED'));
      await expect(backend.navigate('https://bad.example.com')).rejects.toThrow(
        'net::ERR_CONNECTION_REFUSED'
      );
    });

    it('L2: click propagates selector-not-found errors', async () => {
      mocks.page.click.mockRejectedValueOnce(
        new Error('Timeout 30000ms exceeded waiting for selector "#missing"')
      );
      await expect(backend.click('#missing')).rejects.toThrow(/selector/i);
    });

    it('L3: isConnected returns false when browser disconnects', async () => {
      mocks.browser.isConnected.mockReturnValue(false);
      expect(backend.isConnected()).toBe(false);
    });
  });

  // ── M. Launch Options ────────────────────────────────────────────────

  describe('M – Launch Options', () => {
    it('M1: custom launch options are passed through', async () => {
      const customBackend = new PlaywrightBackend({
        launchFn: mocks.launchFn as any,
        launchOptions: { slowMo: 100, args: ['--no-sandbox'] },
      });
      await customBackend.initialize(DEFAULT_SESSION_CONFIG);

      expect(mocks.launchFn).toHaveBeenCalledWith(
        expect.objectContaining({
          headless: true,
          slowMo: 100,
          args: ['--no-sandbox'],
        })
      );
    });

    it('M2: block resource types config is accepted', () => {
      const b = new PlaywrightBackend({
        launchFn: mocks.launchFn as any,
        blockResourceTypes: ['image', 'stylesheet', 'font'],
      });
      expect(b).toBeInstanceOf(PlaywrightBackend);
    });
  });

  // ── N. CrawlRunner Compatibility ─────────────────────────────────────

  describe('N – CrawlRunner Compatibility', () => {
    it('N1: backend can be passed as CrawlAgentBrowserConfig.backend', async () => {
      // Type check — verifying the interface is compatible
      const config: import('../../src/fleet/crawl-runner.js').CrawlAgentBrowserConfig = {
        agentId: 'crawl-001',
        tongue: 'KO',
        backend,
        role: 'SCOUT',
      };
      expect(config.backend).toBe(backend);
    });
  });
});
