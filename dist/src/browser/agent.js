"use strict";
/**
 * SCBE Browser Agent
 * ===================
 *
 * Main browser automation agent with SCBE 14-layer governance.
 *
 * Architecture:
 * ┌─────────────────────────────────────────────────────────┐
 * │                    BROWSER AGENT                        │
 * ├─────────────────────────────────────────────────────────┤
 * │  Observation: DOM state, screenshot, URL                │
 * │  Action Space: click, type, scroll, navigate            │
 * ├─────────────────────────────────────────────────────────┤
 * │                         ↓                               │
 * │  ┌─────────────────────────────────────────────────┐    │
 * │  │         SCBE 14-Layer Governance                │    │
 * │  │  • Every action → pipeline evaluation           │    │
 * │  │  • Temporal tracking per browser session        │    │
 * │  │  • Hive memory for cross-session learning       │    │
 * │  │  • 4-tier decision: ALLOW/QUARANTINE/DENY       │    │
 * │  └─────────────────────────────────────────────────┘    │
 * │                         ↓                               │
 * │  Playwright/Puppeteer execution layer                   │
 * └─────────────────────────────────────────────────────────┘
 *
 * @module browser/agent
 * @layer Layers 1-14 (full pipeline)
 * @version 3.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MockBrowserBackend = exports.BrowserAgent = void 0;
exports.createBrowserAgent = createBrowserAgent;
const session_js_1 = require("./session.js");
/**
 * SCBE-governed browser automation agent.
 *
 * Every action goes through the 14-layer governance pipeline before execution.
 */
class BrowserAgent {
    agentId;
    tongue;
    backend;
    session = null;
    config;
    escalationHandler;
    currentObservation = null;
    actionSequence = 0;
    constructor(config) {
        this.agentId = config.agentId;
        this.tongue = config.tongue;
        this.backend = config.backend;
        this.config = config;
        this.escalationHandler = config.escalationHandler;
    }
    /**
     * Start a new browser session.
     */
    async startSession(url) {
        // Create session config
        const sessionConfig = {
            ...(0, session_js_1.defaultSessionConfig)(this.agentId, this.tongue),
            ...this.config.sessionConfig,
        };
        // Initialize backend
        await this.backend.initialize(sessionConfig);
        // Create session
        this.session = (0, session_js_1.createBrowserSession)(sessionConfig);
        // Add event listener
        if (this.config.onSessionEvent) {
            this.session.addEventListener(this.config.onSessionEvent);
        }
        // Initialize session
        await this.session.initialize();
        // Navigate to initial URL if provided
        if (url) {
            await this.navigate(url);
        }
    }
    /**
     * Execute a browser action with SCBE governance.
     */
    async execute(action) {
        if (!this.session) {
            throw new Error('Session not started. Call startSession() first.');
        }
        if (!this.backend.isConnected()) {
            throw new Error('Browser not connected.');
        }
        // Check max actions
        if (this.config.maxActions) {
            const stats = this.session.getStatistics();
            if (stats.actionCount >= this.config.maxActions) {
                return {
                    success: false,
                    error: `Maximum actions (${this.config.maxActions}) reached`,
                    duration: 0,
                };
            }
        }
        const startTime = Date.now();
        try {
            // Get current observation
            const observation = await this.getObservation();
            // Evaluate action through SCBE pipeline
            const { governance, canExecute, escalationRequired } = await this.session.evaluateAction(action, observation);
            // Handle escalation if required
            if (escalationRequired && !canExecute) {
                const resolved = await this.handleEscalation(escalationRequired);
                if (!resolved.canProceed) {
                    return {
                        success: false,
                        error: `Action denied after escalation: ${governance.explanation}`,
                        duration: Date.now() - startTime,
                    };
                }
                // Use potentially modified action
                action = resolved.action;
            }
            // Check if we can execute
            if (!canExecute && !escalationRequired) {
                return {
                    success: false,
                    error: `Action denied: ${governance.explanation}`,
                    duration: Date.now() - startTime,
                };
            }
            // Execute the action
            const execResult = await this.executeAction(action);
            // Get updated observation
            const newObservation = await this.getObservation();
            // Create result
            const result = {
                success: execResult.success,
                error: execResult.error,
                value: execResult.value,
                duration: Date.now() - startTime,
                observation: newObservation,
                screenshot: this.config.autoScreenshot ? await this.takeScreenshot() : undefined,
            };
            // Record in session
            // Note: The history entry ID should be retrieved from the evaluation
            // For now we use a generated ID
            const entryId = `${this.session.sessionId}-${this.actionSequence++}`;
            this.session.recordResult(entryId, result, newObservation);
            // Callback
            if (this.config.onActionComplete) {
                this.config.onActionComplete(action, result, governance);
            }
            return result;
        }
        catch (err) {
            return {
                success: false,
                error: err instanceof Error ? err.message : 'Unknown error',
                duration: Date.now() - startTime,
            };
        }
    }
    // ===========================================================================
    // CONVENIENCE METHODS
    // ===========================================================================
    /**
     * Navigate to URL.
     */
    async navigate(url, options) {
        const action = {
            type: 'navigate',
            url,
            waitUntil: options?.waitUntil,
        };
        return this.execute(action);
    }
    /**
     * Click element.
     */
    async click(selector, options) {
        const action = {
            type: 'click',
            selector,
            position: options?.position,
        };
        return this.execute(action);
    }
    /**
     * Type text into element.
     */
    async type(selector, text, options) {
        const action = {
            type: 'type',
            selector,
            text,
            clear: options?.clear,
            sensitive: options?.sensitive,
        };
        return this.execute(action);
    }
    /**
     * Execute JavaScript (requires highest governance tier).
     */
    async executeScript(script, args) {
        return this.execute({
            type: 'execute_script',
            script,
            args,
        });
    }
    /**
     * Take screenshot without action evaluation.
     */
    async takeScreenshot() {
        if (!this.backend.isConnected())
            return undefined;
        try {
            const buffer = await this.backend.screenshot({ fullPage: false });
            return {
                data: buffer.toString('base64'),
                format: 'png',
                width: this.config.sessionConfig?.viewport?.width ?? 1280,
                height: this.config.sessionConfig?.viewport?.height ?? 720,
                fullPage: false,
                timestamp: Date.now(),
            };
        }
        catch {
            return undefined;
        }
    }
    // ===========================================================================
    // SESSION MANAGEMENT
    // ===========================================================================
    /**
     * Get current observation.
     */
    async getObservation() {
        if (!this.backend.isConnected()) {
            throw new Error('Browser not connected');
        }
        const page = await this.backend.observe();
        this.currentObservation = {
            sessionId: this.session?.sessionId ?? 'unknown',
            sequence: this.actionSequence,
            page,
            timestamp: Date.now(),
        };
        return this.currentObservation;
    }
    /**
     * Get session statistics.
     */
    getStatistics() {
        return this.session?.getStatistics() ?? null;
    }
    /**
     * Get session history.
     */
    getHistory(options) {
        return this.session?.getHistory(options) ?? [];
    }
    /**
     * Export session for Hive Memory.
     */
    exportSession() {
        return this.session?.exportForHiveMemory() ?? null;
    }
    /**
     * Import historical data for learning.
     */
    importHistory(data) {
        this.session?.importHistoricalData(data);
    }
    /**
     * Pause session.
     */
    pause() {
        this.session?.pause();
    }
    /**
     * Resume session.
     */
    resume() {
        this.session?.resume();
    }
    /**
     * End session and close browser.
     */
    async endSession() {
        let summary = null;
        if (this.session) {
            summary = await this.session.terminate();
        }
        try {
            await this.backend.close();
        }
        catch {
            // Ignore close errors
        }
        this.session = null;
        this.currentObservation = null;
        return summary;
    }
    // ===========================================================================
    // PRIVATE METHODS
    // ===========================================================================
    async executeAction(action) {
        try {
            switch (action.type) {
                case 'navigate':
                    await this.backend.navigate(action.url, {
                        waitUntil: action.waitUntil,
                        timeout: action.timeout,
                    });
                    return { success: true };
                case 'click':
                    await this.backend.click(action.selector, { position: action.position });
                    return { success: true };
                case 'type':
                    await this.backend.type(action.selector, action.text, {
                        delay: action.delay,
                        clear: action.clear,
                    });
                    return { success: true };
                case 'scroll':
                    await this.backend.scroll({ selector: action.selector, delta: action.delta });
                    return { success: true };
                case 'execute_script':
                    const result = await this.backend.executeScript(action.script, action.args);
                    return { success: true, value: result };
                case 'screenshot':
                    const buffer = await this.backend.screenshot({
                        fullPage: action.fullPage,
                        selector: action.selector,
                    });
                    return { success: true, value: buffer.toString('base64') };
                case 'go_back':
                case 'go_forward':
                case 'refresh':
                case 'wait':
                case 'hover':
                case 'select':
                case 'press':
                    // These would be implemented with the actual backend
                    return { success: true };
                default:
                    return { success: false, error: `Unsupported action type: ${action.type}` };
            }
        }
        catch (err) {
            return {
                success: false,
                error: err instanceof Error ? err.message : 'Execution error',
            };
        }
    }
    async handleEscalation(request) {
        if (!this.escalationHandler || !this.session) {
            // No handler - deny by default
            return { canProceed: false, action: request.action };
        }
        // Submit escalation
        await this.escalationHandler.submit(request);
        // Wait for response
        const response = await this.escalationHandler.waitForResponse(request.requestId, request.deadline - Date.now());
        // Handle response
        return this.session.handleEscalationResponse(response);
    }
}
exports.BrowserAgent = BrowserAgent;
// =============================================================================
// FACTORY
// =============================================================================
/**
 * Create a browser agent.
 */
function createBrowserAgent(config) {
    return new BrowserAgent(config);
}
// =============================================================================
// MOCK BACKEND FOR TESTING
// =============================================================================
/**
 * Mock browser backend for testing.
 */
class MockBrowserBackend {
    connected = false;
    url = 'about:blank';
    title = 'Mock Page';
    async initialize() {
        this.connected = true;
    }
    async navigate(url) {
        this.url = url;
        this.title = `Page at ${url}`;
    }
    async click() {
        // Mock click
    }
    async type() {
        // Mock type
    }
    async scroll() {
        // Mock scroll
    }
    async executeScript(script) {
        return eval(script);
    }
    async screenshot() {
        return Buffer.from('mock-screenshot');
    }
    async observe() {
        return {
            url: this.url,
            title: this.title,
            readyState: 'complete',
            viewport: { width: 1280, height: 720 },
            scroll: { x: 0, y: 0 },
            interactiveElements: [],
            forms: [],
            dialogs: [],
            loadTime: 100,
            timestamp: Date.now(),
        };
    }
    async close() {
        this.connected = false;
    }
    isConnected() {
        return this.connected;
    }
}
exports.MockBrowserBackend = MockBrowserBackend;
//# sourceMappingURL=agent.js.map