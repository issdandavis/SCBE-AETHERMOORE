"use strict";
/**
 * SCBE Symphonic Cipher - TypeScript Implementation
 *
 * A complete port of the Python Symphonic Cipher to TypeScript,
 * providing feature parity for web and Node.js developers.
 *
 * Components:
 * - Complex: Complex number arithmetic for FFT
 * - FFT: Cooley-Tukey radix-2 Fast Fourier Transform
 * - Feistel: Balanced Feistel network for intent modulation
 * - ZBase32: Human-friendly encoding (Phil Zimmermann)
 * - SymphonicAgent: Audio synthesis simulation
 * - HybridCrypto: Unified signing/verification interface
 *
 * @module symphonic
 * @version 1.0.0
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
exports.quickVerify = exports.quickSign = exports.VERSION = exports.verifyIntent = exports.signIntent = exports.createHybridCrypto = exports.HybridCrypto = exports.createSymphonicAgent = exports.SymphonicAgent = exports.getAlphabet = exports.ZBase32 = exports.createFeistel = exports.Feistel = exports.FFT = exports.Complex = void 0;
// Complex number class
var Complex_js_1 = require("./Complex.js");
Object.defineProperty(exports, "Complex", { enumerable: true, get: function () { return Complex_js_1.Complex; } });
// Fast Fourier Transform
var FFT_js_1 = require("./FFT.js");
Object.defineProperty(exports, "FFT", { enumerable: true, get: function () { return FFT_js_1.FFT; } });
// Feistel Network cipher
var Feistel_js_1 = require("./Feistel.js");
Object.defineProperty(exports, "Feistel", { enumerable: true, get: function () { return Feistel_js_1.Feistel; } });
Object.defineProperty(exports, "createFeistel", { enumerable: true, get: function () { return Feistel_js_1.createFeistel; } });
// Z-Base-32 encoding
var ZBase32_js_1 = require("./ZBase32.js");
Object.defineProperty(exports, "ZBase32", { enumerable: true, get: function () { return ZBase32_js_1.ZBase32; } });
Object.defineProperty(exports, "getAlphabet", { enumerable: true, get: function () { return ZBase32_js_1.getAlphabet; } });
// Symphonic Agent (audio synthesis simulation)
var SymphonicAgent_js_1 = require("./SymphonicAgent.js");
Object.defineProperty(exports, "SymphonicAgent", { enumerable: true, get: function () { return SymphonicAgent_js_1.SymphonicAgent; } });
Object.defineProperty(exports, "createSymphonicAgent", { enumerable: true, get: function () { return SymphonicAgent_js_1.createSymphonicAgent; } });
// Hybrid Crypto (main interface)
var HybridCrypto_js_1 = require("./HybridCrypto.js");
Object.defineProperty(exports, "HybridCrypto", { enumerable: true, get: function () { return HybridCrypto_js_1.HybridCrypto; } });
Object.defineProperty(exports, "createHybridCrypto", { enumerable: true, get: function () { return HybridCrypto_js_1.createHybridCrypto; } });
Object.defineProperty(exports, "signIntent", { enumerable: true, get: function () { return HybridCrypto_js_1.signIntent; } });
Object.defineProperty(exports, "verifyIntent", { enumerable: true, get: function () { return HybridCrypto_js_1.verifyIntent; } });
/**
 * Version of the Symphonic Cipher TypeScript implementation
 */
exports.VERSION = '1.0.0';
/**
 * Quick sign function for simple use cases
 */
function quickSign(intent, key) {
    const { HybridCrypto } = require('./HybridCrypto.js');
    return new HybridCrypto().signCompact(intent, key);
}
exports.quickSign = quickSign;
/**
 * Quick verify function for simple use cases
 */
function quickVerify(intent, signature, key) {
    const { HybridCrypto } = require('./HybridCrypto.js');
    const result = new HybridCrypto().verifyCompact(intent, signature, key);
    return result.valid;
}
exports.quickVerify = quickVerify;
// Dual-Channel Consensus (Audio Module)
__exportStar(require("./audio/index.js"), exports);
//# sourceMappingURL=index.js.map