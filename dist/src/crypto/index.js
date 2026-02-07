"use strict";
/**
 * SCBE Cryptographic Module
 * Core encryption and security primitives
 *
 * Includes:
 * - Post-Quantum Cryptography (ML-KEM-768, ML-DSA-65)
 * - Envelope encryption
 * - Key management
 * - Replay protection
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
__exportStar(require("./envelope.js"), exports);
__exportStar(require("./hkdf.js"), exports);
__exportStar(require("./jcs.js"), exports);
__exportStar(require("./kms.js"), exports);
__exportStar(require("./nonceManager.js"), exports);
__exportStar(require("./replayGuard.js"), exports);
__exportStar(require("./bloom.js"), exports);
__exportStar(require("./pqc.js"), exports);
//# sourceMappingURL=index.js.map