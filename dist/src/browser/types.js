"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DOMAIN_RISK = exports.ACTION_SENSITIVITY = void 0;
exports.isNavigateAction = isNavigateAction;
exports.isClickAction = isClickAction;
exports.isTypeAction = isTypeAction;
exports.isExecuteScriptAction = isExecuteScriptAction;
exports.describeAction = describeAction;
// =============================================================================
// ACTION RISK & GOVERNANCE
// =============================================================================
/**
 * Action sensitivity levels for governance.
 */
exports.ACTION_SENSITIVITY = {
    navigate: 0.3,
    scroll: 0.1,
    hover: 0.1,
    wait: 0.1,
    screenshot: 0.2,
    go_back: 0.2,
    go_forward: 0.2,
    refresh: 0.3,
    click: 0.4,
    select: 0.4,
    press: 0.4,
    type: 0.5,
    dialog_accept: 0.5,
    dialog_dismiss: 0.3,
    download: 0.7,
    upload: 0.8,
    set_cookie: 0.7,
    clear_cookies: 0.6,
    execute_script: 0.9,
};
/**
 * Domain risk levels.
 */
exports.DOMAIN_RISK = {
    banking: 0.9,
    financial: 0.85,
    healthcare: 0.8,
    government: 0.8,
    shopping: 0.6,
    social_media: 0.5,
    news: 0.2,
    search: 0.1,
    unknown: 0.4,
};
// =============================================================================
// EXPORT HELPERS
// =============================================================================
/**
 * Type guard for navigate action.
 */
function isNavigateAction(action) {
    return action.type === 'navigate';
}
/**
 * Type guard for click action.
 */
function isClickAction(action) {
    return action.type === 'click';
}
/**
 * Type guard for type action.
 */
function isTypeAction(action) {
    return action.type === 'type';
}
/**
 * Type guard for execute_script action.
 */
function isExecuteScriptAction(action) {
    return action.type === 'execute_script';
}
/**
 * Get action description for logging.
 */
function describeAction(action) {
    switch (action.type) {
        case 'navigate':
            return `Navigate to ${action.url}`;
        case 'click':
            return `Click on "${action.selector}"`;
        case 'type':
            return `Type ${action.sensitive ? '[SENSITIVE]' : `"${action.text.slice(0, 20)}..."`} into "${action.selector}"`;
        case 'scroll':
            return action.selector ? `Scroll to "${action.selector}"` : 'Scroll page';
        case 'execute_script':
            return 'Execute JavaScript';
        case 'download':
            return `Download from ${action.url}`;
        case 'upload':
            return `Upload ${action.files.length} file(s) to "${action.selector}"`;
        default:
            return `${action.type} action`;
    }
}
//# sourceMappingURL=types.js.map