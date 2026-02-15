"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.WSClient = exports.createCDPBackend = exports.CDPBackend = exports.MockBrowserBackend = exports.createBrowserAgent = exports.BrowserAgent = exports.defaultSessionConfig = exports.createBrowserSession = exports.BrowserSession = exports.encodeSessionPosition = exports.encodeActionSemantic = exports.classifyDomain = exports.computeRiskScore = exports.BrowserActionEvaluator = exports.describeAction = exports.isExecuteScriptAction = exports.isTypeAction = exports.isClickAction = exports.isNavigateAction = exports.DOMAIN_RISK = exports.ACTION_SENSITIVITY = void 0;
// Constants
var types_js_1 = require("./types.js");
Object.defineProperty(exports, "ACTION_SENSITIVITY", { enumerable: true, get: function () { return types_js_1.ACTION_SENSITIVITY; } });
Object.defineProperty(exports, "DOMAIN_RISK", { enumerable: true, get: function () { return types_js_1.DOMAIN_RISK; } });
// Type guards
var types_js_2 = require("./types.js");
Object.defineProperty(exports, "isNavigateAction", { enumerable: true, get: function () { return types_js_2.isNavigateAction; } });
Object.defineProperty(exports, "isClickAction", { enumerable: true, get: function () { return types_js_2.isClickAction; } });
Object.defineProperty(exports, "isTypeAction", { enumerable: true, get: function () { return types_js_2.isTypeAction; } });
Object.defineProperty(exports, "isExecuteScriptAction", { enumerable: true, get: function () { return types_js_2.isExecuteScriptAction; } });
Object.defineProperty(exports, "describeAction", { enumerable: true, get: function () { return types_js_2.describeAction; } });
// Evaluator
var evaluator_js_1 = require("./evaluator.js");
Object.defineProperty(exports, "BrowserActionEvaluator", { enumerable: true, get: function () { return evaluator_js_1.BrowserActionEvaluator; } });
Object.defineProperty(exports, "computeRiskScore", { enumerable: true, get: function () { return evaluator_js_1.computeRiskScore; } });
Object.defineProperty(exports, "classifyDomain", { enumerable: true, get: function () { return evaluator_js_1.classifyDomain; } });
Object.defineProperty(exports, "encodeActionSemantic", { enumerable: true, get: function () { return evaluator_js_1.encodeActionSemantic; } });
Object.defineProperty(exports, "encodeSessionPosition", { enumerable: true, get: function () { return evaluator_js_1.encodeSessionPosition; } });
// Session
var session_js_1 = require("./session.js");
Object.defineProperty(exports, "BrowserSession", { enumerable: true, get: function () { return session_js_1.BrowserSession; } });
Object.defineProperty(exports, "createBrowserSession", { enumerable: true, get: function () { return session_js_1.createBrowserSession; } });
Object.defineProperty(exports, "defaultSessionConfig", { enumerable: true, get: function () { return session_js_1.defaultSessionConfig; } });
// Agent
var agent_js_1 = require("./agent.js");
Object.defineProperty(exports, "BrowserAgent", { enumerable: true, get: function () { return agent_js_1.BrowserAgent; } });
Object.defineProperty(exports, "createBrowserAgent", { enumerable: true, get: function () { return agent_js_1.createBrowserAgent; } });
Object.defineProperty(exports, "MockBrowserBackend", { enumerable: true, get: function () { return agent_js_1.MockBrowserBackend; } });
// CDP Backend (SCBEPuppeteer — zero-dependency browser automation)
var cdp_backend_js_1 = require("./cdp-backend.js");
Object.defineProperty(exports, "CDPBackend", { enumerable: true, get: function () { return cdp_backend_js_1.CDPBackend; } });
Object.defineProperty(exports, "createCDPBackend", { enumerable: true, get: function () { return cdp_backend_js_1.createCDPBackend; } });
// WebSocket Client (zero-dependency RFC 6455 client)
var ws_client_js_1 = require("./ws-client.js");
Object.defineProperty(exports, "WSClient", { enumerable: true, get: function () { return ws_client_js_1.WSClient; } });
//# sourceMappingURL=index.js.map