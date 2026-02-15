/**
 * @file playwright-backend.ts
 * @module browser/playwright-backend
 * @layer Layers 1-14 (full pipeline via BrowserAgent)
 * @version 3.2.4
 *
 * Playwright-backed BrowserBackend implementation.
 * Bridges the SCBE browser agent governance system to a real browser.
 *
 * Usage:
 * ```typescript
 * import { PlaywrightBackend } from './playwright-backend';
 * import { createBrowserAgent } from './agent';
 *
 * const backend = new PlaywrightBackend();
 * const agent = createBrowserAgent({
 *   agentId: 'agent-001',
 *   tongue: 'KO',
 *   backend,
 * });
 *
 * await agent.startSession('https://example.com');
 * await agent.click('#login-button');
 * const summary = await agent.endSession();
 * ```
 */

import type { BrowserBackend } from './agent.js';
import type {
  BrowserSessionConfig,
  PageObservation,
  DOMElementState,
  FormObservation,
  FormFieldObservation,
  DialogObservation,
  SensitiveFieldType,
} from './types.js';

// ---------------------------------------------------------------------------
// Playwright types — we use dynamic import so the module works even when
// playwright is not installed (falls back gracefully at runtime).
// ---------------------------------------------------------------------------

/** Minimal subset of Playwright types we depend on. */
interface PwBrowser {
  newContext(opts?: Record<string, unknown>): Promise<PwContext>;
  close(): Promise<void>;
  isConnected(): boolean;
}
interface PwContext {
  newPage(): Promise<PwPage>;
  close(): Promise<void>;
}
interface PwPage {
  goto(
    url: string,
    opts?: { waitUntil?: string; timeout?: number }
  ): Promise<unknown>;
  url(): string;
  title(): Promise<string>;
  click(selector: string, opts?: Record<string, unknown>): Promise<void>;
  fill(selector: string, value: string): Promise<void>;
  type(selector: string, text: string, opts?: Record<string, unknown>): Promise<void>;
  evaluate<T>(fn: string | ((...a: unknown[]) => T), ...args: unknown[]): Promise<T>;
  screenshot(opts?: Record<string, unknown>): Promise<Buffer>;
  goBack(opts?: Record<string, unknown>): Promise<unknown>;
  goForward(opts?: Record<string, unknown>): Promise<unknown>;
  reload(opts?: Record<string, unknown>): Promise<unknown>;
  keyboard: { press(key: string): Promise<void> };
  mouse: {
    wheel(dx: number, dy: number): Promise<void>;
    move(x: number, y: number): Promise<void>;
  };
  selectOption(selector: string, values: string[]): Promise<string[]>;
  setInputFiles(selector: string, files: string[]): Promise<void>;
  hover(selector: string, opts?: Record<string, unknown>): Promise<void>;
  waitForSelector(selector: string, opts?: Record<string, unknown>): Promise<unknown>;
  waitForTimeout(ms: number): Promise<void>;
  waitForLoadState(state?: string, opts?: Record<string, unknown>): Promise<void>;
  on(event: string, handler: (...args: unknown[]) => void): void;
  off(event: string, handler: (...args: unknown[]) => void): void;
  isClosed(): boolean;
  context(): PwContext;
  close(): Promise<void>;
}

type LaunchFn = (opts?: Record<string, unknown>) => Promise<PwBrowser>;

// ---------------------------------------------------------------------------
// Sensitive field detection patterns
// ---------------------------------------------------------------------------

const SENSITIVE_PATTERNS: [RegExp, SensitiveFieldType][] = [
  [/passw/i, 'password'],
  [/credit.?card|card.?num/i, 'credit_card'],
  [/\bssn\b|social.?sec/i, 'ssn'],
  [/bank.?acc|routing/i, 'bank_account'],
  [/api.?key|secret.?key|token/i, 'api_key'],
  [/\bsecret\b/i, 'secret'],
  [/national.?id|passport/i, 'personal_id'],
  [/medical|diagnosis|patient/i, 'medical'],
  [/biometric|fingerprint|retina/i, 'biometric'],
];

function detectSensitivity(
  name: string,
  type: string,
  label: string
): SensitiveFieldType | 'none' {
  const combined = `${name} ${type} ${label}`;
  for (const [re, kind] of SENSITIVE_PATTERNS) {
    if (re.test(combined)) return kind;
  }
  if (type === 'password') return 'password';
  return 'none';
}

// ---------------------------------------------------------------------------
// DOM observation script — injected into the page
// ---------------------------------------------------------------------------

/**
 * Script evaluated inside the page to extract interactive elements, forms,
 * and dialog state.  Returns a plain JSON-serialisable object that maps
 * directly to PageObservation (minus the `timestamp` and `loadTime` fields
 * which are set on the Node side).
 */
const OBSERVE_SCRIPT = `() => {
  // --- Interactive elements ---
  const interactive = [];
  const selectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [tabindex], [onclick], [contenteditable="true"]';
  const els = document.querySelectorAll(selectors);

  for (let i = 0; i < els.length && i < 500; i++) {
    const el = els[i];
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;

    const style = window.getComputedStyle(el);
    const visible = style.display !== 'none'
      && style.visibility !== 'hidden'
      && parseFloat(style.opacity) > 0;

    const data = {};
    for (const attr of el.attributes) {
      if (attr.name.startsWith('data-')) {
        data[attr.name] = attr.value;
      }
    }

    interactive.push({
      tagName: el.tagName.toLowerCase(),
      id: el.id || undefined,
      classList: Array.from(el.classList),
      textContent: (el.textContent || '').trim().slice(0, 200),
      bounds: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      visible,
      interactive: !el.disabled,
      inputType: el.type || undefined,
      value: (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')
        ? (el.type === 'password' ? '***' : (el.value || '').slice(0, 200))
        : undefined,
      ariaRole: el.getAttribute('role') || undefined,
      dataAttributes: data,
    });
  }

  // --- Forms ---
  const forms = [];
  for (const form of document.forms) {
    const fields = [];
    let hasSensitive = false;
    const sensitiveTypes = [];

    for (const el of form.elements) {
      if (!el.name && !el.id) continue;
      const label = el.labels?.[0]?.textContent?.trim() || '';
      const fType = el.type || 'text';
      let sens = 'none';
      const combined = (el.name || '') + ' ' + fType + ' ' + label;
      if (/passw/i.test(combined)) sens = 'password';
      else if (/credit.?card|card.?num/i.test(combined)) sens = 'credit_card';
      else if (/ssn|social.?sec/i.test(combined)) sens = 'ssn';
      else if (/api.?key|secret/i.test(combined)) sens = 'api_key';
      else if (fType === 'password') sens = 'password';

      if (sens !== 'none') {
        hasSensitive = true;
        if (!sensitiveTypes.includes(sens)) sensitiveTypes.push(sens);
      }

      fields.push({
        name: el.name || el.id || '',
        type: fType,
        value: sens !== 'none' ? '***' : (el.value || '').slice(0, 100),
        required: el.required || false,
        label: label.slice(0, 100) || undefined,
        sensitivity: sens,
      });
    }

    forms.push({
      identifier: form.id || form.name || 'form-' + forms.length,
      action: form.action || '',
      method: (form.method || 'GET').toUpperCase(),
      fields,
      hasSensitiveFields: hasSensitive,
      sensitiveFieldTypes: sensitiveTypes,
    });
  }

  return {
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    scroll: {
      x: window.scrollX,
      y: window.scrollY,
    },
    interactiveElements: interactive,
    forms,
    dialogs: [],
  };
}`;

// ---------------------------------------------------------------------------
// PlaywrightBackend
// ---------------------------------------------------------------------------

/** Options for configuring the Playwright backend. */
export interface PlaywrightBackendOptions {
  /**
   * Supply your own `chromium.launch` (or firefox/webkit) function.
   * If omitted, we dynamically `require('playwright')` at init time.
   */
  launchFn?: LaunchFn;

  /** Extra Playwright launch options (headless, slowMo, args, etc.) */
  launchOptions?: Record<string, unknown>;

  /** Block resource types to speed up crawling (images, fonts, etc.) */
  blockResourceTypes?: string[];
}

/**
 * Production BrowserBackend backed by Playwright.
 *
 * Every action the BrowserAgent calls (click, type, navigate, etc.) is
 * forwarded to a real Chromium/Firefox/WebKit browser instance.  The
 * `observe()` method injects a script to extract DOM state, returning a
 * `PageObservation` the agent's 14-layer evaluator can score.
 */
export class PlaywrightBackend implements BrowserBackend {
  private browser: PwBrowser | null = null;
  private context: PwContext | null = null;
  private page: PwPage | null = null;
  private connected = false;
  private dialogs: DialogObservation[] = [];
  private loadStart = 0;

  private readonly launchFn?: LaunchFn;
  private readonly launchOptions: Record<string, unknown>;
  private readonly blockResourceTypes: Set<string>;

  constructor(options?: PlaywrightBackendOptions) {
    this.launchFn = options?.launchFn;
    this.launchOptions = options?.launchOptions ?? {};
    this.blockResourceTypes = new Set(
      options?.blockResourceTypes ?? ['image', 'font', 'media']
    );
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────

  async initialize(config: BrowserSessionConfig): Promise<void> {
    // Resolve the Playwright launcher
    let launch: LaunchFn;
    if (this.launchFn) {
      launch = this.launchFn;
    } else {
      // Dynamic import so the module compiles even without playwright installed
      try {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const pw = require('playwright');
        const browserType = config.browserType ?? 'chromium';
        launch = (opts?: Record<string, unknown>) => pw[browserType].launch(opts);
      } catch {
        throw new Error(
          'Playwright is not installed. Run: npm install playwright && npx playwright install chromium'
        );
      }
    }

    this.browser = await launch({
      headless: config.headless ?? true,
      ...this.launchOptions,
    });

    this.context = await this.browser!.newContext({
      viewport: config.viewport ?? { width: 1280, height: 720 },
      userAgent: config.userAgent,
      ...(config.proxy
        ? {
            proxy: {
              server: config.proxy.server,
              username: config.proxy.username,
              password: config.proxy.password,
            },
          }
        : {}),
    });

    this.page = await this.context.newPage();

    // Track dialogs
    this.page.on('dialog', (dialog: { type: () => string; message: () => string; defaultValue: () => string }) => {
      this.dialogs.push({
        type: dialog.type() as DialogObservation['type'],
        message: dialog.message(),
        defaultValue: dialog.defaultValue() || undefined,
      });
    });

    this.connected = true;
  }

  // ── Navigation ────────────────────────────────────────────────────────

  async navigate(
    url: string,
    options?: { waitUntil?: string; timeout?: number }
  ): Promise<void> {
    this.ensurePage();
    this.loadStart = Date.now();
    await this.page!.goto(url, {
      waitUntil: options?.waitUntil ?? 'domcontentloaded',
      timeout: options?.timeout ?? 30_000,
    });
  }

  // ── Interactions ──────────────────────────────────────────────────────

  async click(
    selector: string,
    options?: { position?: { x: number; y: number } }
  ): Promise<void> {
    this.ensurePage();
    await this.page!.click(selector, options ? { position: options.position } : undefined);
  }

  async type(
    selector: string,
    text: string,
    options?: { delay?: number; clear?: boolean }
  ): Promise<void> {
    this.ensurePage();
    if (options?.clear) {
      await this.page!.fill(selector, '');
    }
    await this.page!.type(selector, text, { delay: options?.delay });
  }

  async scroll(options: {
    selector?: string;
    delta?: { x: number; y: number };
  }): Promise<void> {
    this.ensurePage();
    if (options.selector) {
      await this.page!.evaluate(
        `(sel) => document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth' })`,
        [options.selector]
      );
    } else {
      const dx = options.delta?.x ?? 0;
      const dy = options.delta?.y ?? 300;
      await this.page!.mouse.wheel(dx, dy);
    }
  }

  // ── Script execution ──────────────────────────────────────────────────

  async executeScript<T>(script: string, args?: unknown[]): Promise<T> {
    this.ensurePage();
    if (args && args.length > 0) {
      return this.page!.evaluate<T>(script, ...args);
    }
    return this.page!.evaluate<T>(script);
  }

  // ── Screenshot ────────────────────────────────────────────────────────

  async screenshot(options?: {
    fullPage?: boolean;
    selector?: string;
  }): Promise<Buffer> {
    this.ensurePage();
    if (options?.selector) {
      // Element screenshot via evaluate + clip
      const bounds = await this.page!.evaluate<{
        x: number;
        y: number;
        width: number;
        height: number;
      }>(
        `(sel) => {
          const el = document.querySelector(sel);
          if (!el) throw new Error('Element not found: ' + sel);
          const r = el.getBoundingClientRect();
          return { x: r.x, y: r.y, width: r.width, height: r.height };
        }`,
        [options.selector]
      );
      return this.page!.screenshot({ clip: bounds });
    }
    return this.page!.screenshot({ fullPage: options?.fullPage ?? false });
  }

  // ── Observation ───────────────────────────────────────────────────────

  async observe(): Promise<PageObservation> {
    this.ensurePage();
    const loadTime = this.loadStart > 0 ? Date.now() - this.loadStart : 0;

    const raw = await this.page!.evaluate<{
      url: string;
      title: string;
      readyState: string;
      viewport: { width: number; height: number };
      scroll: { x: number; y: number };
      interactiveElements: DOMElementState[];
      forms: FormObservation[];
      dialogs: DialogObservation[];
    }>(OBSERVE_SCRIPT);

    // Merge any dialogs we captured via the event listener
    const dialogs = this.dialogs.length > 0 ? [...this.dialogs] : raw.dialogs;
    this.dialogs = []; // drain after reading

    return {
      url: raw.url,
      title: raw.title,
      readyState: raw.readyState as PageObservation['readyState'],
      viewport: raw.viewport,
      scroll: raw.scroll,
      interactiveElements: raw.interactiveElements,
      forms: raw.forms,
      dialogs,
      loadTime,
      timestamp: Date.now(),
    };
  }

  // ── Cleanup ───────────────────────────────────────────────────────────

  async close(): Promise<void> {
    this.connected = false;
    try {
      if (this.page && !this.page.isClosed()) await this.page.close();
    } catch { /* ignore */ }
    try {
      if (this.context) await this.context.close();
    } catch { /* ignore */ }
    try {
      if (this.browser) await this.browser.close();
    } catch { /* ignore */ }
    this.page = null;
    this.context = null;
    this.browser = null;
  }

  isConnected(): boolean {
    return this.connected && !!this.browser?.isConnected();
  }

  // ── Internals ─────────────────────────────────────────────────────────

  private ensurePage(): asserts this is { page: PwPage } {
    if (!this.page || !this.connected) {
      throw new Error('Browser not initialized — call initialize() first');
    }
  }
}

// ---------------------------------------------------------------------------
// Factory helper
// ---------------------------------------------------------------------------

/**
 * Create a PlaywrightBackend with sensible defaults.
 *
 * ```typescript
 * const backend = createPlaywrightBackend({ headless: true });
 * ```
 */
export function createPlaywrightBackend(
  options?: PlaywrightBackendOptions
): PlaywrightBackend {
  return new PlaywrightBackend(options);
}
