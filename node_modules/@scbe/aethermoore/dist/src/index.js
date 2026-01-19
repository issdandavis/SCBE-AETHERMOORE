"use strict";
/**
 * SCBE-AETHERMOORE v3.0
 * Hyperbolic Geometry-Based Security with 14-Layer Architecture
 *
 * Patent Pending: USPTO #63/961,403
 * Author: Issac Daniel Davis
 *
 * @packageDocumentation
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
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_CONFIG = exports.ARCHITECTURE_LAYERS = exports.PATENT_NUMBER = exports.VERSION = exports.crypto = exports.symphonic = void 0;
// Namespace exports for convenient access (scbe.symphonic, scbe.crypto)
const symphonic = __importStar(require("./symphonic/index.js"));
exports.symphonic = symphonic;
const crypto = __importStar(require("./crypto/index.js"));
exports.crypto = crypto;
// Core Crypto Exports (also available at top level)
__exportStar(require("./crypto/envelope.js"), exports);
__exportStar(require("./crypto/hkdf.js"), exports);
__exportStar(require("./crypto/jcs.js"), exports);
__exportStar(require("./crypto/kms.js"), exports);
__exportStar(require("./crypto/nonceManager.js"), exports);
__exportStar(require("./crypto/replayGuard.js"), exports);
__exportStar(require("./crypto/bloom.js"), exports);
// Metrics Exports
__exportStar(require("./metrics/telemetry.js"), exports);
// Rollout Exports
__exportStar(require("./rollout/canary.js"), exports);
__exportStar(require("./rollout/circuitBreaker.js"), exports);
// Self-Healing Exports
__exportStar(require("./selfHealing/coordinator.js"), exports);
__exportStar(require("./selfHealing/deepHealing.js"), exports);
__exportStar(require("./selfHealing/quickFixBot.js"), exports);
// Version and Metadata
exports.VERSION = '3.0.0';
exports.PATENT_NUMBER = 'USPTO #63/961,403';
exports.ARCHITECTURE_LAYERS = 14;
/**
 * Default SCBE configuration
 */
exports.DEFAULT_CONFIG = {
    enableFullStack: true,
    harmonicScaling: 1.5,
    poincareRadius: 0.99,
    antifragile: true,
};
//# sourceMappingURL=index.js.map