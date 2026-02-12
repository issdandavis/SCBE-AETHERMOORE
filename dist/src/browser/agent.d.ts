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
import { TongueCode } from '../tokenizer/ss1.js';
import { BrowserAction, BrowserObservation, BrowserSessionConfig, GovernanceResult, ActionResult, EscalationRequest, EscalationResponse, PageObservation } from './types.js';
import { SessionSummary, SessionStatistics, HiveMemoryExport } from './session.js';
/**
 * Interface for browser automation backends (Playwright, Puppeteer, etc.)
 */
export interface BrowserBackend {
    /** Initialize the browser */
    initialize(config: BrowserSessionConfig): Promise<void>;
    /** Navigate to URL */
    navigate(url: string, options?: {
        waitUntil?: string;
        timeout?: number;
    }): Promise<void>;
    /** Click element */
    click(selector: string, options?: {
        position?: {
            x: number;
            y: number;
        };
    }): Promise<void>;
    /** Type text */
    type(selector: string, text: string, options?: {
        delay?: number;
        clear?: boolean;
    }): Promise<void>;
    /** Scroll */
    scroll(options: {
        selector?: string;
        delta?: {
            x: number;
            y: number;
        };
    }): Promise<void>;
    /** Execute script */
    executeScript<T>(script: string, args?: unknown[]): Promise<T>;
    /** Take screenshot */
    screenshot(options?: {
        fullPage?: boolean;
        selector?: string;
    }): Promise<Buffer>;
    /** Get page observation */
    observe(): Promise<PageObservation>;
    /** Close browser */
    close(): Promise<void>;
    /** Check if browser is connected */
    isConnected(): boolean;
}
/**
 * Interface for handling escalations (to higher AI or human)
 */
export interface EscalationHandler {
    /** Submit escalation request */
    submit(request: EscalationRequest): Promise<void>;
    /** Wait for escalation response */
    waitForResponse(requestId: string, timeout: number): Promise<EscalationResponse>;
    /** Check if escalation is pending */
    isPending(requestId: string): boolean;
}
export interface BrowserAgentConfig {
    /** Agent ID */
    agentId: string;
    /** Agent's Sacred Tongue */
    tongue: TongueCode;
    /** Browser backend */
    backend: BrowserBackend;
    /** Session config overrides */
    sessionConfig?: Partial<BrowserSessionConfig>;
    /** Escalation handler */
    escalationHandler?: EscalationHandler;
    /** Enable auto-screenshot on actions */
    autoScreenshot?: boolean;
    /** Maximum actions per session */
    maxActions?: number;
    /** Callback for action completion */
    onActionComplete?: (action: BrowserAction, result: ActionResult, governance: GovernanceResult) => void;
    /** Callback for session events */
    onSessionEvent?: (event: unknown) => void;
}
/**
 * SCBE-governed browser automation agent.
 *
 * Every action goes through the 14-layer governance pipeline before execution.
 */
export declare class BrowserAgent {
    readonly agentId: string;
    readonly tongue: TongueCode;
    private backend;
    private session;
    private config;
    private escalationHandler?;
    private currentObservation;
    private actionSequence;
    constructor(config: BrowserAgentConfig);
    /**
     * Start a new browser session.
     */
    startSession(url?: string): Promise<void>;
    /**
     * Execute a browser action with SCBE governance.
     */
    execute(action: BrowserAction): Promise<ActionResult>;
    /**
     * Navigate to URL.
     */
    navigate(url: string, options?: {
        waitUntil?: 'load' | 'domcontentloaded' | 'networkidle';
    }): Promise<ActionResult>;
    /**
     * Click element.
     */
    click(selector: string, options?: {
        position?: {
            x: number;
            y: number;
        };
    }): Promise<ActionResult>;
    /**
     * Type text into element.
     */
    type(selector: string, text: string, options?: {
        clear?: boolean;
        sensitive?: boolean;
    }): Promise<ActionResult>;
    /**
     * Execute JavaScript (requires highest governance tier).
     */
    executeScript<T>(script: string, args?: unknown[]): Promise<ActionResult>;
    /**
     * Take screenshot without action evaluation.
     */
    takeScreenshot(): Promise<{
        data: string;
        format: 'png';
        width: number;
        height: number;
        fullPage: boolean;
        timestamp: number;
    } | undefined>;
    /**
     * Get current observation.
     */
    getObservation(): Promise<BrowserObservation>;
    /**
     * Get session statistics.
     */
    getStatistics(): SessionStatistics | null;
    /**
     * Get session history.
     */
    getHistory(options?: {
        limit?: number;
        decision?: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
    }): import("./types.js").ActionHistoryEntry[];
    /**
     * Export session for Hive Memory.
     */
    exportSession(): HiveMemoryExport | null;
    /**
     * Import historical data for learning.
     */
    importHistory(data: HiveMemoryExport): void;
    /**
     * Pause session.
     */
    pause(): void;
    /**
     * Resume session.
     */
    resume(): void;
    /**
     * End session and close browser.
     */
    endSession(): Promise<SessionSummary | null>;
    private executeAction;
    private handleEscalation;
}
/**
 * Create a browser agent.
 */
export declare function createBrowserAgent(config: BrowserAgentConfig): BrowserAgent;
/**
 * Mock browser backend for testing.
 */
export declare class MockBrowserBackend implements BrowserBackend {
    private connected;
    private url;
    private title;
    initialize(): Promise<void>;
    navigate(url: string): Promise<void>;
    click(): Promise<void>;
    type(): Promise<void>;
    scroll(): Promise<void>;
    executeScript<T>(script: string): Promise<T>;
    screenshot(): Promise<Buffer>;
    observe(): Promise<PageObservation>;
    close(): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=agent.d.ts.map