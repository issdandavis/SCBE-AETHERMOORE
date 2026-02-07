/**
 * SCBE Browser Agent Types
 * =========================
 *
 * Type definitions for browser automation agents governed by the SCBE 14-layer pipeline.
 *
 * @module browser/types
 * @layer Layer 1-14 (full pipeline integration)
 * @version 3.0.0
 */
import { TongueCode } from '../tokenizer/ss1.js';
/**
 * Current state of a DOM element for observation.
 */
export interface DOMElementState {
    /** Element tag name */
    tagName: string;
    /** Element ID if present */
    id?: string;
    /** Element class list */
    classList: string[];
    /** Text content (truncated) */
    textContent: string;
    /** Bounding box */
    bounds: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
    /** Whether element is visible */
    visible: boolean;
    /** Whether element is interactive (clickable, typeable) */
    interactive: boolean;
    /** Input type if applicable */
    inputType?: string;
    /** Current value for inputs */
    value?: string;
    /** ARIA role if present */
    ariaRole?: string;
    /** Data attributes */
    dataAttributes: Record<string, string>;
}
/**
 * Page-level observation snapshot.
 */
export interface PageObservation {
    /** Current URL */
    url: string;
    /** Page title */
    title: string;
    /** Document ready state */
    readyState: 'loading' | 'interactive' | 'complete';
    /** Viewport dimensions */
    viewport: {
        width: number;
        height: number;
    };
    /** Scroll position */
    scroll: {
        x: number;
        y: number;
    };
    /** Interactive elements on page */
    interactiveElements: DOMElementState[];
    /** Form elements */
    forms: FormObservation[];
    /** Any alerts/dialogs present */
    dialogs: DialogObservation[];
    /** Page load time (ms) */
    loadTime: number;
    /** Timestamp of observation */
    timestamp: number;
}
/**
 * Form observation for data entry governance.
 */
export interface FormObservation {
    /** Form ID or name */
    identifier: string;
    /** Form action URL */
    action: string;
    /** HTTP method */
    method: 'GET' | 'POST';
    /** Form fields */
    fields: FormFieldObservation[];
    /** Whether form contains sensitive fields */
    hasSensitiveFields: boolean;
    /** Detected sensitive field types */
    sensitiveFieldTypes: SensitiveFieldType[];
}
/**
 * Individual form field observation.
 */
export interface FormFieldObservation {
    /** Field name */
    name: string;
    /** Field type */
    type: string;
    /** Current value (masked for sensitive) */
    value: string;
    /** Whether field is required */
    required: boolean;
    /** Field label if found */
    label?: string;
    /** Detected sensitivity */
    sensitivity: SensitiveFieldType | 'none';
}
/**
 * Dialog/alert observation.
 */
export interface DialogObservation {
    /** Dialog type */
    type: 'alert' | 'confirm' | 'prompt' | 'beforeunload';
    /** Dialog message */
    message: string;
    /** Default value for prompts */
    defaultValue?: string;
}
/**
 * Types of sensitive form fields requiring elevated governance.
 */
export type SensitiveFieldType = 'password' | 'credit_card' | 'ssn' | 'bank_account' | 'api_key' | 'secret' | 'personal_id' | 'medical' | 'biometric';
/**
 * Screenshot observation for visual analysis.
 */
export interface ScreenshotObservation {
    /** Base64 encoded image */
    data: string;
    /** Image format */
    format: 'png' | 'jpeg' | 'webp';
    /** Dimensions */
    width: number;
    height: number;
    /** Full page or viewport only */
    fullPage: boolean;
    /** Timestamp */
    timestamp: number;
}
/**
 * Complete browser observation combining all sources.
 */
export interface BrowserObservation {
    /** Session ID */
    sessionId: string;
    /** Observation sequence number */
    sequence: number;
    /** Page state */
    page: PageObservation;
    /** Screenshot if captured */
    screenshot?: ScreenshotObservation;
    /** Network activity summary */
    network?: NetworkObservation;
    /** Console messages */
    console?: ConsoleObservation[];
    /** Performance metrics */
    performance?: PerformanceObservation;
    /** Timestamp */
    timestamp: number;
}
/**
 * Network activity observation.
 */
export interface NetworkObservation {
    /** Pending requests */
    pendingRequests: number;
    /** Recent requests */
    recentRequests: NetworkRequest[];
    /** Blocked requests (by content policy) */
    blockedRequests: number;
    /** Data transferred (bytes) */
    bytesTransferred: number;
}
/**
 * Individual network request.
 */
export interface NetworkRequest {
    url: string;
    method: string;
    status?: number;
    resourceType: string;
    timestamp: number;
}
/**
 * Console message observation.
 */
export interface ConsoleObservation {
    level: 'log' | 'info' | 'warn' | 'error';
    message: string;
    timestamp: number;
}
/**
 * Performance metrics observation.
 */
export interface PerformanceObservation {
    /** Time to first byte (ms) */
    ttfb: number;
    /** First contentful paint (ms) */
    fcp: number;
    /** Largest contentful paint (ms) */
    lcp: number;
    /** Total blocking time (ms) */
    tbt: number;
    /** Memory usage (bytes) */
    memoryUsage?: number;
}
/**
 * Base browser action interface.
 */
export interface BrowserActionBase {
    /** Action type discriminator */
    type: BrowserActionType;
    /** Optional target element selector */
    selector?: string;
    /** Action metadata */
    metadata?: Record<string, unknown>;
}
/**
 * All supported browser action types.
 */
export type BrowserActionType = 'navigate' | 'click' | 'type' | 'scroll' | 'select' | 'hover' | 'press' | 'screenshot' | 'wait' | 'execute_script' | 'download' | 'upload' | 'set_cookie' | 'clear_cookies' | 'dialog_accept' | 'dialog_dismiss' | 'go_back' | 'go_forward' | 'refresh';
/**
 * Navigate to URL action.
 */
export interface NavigateAction extends BrowserActionBase {
    type: 'navigate';
    /** Target URL */
    url: string;
    /** Wait until condition */
    waitUntil?: 'load' | 'domcontentloaded' | 'networkidle';
    /** Timeout (ms) */
    timeout?: number;
}
/**
 * Click action.
 */
export interface ClickAction extends BrowserActionBase {
    type: 'click';
    /** Element selector */
    selector: string;
    /** Click position within element */
    position?: {
        x: number;
        y: number;
    };
    /** Click options */
    options?: {
        button?: 'left' | 'right' | 'middle';
        clickCount?: number;
        delay?: number;
        force?: boolean;
    };
}
/**
 * Type text action.
 */
export interface TypeAction extends BrowserActionBase {
    type: 'type';
    /** Element selector */
    selector: string;
    /** Text to type */
    text: string;
    /** Whether to clear field first */
    clear?: boolean;
    /** Typing delay (ms between keystrokes) */
    delay?: number;
    /** Whether content is sensitive (will be masked in logs) */
    sensitive?: boolean;
}
/**
 * Scroll action.
 */
export interface ScrollAction extends BrowserActionBase {
    type: 'scroll';
    /** Scroll to element selector */
    selector?: string;
    /** Or scroll by coordinates */
    delta?: {
        x: number;
        y: number;
    };
    /** Or scroll to coordinates */
    to?: {
        x: number;
        y: number;
    };
}
/**
 * Select option action.
 */
export interface SelectAction extends BrowserActionBase {
    type: 'select';
    /** Select element selector */
    selector: string;
    /** Value(s) to select */
    values: string[];
}
/**
 * Hover action.
 */
export interface HoverAction extends BrowserActionBase {
    type: 'hover';
    /** Element selector */
    selector: string;
    /** Position within element */
    position?: {
        x: number;
        y: number;
    };
}
/**
 * Keyboard press action.
 */
export interface PressAction extends BrowserActionBase {
    type: 'press';
    /** Key or key combination */
    key: string;
    /** Modifier keys */
    modifiers?: ('Control' | 'Shift' | 'Alt' | 'Meta')[];
}
/**
 * Screenshot action.
 */
export interface ScreenshotAction extends BrowserActionBase {
    type: 'screenshot';
    /** Output path */
    path?: string;
    /** Full page or viewport */
    fullPage?: boolean;
    /** Element selector for element screenshot */
    selector?: string;
}
/**
 * Wait action.
 */
export interface WaitAction extends BrowserActionBase {
    type: 'wait';
    /** Wait for selector */
    selector?: string;
    /** Or wait for timeout (ms) */
    timeout?: number;
    /** Or wait for network idle */
    networkIdle?: boolean;
    /** Or wait for function */
    function?: string;
}
/**
 * Execute JavaScript action (highest risk).
 */
export interface ExecuteScriptAction extends BrowserActionBase {
    type: 'execute_script';
    /** Script to execute */
    script: string;
    /** Script arguments */
    args?: unknown[];
}
/**
 * Download file action.
 */
export interface DownloadAction extends BrowserActionBase {
    type: 'download';
    /** URL to download */
    url: string;
    /** Save path */
    path?: string;
}
/**
 * Upload file action.
 */
export interface UploadAction extends BrowserActionBase {
    type: 'upload';
    /** File input selector */
    selector: string;
    /** File path(s) to upload */
    files: string[];
}
/**
 * Set cookie action.
 */
export interface SetCookieAction extends BrowserActionBase {
    type: 'set_cookie';
    /** Cookie name */
    name: string;
    /** Cookie value */
    value: string;
    /** Cookie domain */
    domain?: string;
    /** Cookie path */
    path?: string;
    /** Cookie expiry */
    expires?: number;
    /** Secure flag */
    secure?: boolean;
    /** HttpOnly flag */
    httpOnly?: boolean;
    /** SameSite attribute */
    sameSite?: 'Strict' | 'Lax' | 'None';
}
/**
 * Clear cookies action.
 */
export interface ClearCookiesAction extends BrowserActionBase {
    type: 'clear_cookies';
    /** Only clear for specific domain */
    domain?: string;
}
/**
 * Dialog accept action.
 */
export interface DialogAcceptAction extends BrowserActionBase {
    type: 'dialog_accept';
    /** Prompt input value */
    promptText?: string;
}
/**
 * Dialog dismiss action.
 */
export interface DialogDismissAction extends BrowserActionBase {
    type: 'dialog_dismiss';
}
/**
 * Go back action.
 */
export interface GoBackAction extends BrowserActionBase {
    type: 'go_back';
}
/**
 * Go forward action.
 */
export interface GoForwardAction extends BrowserActionBase {
    type: 'go_forward';
}
/**
 * Refresh action.
 */
export interface RefreshAction extends BrowserActionBase {
    type: 'refresh';
}
/**
 * Union type of all browser actions.
 */
export type BrowserAction = NavigateAction | ClickAction | TypeAction | ScrollAction | SelectAction | HoverAction | PressAction | ScreenshotAction | WaitAction | ExecuteScriptAction | DownloadAction | UploadAction | SetCookieAction | ClearCookiesAction | DialogAcceptAction | DialogDismissAction | GoBackAction | GoForwardAction | RefreshAction;
/**
 * Action sensitivity levels for governance.
 */
export declare const ACTION_SENSITIVITY: Record<BrowserActionType, number>;
/**
 * Domain risk categories.
 */
export type DomainRiskCategory = 'banking' | 'financial' | 'healthcare' | 'government' | 'shopping' | 'social_media' | 'news' | 'search' | 'unknown';
/**
 * Domain risk levels.
 */
export declare const DOMAIN_RISK: Record<DomainRiskCategory, number>;
/**
 * Governance decision for a browser action.
 */
export type BrowserDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
/**
 * Result of governance evaluation for an action.
 */
export interface GovernanceResult {
    /** Decision outcome */
    decision: BrowserDecision;
    /** Unique decision ID for audit trail */
    decisionId: string;
    /** Combined risk score (0-1) */
    riskScore: number;
    /** Confidence in decision (0-1) */
    confidence: number;
    /** Risk breakdown */
    riskFactors: {
        actionRisk: number;
        domainRisk: number;
        sessionRisk: number;
        temporalRisk: number;
        historicalRisk: number;
    };
    /** Explanation for humans */
    explanation: string;
    /** Required governance tier (KO, AV, RU, CA, UM, DR) */
    requiredTier: TongueCode;
    /** Whether Roundtable approval is needed */
    requiresRoundtable: boolean;
    /** Token if action is allowed */
    token?: string;
    /** Token expiry */
    expiresAt?: number;
    /** Pipeline layer outputs (for debugging) */
    pipelineOutputs?: Record<string, unknown>;
}
/**
 * Action execution result.
 */
export interface ActionResult {
    /** Whether action succeeded */
    success: boolean;
    /** Error message if failed */
    error?: string;
    /** Return value from action */
    value?: unknown;
    /** Execution time (ms) */
    duration: number;
    /** New page observation after action */
    observation?: BrowserObservation;
    /** Screenshot after action */
    screenshot?: ScreenshotObservation;
}
/**
 * Browser session configuration.
 */
export interface BrowserSessionConfig {
    /** Session ID */
    sessionId: string;
    /** Agent ID */
    agentId: string;
    /** Agent's Sacred Tongue */
    tongue: TongueCode;
    /** Browser type */
    browserType: 'chromium' | 'firefox' | 'webkit';
    /** Headless mode */
    headless: boolean;
    /** Viewport size */
    viewport: {
        width: number;
        height: number;
    };
    /** User agent override */
    userAgent?: string;
    /** Proxy configuration */
    proxy?: {
        server: string;
        username?: string;
        password?: string;
    };
    /** Default timeout (ms) */
    timeout: number;
    /** Recording enabled */
    recordVideo?: boolean;
    /** Trace enabled */
    recordTrace?: boolean;
}
/**
 * Browser session state.
 */
export interface BrowserSessionState {
    /** Session ID */
    sessionId: string;
    /** Current status */
    status: 'initializing' | 'active' | 'paused' | 'terminated';
    /** Start time */
    startedAt: number;
    /** Last action time */
    lastActionAt?: number;
    /** Action count */
    actionCount: number;
    /** Decisions made */
    decisions: {
        allow: number;
        quarantine: number;
        escalate: number;
        deny: number;
    };
    /** Current page URL */
    currentUrl?: string;
    /** Session risk accumulator */
    sessionRisk: number;
    /** Errors encountered */
    errorCount: number;
}
/**
 * Action history entry for session memory.
 */
export interface ActionHistoryEntry {
    /** Entry ID */
    id: string;
    /** Action that was evaluated */
    action: BrowserAction;
    /** Governance result */
    governance: GovernanceResult;
    /** Execution result (if executed) */
    result?: ActionResult;
    /** Observation before action */
    observationBefore?: BrowserObservation;
    /** Observation after action */
    observationAfter?: BrowserObservation;
    /** Timestamp */
    timestamp: number;
}
/**
 * Escalation request for human/AI review.
 */
export interface EscalationRequest {
    /** Request ID */
    requestId: string;
    /** Session ID */
    sessionId: string;
    /** Action requiring escalation */
    action: BrowserAction;
    /** Governance result */
    governance: GovernanceResult;
    /** Current observation */
    observation: BrowserObservation;
    /** Escalation level */
    level: 'higher_ai' | 'human';
    /** Requested at */
    requestedAt: number;
    /** Response deadline */
    deadline: number;
}
/**
 * Escalation response from reviewer.
 */
export interface EscalationResponse {
    /** Request ID */
    requestId: string;
    /** Reviewer type */
    reviewer: 'higher_ai' | 'human';
    /** Decision */
    decision: 'approve' | 'deny' | 'modify';
    /** Modified action if applicable */
    modifiedAction?: BrowserAction;
    /** Reason for decision */
    reason: string;
    /** Responded at */
    respondedAt: number;
}
/**
 * Type guard for navigate action.
 */
export declare function isNavigateAction(action: BrowserAction): action is NavigateAction;
/**
 * Type guard for click action.
 */
export declare function isClickAction(action: BrowserAction): action is ClickAction;
/**
 * Type guard for type action.
 */
export declare function isTypeAction(action: BrowserAction): action is TypeAction;
/**
 * Type guard for execute_script action.
 */
export declare function isExecuteScriptAction(action: BrowserAction): action is ExecuteScriptAction;
/**
 * Get action description for logging.
 */
export declare function describeAction(action: BrowserAction): string;
//# sourceMappingURL=types.d.ts.map