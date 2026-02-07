"use strict";
/**
 * Gateway Module - Unified SCBE API Gateway
 *
 * Provides single entry point for all SCBE ecosystem services:
 * - 14-layer authorization pipeline
 * - Six Sacred Tongues protocol encoding
 * - Swarm coordination and fleet management
 * - Contact graph routing
 * - Quantum key exchange (when available)
 *
 * @module gateway
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = exports.UnifiedSCBEGateway = void 0;
var unified_api_js_1 = require("./unified-api.js");
Object.defineProperty(exports, "UnifiedSCBEGateway", { enumerable: true, get: function () { return unified_api_js_1.UnifiedSCBEGateway; } });
// Re-export for convenience
var unified_api_js_2 = require("./unified-api.js");
Object.defineProperty(exports, "default", { enumerable: true, get: function () { return __importDefault(unified_api_js_2).default; } });
//# sourceMappingURL=index.js.map