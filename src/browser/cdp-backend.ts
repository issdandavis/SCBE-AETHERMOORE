/**
 * @file cdp-backend.ts
 * @module browser/cdp-backend
 * @layer Layer 1-14 (full pipeline integration)
 * @component SCBEPuppeteer — Chrome DevTools Protocol Backend
 * @version 1.0.0
 *
 * Zero-dependency browser automation backend using Chrome DevTools Protocol.
 * Implements BrowserBackend interface for the SCBE Browser Agent.
 *
 * No Playwright. No Puppeteer. No Selenium. Just raw CDP over WebSocket
 * using our own WSClient (src/browser/ws-client.ts).
 *
 * Launch Chrome with: chrome --remote-debugging-port=9222
 */

import { request as httpRequest } from 'http';
import { BrowserBackend } from './agent.js';
import { WSClient } from './ws-client.js';
import {
  BrowserSessionConfig,
  PageObservation,
  DOMElementState,
  FormObservation,
  FormFieldObservation,
  SensitiveFieldType,
  DialogObservation,
} from './types.js';

// =============================================================================
// TYPES
// =============================================================================

/** CDP command response */
interface CDPResponse {
  id: number;
  result?: Record<string, unknown>;
  error?: { code: number; message: string };
}

/** CDP event message */
interface CDPEvent {
  method: string;
  params: Record<string, unknown>;
}

/** CDP target info from /json endpoint */
interface CDPTarget {
  id: string;
  type: string;
  title: string;
  url: string;
  webSocketDebuggerUrl?: string;
}

/** Options for CDPBackend construction */
export interface CDPBackendOptions {
  /** Chrome debug host (default 127.0.0.1) */
  host?: string;
  /** Chrome debug port (default 9222) */
  port?: number;
  /** Specific target ID to connect to */
  targetId?: string;
  /** Command timeout in ms (default 30000) */
  commandTimeout?: number;
  /** Whether to log CDP traffic (default false) */
  debug?: boolean;
}

// =============================================================================
// SENSITIVE FIELD PATTERNS
// =============================================================================

const SENSITIVE_PATTERNS: [RegExp, SensitiveFieldType][] = [
  [/password|passwd|pwd/i, 'password'],
  [/credit.?card|card.?number|cc.?num/i, 'credit_card'],
  [/ssn|social.?security/i, 'ssn'],
  [/bank.?account|routing.?number|iban/i, 'bank_account'],
  [/api.?key|access.?key|secret.?key/i, 'api_key'],
  [/secret|token/i, 'secret'],
  [/passport|driver.?license|national.?id/i, 'personal_id'],
  [/medical|health|diagnosis|prescription/i, 'medical'],
  [/biometric|fingerprint|face.?id/i, 'biometric'],
];

// =============================================================================
// CDP BACKEND
// =============================================================================

/**
 * SCBEPuppeteer — our own browser automation using Chrome DevTools Protocol.
 *
 * Connects directly to Chrome via WebSocket, sends CDP commands,
 * and translates responses to the BrowserBackend interface.
 *
 * ```
 * ┌──────────────────────────────────────────────┐
 * │  CDPBackend (implements BrowserBackend)       │
 * ├──────────────────────────────────────────────┤
 * │  navigate()  → Page.navigate                 │
 * │  click()     → DOM.querySelector             │
 * │               → DOM.getBoxModel              │
 * │               → Input.dispatchMouseEvent     │
 * │  type()      → DOM.focus                     │
 * │               → Input.dispatchKeyEvent       │
 * │  scroll()    → Runtime.evaluate              │
 * │  screenshot()→ Page.captureScreenshot        │
 * │  observe()   → Runtime.evaluate (DOM query)  │
 * │  exec()      → Runtime.evaluate              │
 * ├──────────────────────────────────────────────┤
 * │  WSClient (ws-client.ts)                     │
 * │  Raw TCP → HTTP upgrade → WebSocket frames   │
 * └──────────────────────────────────────────────┘
 * ```
 */
export class CDPBackend implements BrowserBackend {
  private ws: WSClient | null = null;
  private host: string;
  private port: number;
  private targetId?: string;
  private commandTimeout: number;
  private debug: boolean;

  private commandId = 0;
  private pending = new Map<number, {
    resolve: (result: Record<string, unknown>) => void;
    reject: (err: Error) => void;
    timer: ReturnType<typeof setTimeout>;
  }>();

  private eventHandlers = new Map<string, ((params: Record<string, unknown>) => void)[]>();
  private connected = false;
  private dialogs: DialogObservation[] = [];
  private sessionConfig: BrowserSessionConfig | null = null;

  constructor(options?: CDPBackendOptions) {
    this.host = options?.host ?? '127.0.0.1';
    this.port = options?.port ?? 9222;
    this.targetId = options?.targetId;
    this.commandTimeout = options?.commandTimeout ?? 30000;
    this.debug = options?.debug ?? false;
  }

  // ===========================================================================
  // BrowserBackend Interface
  // ===========================================================================

  async initialize(config: BrowserSessionConfig): Promise<void> {
    this.sessionConfig = config;

    // Step 1: Discover Chrome targets via HTTP /json endpoint
    const targets = await this.getTargets();

    // Step 2: Select target
    let target: CDPTarget | undefined;
    if (this.targetId) {
      target = targets.find((t) => t.id === this.targetId);
    } else {
      // Prefer page targets
      target = targets.find((t) => t.type === 'page') ?? targets[0];
    }

    if (!target) {
      throw new Error(
        `No Chrome targets found. Start Chrome with: chrome --remote-debugging-port=${this.port}`
      );
    }

    const wsUrl = target.webSocketDebuggerUrl;
    if (!wsUrl) {
      throw new Error(`Target "${target.title}" has no WebSocket debug URL`);
    }

    // Step 3: Connect WebSocket
    this.ws = new WSClient(wsUrl, { connectTimeout: config.timeout });

    this.ws.on('message', (data: string) => this.onMessage(data));
    this.ws.on('close', () => {
      this.connected = false;
    });
    this.ws.on('error', (err: Error) => {
      if (this.debug) console.error('[CDP] WebSocket error:', err.message);
    });

    await this.ws.connect();
    this.connected = true;

    // Step 4: Enable required CDP domains
    await this.send('Page.enable');
    await this.send('DOM.enable');
    await this.send('Runtime.enable');
    await this.send('Network.enable');

    // Step 5: Set up dialog handler
    this.onEvent('Page.javascriptDialogOpening', (params) => {
      this.dialogs.push({
        type: params.type as DialogObservation['type'],
        message: params.message as string,
        defaultValue: params.defaultPromptText as string | undefined,
      });
    });

    this.onEvent('Page.javascriptDialogClosed', () => {
      this.dialogs.shift();
    });

    // Step 6: Configure viewport if specified
    if (config.viewport) {
      await this.send('Emulation.setDeviceMetricsOverride', {
        width: config.viewport.width,
        height: config.viewport.height,
        deviceScaleFactor: 1,
        mobile: false,
      });
    }

    // Step 7: Set user agent if specified
    if (config.userAgent) {
      await this.send('Network.setUserAgentOverride', {
        userAgent: config.userAgent,
      });
    }

    if (this.debug) {
      console.log(`[CDP] Connected to "${target.title}" (${target.url})`);
    }
  }

  async navigate(
    url: string,
    options?: { waitUntil?: string; timeout?: number }
  ): Promise<void> {
    this.assertConnected();

    const timeout = options?.timeout ?? this.commandTimeout;

    // Navigate
    const result = await this.send('Page.navigate', { url }, timeout);

    if (result.errorText) {
      throw new Error(`Navigation failed: ${result.errorText}`);
    }

    // Wait for load event
    const waitUntil = options?.waitUntil ?? 'load';
    await this.waitForLoad(waitUntil, timeout);
  }

  async click(
    selector: string,
    options?: { position?: { x: number; y: number } }
  ): Promise<void> {
    this.assertConnected();

    let x: number;
    let y: number;

    if (options?.position) {
      x = options.position.x;
      y = options.position.y;
    } else {
      // Find element and get center coordinates
      const coords = await this.getElementCenter(selector);
      x = coords.x;
      y = coords.y;
    }

    // Dispatch mouse events: move → down → up
    await this.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x,
      y,
    });

    await this.send('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x,
      y,
      button: 'left',
      clickCount: 1,
    });

    await this.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x,
      y,
      button: 'left',
      clickCount: 1,
    });
  }

  async type(
    selector: string,
    text: string,
    options?: { delay?: number; clear?: boolean }
  ): Promise<void> {
    this.assertConnected();

    // Focus the element
    const nodeId = await this.querySelector(selector);
    await this.send('DOM.focus', { nodeId });

    // Clear if requested
    if (options?.clear) {
      await this.send('Runtime.evaluate', {
        expression: `document.querySelector(${JSON.stringify(selector)}).value = ''`,
      });
    }

    // Type each character
    const delay = options?.delay ?? 0;

    for (const char of text) {
      // insertText is the reliable way to type characters
      await this.send('Input.dispatchKeyEvent', {
        type: 'keyDown',
        key: char,
        text: char,
      });

      await this.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: char,
      });

      if (delay > 0) {
        await sleep(delay);
      }
    }
  }

  async scroll(options: {
    selector?: string;
    delta?: { x: number; y: number };
  }): Promise<void> {
    this.assertConnected();

    if (options.selector) {
      // Scroll element into view
      await this.send('Runtime.evaluate', {
        expression: `document.querySelector(${JSON.stringify(options.selector)})?.scrollIntoView({ behavior: 'smooth', block: 'center' })`,
        awaitPromise: false,
      });
    } else if (options.delta) {
      await this.send('Runtime.evaluate', {
        expression: `window.scrollBy(${options.delta.x}, ${options.delta.y})`,
        awaitPromise: false,
      });
    }
  }

  async executeScript<T>(script: string, args?: unknown[]): Promise<T> {
    this.assertConnected();

    // Wrap script with args if provided
    let expression = script;
    if (args && args.length > 0) {
      const argsJson = JSON.stringify(args);
      expression = `(function() { const __args = ${argsJson}; return (${script}).apply(null, __args); })()`;
    }

    const result = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });

    if (result.exceptionDetails) {
      const details = result.exceptionDetails as Record<string, unknown>;
      const text = (details.text as string) ?? 'Script execution failed';
      throw new Error(text);
    }

    const evalResult = result.result as Record<string, unknown>;
    return evalResult?.value as T;
  }

  async screenshot(options?: {
    fullPage?: boolean;
    selector?: string;
  }): Promise<Buffer> {
    this.assertConnected();

    const params: Record<string, unknown> = { format: 'png' };

    if (options?.fullPage) {
      // Get full page metrics for full-page screenshot
      const metrics = await this.send('Page.getLayoutMetrics');
      const contentSize = metrics.cssContentSize as Record<string, number> ??
        metrics.contentSize as Record<string, number>;

      if (contentSize) {
        params.clip = {
          x: 0,
          y: 0,
          width: contentSize.width,
          height: contentSize.height,
          scale: 1,
        };
        params.captureBeyondViewport = true;
      }
    } else if (options?.selector) {
      // Element screenshot — get bounding box
      const coords = await this.getElementBox(options.selector);
      params.clip = {
        x: coords.x,
        y: coords.y,
        width: coords.width,
        height: coords.height,
        scale: 1,
      };
    }

    const result = await this.send('Page.captureScreenshot', params);
    return Buffer.from(result.data as string, 'base64');
  }

  async observe(): Promise<PageObservation> {
    this.assertConnected();

    // Gather page state via Runtime.evaluate (single round-trip for most data)
    const pageData = await this.executeScript<{
      url: string;
      title: string;
      readyState: string;
      scrollX: number;
      scrollY: number;
      innerWidth: number;
      innerHeight: number;
      interactive: Array<{
        tagName: string;
        id: string;
        classList: string[];
        textContent: string;
        x: number;
        y: number;
        width: number;
        height: number;
        visible: boolean;
        inputType?: string;
        value?: string;
        ariaRole?: string;
        dataAttributes: Record<string, string>;
      }>;
      forms: Array<{
        identifier: string;
        action: string;
        method: string;
        fields: Array<{
          name: string;
          type: string;
          value: string;
          required: boolean;
          label?: string;
        }>;
      }>;
    }>(`(function() {
      var result = {
        url: location.href,
        title: document.title,
        readyState: document.readyState,
        scrollX: window.scrollX,
        scrollY: window.scrollY,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        interactive: [],
        forms: []
      };

      // Gather interactive elements
      var interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [tabindex], [onclick]';
      var els = document.querySelectorAll(interactiveSelectors);
      var maxElements = 100;
      for (var i = 0; i < Math.min(els.length, maxElements); i++) {
        var el = els[i];
        var rect = el.getBoundingClientRect();
        var style = window.getComputedStyle(el);
        var visible = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
        var dataAttrs = {};
        for (var j = 0; j < el.attributes.length; j++) {
          var attr = el.attributes[j];
          if (attr.name.startsWith('data-')) {
            dataAttrs[attr.name] = attr.value;
          }
        }
        result.interactive.push({
          tagName: el.tagName.toLowerCase(),
          id: el.id || '',
          classList: Array.from(el.classList),
          textContent: (el.textContent || '').trim().substring(0, 100),
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          visible: visible,
          inputType: el.type || undefined,
          value: el.value !== undefined ? String(el.value).substring(0, 100) : undefined,
          ariaRole: el.getAttribute('role') || undefined,
          dataAttributes: dataAttrs
        });
      }

      // Gather forms
      var formEls = document.querySelectorAll('form');
      for (var f = 0; f < formEls.length; f++) {
        var form = formEls[f];
        var fields = [];
        var inputs = form.querySelectorAll('input, select, textarea');
        for (var k = 0; k < inputs.length; k++) {
          var inp = inputs[k];
          var labelEl = form.querySelector('label[for=' + JSON.stringify(inp.id || '') + ']');
          fields.push({
            name: inp.name || '',
            type: inp.type || 'text',
            value: String(inp.value || '').substring(0, 50),
            required: inp.required || false,
            label: labelEl ? labelEl.textContent.trim() : undefined
          });
        }
        result.forms.push({
          identifier: form.id || form.name || 'form-' + f,
          action: form.action || '',
          method: (form.method || 'GET').toUpperCase(),
          fields: fields
        });
      }

      return result;
    })()`);

    // Transform to PageObservation
    const interactiveElements: DOMElementState[] = (pageData.interactive ?? []).map((el) => ({
      tagName: el.tagName,
      id: el.id || undefined,
      classList: el.classList,
      textContent: el.textContent,
      bounds: { x: el.x, y: el.y, width: el.width, height: el.height },
      visible: el.visible,
      interactive: true,
      inputType: el.inputType,
      value: el.value,
      ariaRole: el.ariaRole,
      dataAttributes: el.dataAttributes,
    }));

    const forms: FormObservation[] = (pageData.forms ?? []).map((form) => {
      const fields: FormFieldObservation[] = form.fields.map((field) => {
        const sensitivity = detectFieldSensitivity(field.name, field.type);
        return {
          name: field.name,
          type: field.type,
          value: sensitivity !== 'none' ? '****' : field.value,
          required: field.required,
          label: field.label,
          sensitivity,
        };
      });

      const sensitiveFields = fields.filter((f) => f.sensitivity !== 'none');
      const sensitiveTypes = [
        ...new Set(sensitiveFields.map((f) => f.sensitivity)),
      ].filter((s): s is SensitiveFieldType => s !== 'none');

      return {
        identifier: form.identifier,
        action: form.action,
        method: form.method as 'GET' | 'POST',
        fields,
        hasSensitiveFields: sensitiveFields.length > 0,
        sensitiveFieldTypes: sensitiveTypes,
      };
    });

    return {
      url: pageData.url,
      title: pageData.title,
      readyState: pageData.readyState as PageObservation['readyState'],
      viewport: {
        width: pageData.innerWidth,
        height: pageData.innerHeight,
      },
      scroll: {
        x: pageData.scrollX,
        y: pageData.scrollY,
      },
      interactiveElements,
      forms,
      dialogs: [...this.dialogs],
      loadTime: 0,
      timestamp: Date.now(),
    };
  }

  async close(): Promise<void> {
    if (this.ws) {
      // Cancel pending commands
      for (const [id, pending] of this.pending) {
        clearTimeout(pending.timer);
        pending.reject(new Error('Connection closing'));
        this.pending.delete(id);
      }

      await this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this.dialogs = [];
    this.eventHandlers.clear();
  }

  isConnected(): boolean {
    return this.connected && this.ws !== null && this.ws.state === 'OPEN';
  }

  // ===========================================================================
  // CDP-SPECIFIC METHODS (not part of BrowserBackend, but useful for advanced use)
  // ===========================================================================

  /**
   * Send a raw CDP command.
   * Exposed for advanced usage beyond BrowserBackend interface.
   */
  async sendCommand(method: string, params?: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.send(method, params);
  }

  /**
   * Register a CDP event handler.
   */
  onEvent(method: string, handler: (params: Record<string, unknown>) => void): void {
    const handlers = this.eventHandlers.get(method) ?? [];
    handlers.push(handler);
    this.eventHandlers.set(method, handlers);
  }

  /**
   * Remove a CDP event handler.
   */
  offEvent(method: string, handler: (params: Record<string, unknown>) => void): void {
    const handlers = this.eventHandlers.get(method);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    }
  }

  /**
   * Accept the current JavaScript dialog.
   */
  async acceptDialog(promptText?: string): Promise<void> {
    await this.send('Page.handleJavaScriptDialog', {
      accept: true,
      promptText,
    });
  }

  /**
   * Dismiss the current JavaScript dialog.
   */
  async dismissDialog(): Promise<void> {
    await this.send('Page.handleJavaScriptDialog', { accept: false });
  }

  /**
   * Go back in browser history.
   */
  async goBack(): Promise<void> {
    const history = await this.send('Page.getNavigationHistory');
    const entries = history.entries as Array<{ id: number }>;
    const currentIndex = history.currentIndex as number;
    if (currentIndex > 0) {
      await this.send('Page.navigateToHistoryEntry', {
        entryId: entries[currentIndex - 1].id,
      });
    }
  }

  /**
   * Go forward in browser history.
   */
  async goForward(): Promise<void> {
    const history = await this.send('Page.getNavigationHistory');
    const entries = history.entries as Array<{ id: number }>;
    const currentIndex = history.currentIndex as number;
    if (currentIndex < entries.length - 1) {
      await this.send('Page.navigateToHistoryEntry', {
        entryId: entries[currentIndex + 1].id,
      });
    }
  }

  /**
   * Reload the page.
   */
  async reload(): Promise<void> {
    await this.send('Page.reload');
    await this.waitForLoad('load', this.commandTimeout);
  }

  /**
   * Set a cookie.
   */
  async setCookie(cookie: {
    name: string;
    value: string;
    domain?: string;
    path?: string;
    secure?: boolean;
    httpOnly?: boolean;
    sameSite?: string;
    expires?: number;
  }): Promise<void> {
    await this.send('Network.setCookie', cookie);
  }

  /**
   * Clear all cookies.
   */
  async clearCookies(domain?: string): Promise<void> {
    if (domain) {
      const result = await this.send('Network.getCookies', { urls: [`https://${domain}`, `http://${domain}`] });
      const cookies = result.cookies as Array<{ name: string; domain: string }>;
      for (const cookie of cookies) {
        await this.send('Network.deleteCookies', {
          name: cookie.name,
          domain: cookie.domain,
        });
      }
    } else {
      await this.send('Network.clearBrowserCookies');
    }
  }

  /**
   * Hover over an element.
   */
  async hover(selector: string): Promise<void> {
    const coords = await this.getElementCenter(selector);
    await this.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: coords.x,
      y: coords.y,
    });
  }

  /**
   * Press a keyboard key.
   */
  async pressKey(key: string, modifiers?: string[]): Promise<void> {
    const mod = resolveModifiers(modifiers ?? []);

    await this.send('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key,
      modifiers: mod,
      windowsVirtualKeyCode: getKeyCode(key),
    });

    await this.send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key,
      modifiers: mod,
      windowsVirtualKeyCode: getKeyCode(key),
    });
  }

  /**
   * Wait for a selector to appear in the DOM.
   */
  async waitForSelector(selector: string, timeout?: number): Promise<void> {
    const deadline = Date.now() + (timeout ?? this.commandTimeout);
    const pollInterval = 100;

    while (Date.now() < deadline) {
      try {
        await this.querySelector(selector);
        return; // Found
      } catch {
        await sleep(pollInterval);
      }
    }

    throw new Error(`Timeout waiting for selector: ${selector}`);
  }

  /**
   * Get a list of all Chrome targets.
   */
  async getTargets(): Promise<CDPTarget[]> {
    return new Promise((resolve, reject) => {
      const req = httpRequest(
        {
          hostname: this.host,
          port: this.port,
          path: '/json',
          method: 'GET',
          timeout: 5000,
        },
        (res) => {
          let body = '';
          res.on('data', (chunk) => (body += chunk));
          res.on('end', () => {
            try {
              resolve(JSON.parse(body));
            } catch {
              reject(new Error(`Invalid JSON from Chrome /json: ${body.slice(0, 100)}`));
            }
          });
        }
      );

      req.on('error', (err) => {
        reject(
          new Error(
            `Cannot reach Chrome at ${this.host}:${this.port}. ` +
              `Start Chrome with: chrome --remote-debugging-port=${this.port}\n` +
              `Original error: ${err.message}`
          )
        );
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error(`Chrome /json request timed out at ${this.host}:${this.port}`));
      });

      req.end();
    });
  }

  // ===========================================================================
  // INTERNAL CDP COMMUNICATION
  // ===========================================================================

  private send(
    method: string,
    params?: Record<string, unknown>,
    timeout?: number
  ): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.state !== 'OPEN') {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const id = ++this.commandId;
      const timeoutMs = timeout ?? this.commandTimeout;

      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP command timed out: ${method} (${timeoutMs}ms)`));
      }, timeoutMs);

      this.pending.set(id, { resolve, reject, timer });

      const message = JSON.stringify({ id, method, params: params ?? {} });

      if (this.debug) {
        console.log(`[CDP →] ${method}`, params ? JSON.stringify(params).slice(0, 200) : '');
      }

      this.ws.send(message);
    });
  }

  private onMessage(data: string): void {
    let parsed: CDPResponse | CDPEvent;
    try {
      parsed = JSON.parse(data);
    } catch {
      return;
    }

    // Command response
    if ('id' in parsed && typeof (parsed as CDPResponse).id === 'number') {
      const resp = parsed as CDPResponse;
      const pending = this.pending.get(resp.id);
      if (pending) {
        clearTimeout(pending.timer);
        this.pending.delete(resp.id);

        if (resp.error) {
          pending.reject(new Error(`CDP error: ${resp.error.message} (${resp.error.code})`));
        } else {
          if (this.debug) {
            console.log(
              `[CDP ←] #${resp.id}`,
              JSON.stringify(resp.result ?? {}).slice(0, 200)
            );
          }
          pending.resolve(resp.result ?? {});
        }
      }
      return;
    }

    // Event
    if ('method' in parsed) {
      const event = parsed as CDPEvent;
      const handlers = this.eventHandlers.get(event.method);
      if (handlers) {
        for (const handler of handlers) {
          try {
            handler(event.params);
          } catch (err) {
            if (this.debug) {
              console.error(`[CDP] Event handler error for ${event.method}:`, err);
            }
          }
        }
      }
    }
  }

  // ===========================================================================
  // DOM HELPERS
  // ===========================================================================

  private async querySelector(selector: string): Promise<number> {
    const doc = await this.send('DOM.getDocument', { depth: 0 });
    const root = doc.root as Record<string, unknown>;
    const rootId = root.nodeId as number;

    const result = await this.send('DOM.querySelector', {
      nodeId: rootId,
      selector,
    });

    const nodeId = result.nodeId as number;
    if (!nodeId) {
      throw new Error(`Element not found: ${selector}`);
    }

    return nodeId;
  }

  private async getElementCenter(selector: string): Promise<{ x: number; y: number }> {
    const nodeId = await this.querySelector(selector);
    const boxResult = await this.send('DOM.getBoxModel', { nodeId });
    const model = boxResult.model as Record<string, unknown>;
    const content = model.content as number[];

    // Content quad: [x1,y1, x2,y2, x3,y3, x4,y4]
    const x = (content[0] + content[2] + content[4] + content[6]) / 4;
    const y = (content[1] + content[3] + content[5] + content[7]) / 4;

    return { x, y };
  }

  private async getElementBox(
    selector: string
  ): Promise<{ x: number; y: number; width: number; height: number }> {
    const nodeId = await this.querySelector(selector);
    const boxResult = await this.send('DOM.getBoxModel', { nodeId });
    const model = boxResult.model as Record<string, unknown>;
    const content = model.content as number[];

    return {
      x: content[0],
      y: content[1],
      width: content[2] - content[0],
      height: content[5] - content[1],
    };
  }

  // ===========================================================================
  // WAIT HELPERS
  // ===========================================================================

  private waitForLoad(condition: string, timeout: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        cleanup();
        reject(new Error(`Timeout waiting for ${condition} (${timeout}ms)`));
      }, timeout);

      const cleanup = () => {
        clearTimeout(timer);
        this.offEvent('Page.loadEventFired', onLoad);
        this.offEvent('Page.domContentEventFired', onDomContent);
      };

      const onLoad = () => {
        cleanup();
        resolve();
      };

      const onDomContent = () => {
        if (condition === 'domcontentloaded') {
          cleanup();
          resolve();
        }
      };

      // Check if already loaded
      this.send('Runtime.evaluate', {
        expression: 'document.readyState',
        returnByValue: true,
      })
        .then((result) => {
          const evalResult = result.result as Record<string, unknown>;
          const readyState = evalResult?.value as string;

          if (condition === 'load' && readyState === 'complete') {
            cleanup();
            resolve();
          } else if (
            condition === 'domcontentloaded' &&
            (readyState === 'interactive' || readyState === 'complete')
          ) {
            cleanup();
            resolve();
          } else if (condition === 'networkidle') {
            // Approximate networkidle: wait 500ms after load
            this.onEvent('Page.loadEventFired', () => {
              setTimeout(() => {
                cleanup();
                resolve();
              }, 500);
            });
          } else {
            // Wait for events
            this.onEvent('Page.loadEventFired', onLoad);
            this.onEvent('Page.domContentEventFired', onDomContent);
          }
        })
        .catch((err) => {
          cleanup();
          reject(err);
        });
    });
  }

  private assertConnected(): void {
    if (!this.isConnected()) {
      throw new Error('CDP backend is not connected. Call initialize() first.');
    }
  }
}

// =============================================================================
// HELPERS
// =============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function detectFieldSensitivity(
  name: string,
  type: string
): SensitiveFieldType | 'none' {
  // Check input type first
  if (type === 'password') return 'password';

  // Check name/id against patterns
  for (const [pattern, sensitivity] of SENSITIVE_PATTERNS) {
    if (pattern.test(name)) return sensitivity;
  }

  return 'none';
}

function resolveModifiers(modifiers: string[]): number {
  let flags = 0;
  for (const mod of modifiers) {
    switch (mod.toLowerCase()) {
      case 'alt':
        flags |= 1;
        break;
      case 'control':
      case 'ctrl':
        flags |= 2;
        break;
      case 'meta':
      case 'command':
      case 'cmd':
        flags |= 4;
        break;
      case 'shift':
        flags |= 8;
        break;
    }
  }
  return flags;
}

const KEY_CODES: Record<string, number> = {
  Backspace: 8,
  Tab: 9,
  Enter: 13,
  Escape: 27,
  Space: 32,
  ArrowLeft: 37,
  ArrowUp: 38,
  ArrowRight: 39,
  ArrowDown: 40,
  Delete: 46,
  Home: 36,
  End: 35,
  PageUp: 33,
  PageDown: 34,
  F1: 112,
  F2: 113,
  F3: 114,
  F4: 115,
  F5: 116,
  F6: 117,
  F7: 118,
  F8: 119,
  F9: 120,
  F10: 121,
  F11: 122,
  F12: 123,
};

function getKeyCode(key: string): number {
  if (KEY_CODES[key]) return KEY_CODES[key];
  if (key.length === 1) return key.toUpperCase().charCodeAt(0);
  return 0;
}

// =============================================================================
// FACTORY
// =============================================================================

/**
 * Create a CDPBackend instance.
 *
 * ```ts
 * import { createCDPBackend } from './cdp-backend.js';
 * import { createBrowserAgent } from './agent.js';
 *
 * const backend = createCDPBackend({ port: 9222 });
 * const agent = createBrowserAgent({
 *   agentId: 'my-agent',
 *   tongue: 'KO',
 *   backend,
 * });
 *
 * await agent.startSession('https://example.com');
 * await agent.click('#submit');
 * await agent.endSession();
 * ```
 */
export function createCDPBackend(options?: CDPBackendOptions): CDPBackend {
  return new CDPBackend(options);
}
