"use strict";
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
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.Feistel = void 0;
/**
 * src/core/Feistel.ts
 * Balanced Feistel Network for Intent Modulation
 * Integrates with SCBE-AETHERMOORE Layer 0 (Pre-processing)
 */
const crypto = __importStar(require("crypto"));
class Feistel {
    rounds;
    constructor(rounds = 6) {
        this.rounds = rounds;
    }
    roundFunction(right, roundKey) {
        const hmac = crypto.createHmac('sha256', roundKey);
        hmac.update(right);
        const digest = hmac.digest();
        if (digest.length >= right.length) {
            return digest.subarray(0, right.length);
        }
        else {
            const repeatCount = Math.ceil(right.length / digest.length);
            return Buffer.alloc(right.length, Buffer.concat(Array(repeatCount).fill(digest)));
        }
    }
    xorBuffers(a, b) {
        const length = Math.min(a.length, b.length);
        const result = Buffer.alloc(length);
        for (let i = 0; i < length; i++) {
            result[i] = a[i] ^ b[i];
        }
        return result;
    }
    encrypt(data, key) {
        let workingBuffer = Buffer.from(data);
        if (workingBuffer.length % 2 !== 0) {
            workingBuffer = Buffer.concat([workingBuffer, Buffer.from([0])]);
        }
        const halfLen = workingBuffer.length / 2;
        let left = Buffer.from(workingBuffer.subarray(0, halfLen));
        let right = Buffer.from(workingBuffer.subarray(halfLen));
        const masterKeyBuf = crypto.createHash('sha256').update(key).digest();
        for (let i = 0; i < this.rounds; i++) {
            const roundKey = crypto
                .createHmac('sha256', masterKeyBuf)
                .update(Buffer.from([i]))
                .digest();
            const nextLeft = right;
            const fOutput = this.roundFunction(right, roundKey);
            const nextRight = this.xorBuffers(left, fOutput);
            left = nextLeft;
            right = nextRight;
        }
        return Buffer.concat([left, right]);
    }
    decrypt(data, key) {
        const halfLen = data.length / 2;
        let left = Buffer.from(data.subarray(0, halfLen));
        let right = Buffer.from(data.subarray(halfLen));
        const masterKeyBuf = crypto.createHash('sha256').update(key).digest();
        for (let i = this.rounds - 1; i >= 0; i--) {
            const roundKey = crypto
                .createHmac('sha256', masterKeyBuf)
                .update(Buffer.from([i]))
                .digest();
            const prevRight = left;
            const fOutput = this.roundFunction(left, roundKey);
            const prevLeft = this.xorBuffers(right, fOutput);
            left = prevLeft;
            right = prevRight;
        }
        return Buffer.concat([left, right]);
    }
}
exports.Feistel = Feistel;
//# sourceMappingURL=Feistel.js.map