"use strict";
/**
 * SCBE Fleet Management System
 *
 * Integrates SCBE security (TrustManager, SpectralIdentity) with
 * AI Workflow Architect's agent orchestration for secure AI fleet management.
 *
 * Features:
 * - Agent registration with spectral identity
 * - Sacred Tongue governance for agent actions
 * - Trust-based task assignment
 * - Fleet-wide security monitoring
 * - Roundtable consensus for critical operations
 * - Polly Pads: Personal agent workspaces with dimensional flux
 * - Swarm coordination with flux ODE dynamics
 *
 * @module fleet
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getXPForNextTier = exports.getNextTier = exports.TIER_THRESHOLDS = exports.PollyPadManager = void 0;
__exportStar(require("./agent-registry"), exports);
__exportStar(require("./fleet-manager"), exports);
__exportStar(require("./governance"), exports);
__exportStar(require("./swarm"), exports);
__exportStar(require("./task-dispatcher"), exports);
// Export types (canonical source for shared types)
__exportStar(require("./types"), exports);
// Export polly-pad specific items (excluding types already exported from ./types)
var polly_pad_1 = require("./polly-pad");
// Polly-pad specific functions and classes
Object.defineProperty(exports, "PollyPadManager", { enumerable: true, get: function () { return polly_pad_1.PollyPadManager; } });
Object.defineProperty(exports, "TIER_THRESHOLDS", { enumerable: true, get: function () { return polly_pad_1.TIER_THRESHOLDS; } });
Object.defineProperty(exports, "getNextTier", { enumerable: true, get: function () { return polly_pad_1.getNextTier; } });
Object.defineProperty(exports, "getXPForNextTier", { enumerable: true, get: function () { return polly_pad_1.getXPForNextTier; } });
//# sourceMappingURL=index.js.map