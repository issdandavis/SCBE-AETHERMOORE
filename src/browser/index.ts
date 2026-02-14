/**
 * SCBE Browser Agent Module
 * ==========================
 *
 * Browser automation agents governed by the SCBE 14-layer pipeline.
 *
 * Features:
 * - Full DOM observation (elements, forms, dialogs)
 * - Complete action space (navigate, click, type, scroll, etc.)
 * - 14-layer governance evaluation for every action
 * - 4-tier decisions: ALLOW / QUARANTINE / ESCALATE / DENY
 * - Session management with risk tracking
 * - Cross-session learning via Hive Memory export
 * - Escalation to higher AI or human review
 *
 * Usage:
 * ```typescript
 * import { createBrowserAgent, MockBrowserBackend } from './browser';
 *
 * const agent = createBrowserAgent({
 *   agentId: 'agent-001',
 *   tongue: 'KO',
 *   backend: new MockBrowserBackend(),
 * });
 *
 * await agent.startSession('https://example.com');
 *
 * const result = await agent.click('#submit-button');
 * console.log(result.success ? 'Clicked!' : result.error);
 *
 * const summary = await agent.endSession();
 * console.log('Session stats:', summary.statistics);
 * ```
 *
 * @module browser
 * @layer Layers 1-14 (full pipeline)
 * @version 3.0.0
 */

// Types
export type {
  // Observation types
  DOMElementState,
  PageObservation,
  FormObservation,
  FormFieldObservation,
  DialogObservation,
  SensitiveFieldType,
  ScreenshotObservation,
  BrowserObservation,
  NetworkObservation,
  NetworkRequest,
  ConsoleObservation,
  PerformanceObservation,
  // Action types
  BrowserActionBase,
  BrowserActionType,
  NavigateAction,
  ClickAction,
  TypeAction,
  ScrollAction,
  SelectAction,
  HoverAction,
  PressAction,
  ScreenshotAction,
  WaitAction,
  ExecuteScriptAction,
  DownloadAction,
  UploadAction,
  SetCookieAction,
  ClearCookiesAction,
  DialogAcceptAction,
  DialogDismissAction,
  GoBackAction,
  GoForwardAction,
  RefreshAction,
  BrowserAction,
  // Governance types
  DomainRiskCategory,
  BrowserDecision,
  GovernanceResult,
  ActionResult,
  // Session types
  BrowserSessionConfig,
  BrowserSessionState,
  ActionHistoryEntry,
  EscalationRequest,
  EscalationResponse,
} from './types.js';

// Constants
export { ACTION_SENSITIVITY, DOMAIN_RISK } from './types.js';

// Type guards
export {
  isNavigateAction,
  isClickAction,
  isTypeAction,
  isExecuteScriptAction,
  describeAction,
} from './types.js';

// Evaluator
export {
  BrowserActionEvaluator,
  computeRiskScore,
  classifyDomain,
  encodeActionSemantic,
  encodeSessionPosition,
} from './evaluator.js';
export type { EvaluatorOptions } from './evaluator.js';

// Session
export { BrowserSession, createBrowserSession, defaultSessionConfig } from './session.js';
export type {
  SessionStatistics,
  PredictedOutcome,
  SessionSummary,
  HiveMemoryExport,
  SessionEvent,
  SessionEventListener,
} from './session.js';

// Agent
export { BrowserAgent, createBrowserAgent, MockBrowserBackend } from './agent.js';
export type { BrowserBackend, EscalationHandler, BrowserAgentConfig } from './agent.js';

// CDP Backend (SCBEPuppeteer — zero-dependency browser automation)
export { CDPBackend, createCDPBackend } from './cdp-backend.js';
export type { CDPBackendOptions } from './cdp-backend.js';

// WebSocket Client (zero-dependency RFC 6455 client)
export { WSClient } from './ws-client.js';
export type { WSClientOptions, WSReadyState } from './ws-client.js';
