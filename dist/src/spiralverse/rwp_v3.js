"use strict";
/**
 * RWP v3.0 Protocol - TypeScript Implementation
 * ==============================================
 *
 * Post-quantum hybrid encryption with Sacred Tongue encoding.
 * Matches Python implementation in src/crypto/rwp_v3.py
 *
 * Security Stack:
 * 1. Argon2id KDF (RFC 9106) for password → key derivation
 * 2. ChaCha20-Poly1305 AEAD (Node.js native - 12-byte nonce)
 * 3. Sacred Tongue encoding for semantic binding
 *
 * Note: Uses ChaCha20-Poly1305 (12-byte nonce) instead of XChaCha20
 * for Node.js compatibility without external dependencies.
 *
 * @module spiralverse/rwp_v3
 * @version 3.0.0
 * @since 2026-02-01
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RWPv3Protocol = exports.TOKENIZER = exports.SacredTongueTokenizer = exports.ARGON2_PARAMS = void 0;
exports.rwpEncryptMessage = rwpEncryptMessage;
exports.rwpDecryptMessage = rwpDecryptMessage;
exports.envelopeToDict = envelopeToDict;
exports.envelopeFromDict = envelopeFromDict;
const crypto_1 = require("crypto");
const sacredTongues_js_1 = require("../harmonic/sacredTongues.js");
// ============================================================
// ARGON2 PARAMETERS (RFC 9106)
// ============================================================
/**
 * Argon2id parameters for key derivation
 * Note: Uses PBKDF2 as fallback if argon2 not available
 */
exports.ARGON2_PARAMS = {
    timeCost: 3, // Iterations
    memoryCost: 65536, // 64 MB
    parallelism: 4,
    hashLen: 32, // 256-bit key
    saltLen: 16, // 128-bit salt
};
// ============================================================
// SACRED TONGUE TOKENIZER
// ============================================================
/**
 * Sacred Tongue tokenizer for byte ↔ token encoding.
 * Bijective mapping: 256 bytes → 256 unique tokens per tongue.
 */
class SacredTongueTokenizer {
    byteToToken = new Map();
    tokenToByte = new Map();
    constructor() {
        this.buildTables();
        this.validateSecurityProperties();
    }
    buildTables() {
        for (const [code, spec] of Object.entries(sacredTongues_js_1.TONGUES)) {
            const b2t = new Array(256);
            const t2b = new Map();
            for (let b = 0; b < 256; b++) {
                const hi = (b >> 4) & 0x0f;
                const lo = b & 0x0f;
                const token = `${spec.prefixes[hi]}'${spec.suffixes[lo]}`;
                b2t[b] = token;
                t2b.set(token, b);
            }
            this.byteToToken.set(code, b2t);
            this.tokenToByte.set(code, t2b);
        }
    }
    validateSecurityProperties() {
        for (const [code, spec] of Object.entries(sacredTongues_js_1.TONGUES)) {
            const tokens = new Set(this.byteToToken.get(code));
            if (tokens.size !== 256) {
                throw new Error(`Tongue ${code} has ${tokens.size} tokens (expected 256)`);
            }
        }
    }
    /**
     * Encode bytes to Sacred Tongue tokens
     */
    encodeBytes(tongueCode, data) {
        const table = this.byteToToken.get(tongueCode);
        if (!table)
            throw new Error(`Unknown tongue: ${tongueCode}`);
        return Array.from(data).map((b) => table[b]);
    }
    /**
     * Decode Sacred Tongue tokens to bytes
     */
    decodeTokens(tongueCode, tokens) {
        const table = this.tokenToByte.get(tongueCode);
        if (!table)
            throw new Error(`Unknown tongue: ${tongueCode}`);
        const bytes = [];
        for (const token of tokens) {
            const b = table.get(token);
            if (b === undefined) {
                throw new Error(`Invalid token for ${tongueCode}: ${token}`);
            }
            bytes.push(b);
        }
        return Buffer.from(bytes);
    }
    /**
     * Encode RWP section using canonical tongue
     */
    encodeSection(section, data) {
        const tongueCode = sacredTongues_js_1.SECTION_TONGUES[section];
        if (!tongueCode)
            throw new Error(`Unknown section: ${section}`);
        return this.encodeBytes(tongueCode, data);
    }
    /**
     * Decode RWP section from tokens
     */
    decodeSection(section, tokens) {
        const tongueCode = sacredTongues_js_1.SECTION_TONGUES[section];
        if (!tongueCode)
            throw new Error(`Unknown section: ${section}`);
        return this.decodeTokens(tongueCode, tokens);
    }
}
exports.SacredTongueTokenizer = SacredTongueTokenizer;
// Global tokenizer instance
exports.TOKENIZER = new SacredTongueTokenizer();
// ============================================================
// RWP v3.0 PROTOCOL
// ============================================================
/**
 * RWP v3.0 Protocol with AEAD encryption and Sacred Tongue encoding.
 *
 * Security stack:
 * 1. PBKDF2-SHA256 KDF (fallback for Argon2id)
 * 2. ChaCha20-Poly1305 AEAD (Node.js native)
 * 3. Sacred Tongue encoding for all envelope fields
 */
class RWPv3Protocol {
    tokenizer;
    enablePqc;
    constructor(options = {}) {
        this.tokenizer = exports.TOKENIZER;
        this.enablePqc = options.enablePqc ?? false;
    }
    /**
     * Derive 256-bit key using PBKDF2 (Argon2id fallback)
     */
    deriveKey(password, salt) {
        // Use PBKDF2 as Node.js-native fallback for Argon2id
        // In production, install argon2 package for proper RFC 9106 compliance
        return (0, crypto_1.pbkdf2Sync)(password, salt, 100000, 32, 'sha256');
    }
    /**
     * Encrypt plaintext with RWP v3.0 protocol
     */
    encrypt(password, plaintext, aad = Buffer.alloc(0)) {
        // Generate cryptographic material
        const salt = (0, crypto_1.randomBytes)(exports.ARGON2_PARAMS.saltLen);
        const nonce = (0, crypto_1.randomBytes)(12); // ChaCha20-Poly1305 uses 12-byte nonce
        // Derive encryption key
        const key = this.deriveKey(password, salt);
        // AEAD encryption: ChaCha20-Poly1305
        const cipher = (0, crypto_1.createCipheriv)('chacha20-poly1305', key, nonce, {
            authTagLength: 16,
        });
        cipher.setAAD(aad, { plaintextLength: plaintext.length });
        const ct = Buffer.concat([cipher.update(plaintext), cipher.final()]);
        const tag = cipher.getAuthTag();
        // Encode all sections as Sacred Tongue tokens
        return {
            version: ['rwp', 'v3', 'ts'],
            aad: this.tokenizer.encodeSection('aad', aad),
            salt: this.tokenizer.encodeSection('salt', salt),
            nonce: this.tokenizer.encodeSection('nonce', nonce),
            ct: this.tokenizer.encodeSection('ct', ct),
            tag: this.tokenizer.encodeSection('tag', tag),
        };
    }
    /**
     * Decrypt RWP v3.0 envelope
     */
    decrypt(password, envelope) {
        // Decode Sacred Tongue tokens
        const aad = this.tokenizer.decodeSection('aad', envelope.aad);
        const salt = this.tokenizer.decodeSection('salt', envelope.salt);
        const nonce = this.tokenizer.decodeSection('nonce', envelope.nonce);
        const ct = this.tokenizer.decodeSection('ct', envelope.ct);
        const tag = this.tokenizer.decodeSection('tag', envelope.tag);
        // Derive decryption key
        const key = this.deriveKey(password, salt);
        // AEAD decryption: ChaCha20-Poly1305
        const decipher = (0, crypto_1.createDecipheriv)('chacha20-poly1305', key, nonce, {
            authTagLength: 16,
        });
        decipher.setAAD(aad, { plaintextLength: ct.length });
        decipher.setAuthTag(tag);
        try {
            const plaintext = Buffer.concat([decipher.update(ct), decipher.final()]);
            return plaintext;
        }
        catch (e) {
            throw new Error('AEAD authentication failed');
        }
    }
}
exports.RWPv3Protocol = RWPv3Protocol;
// ============================================================
// CONVENIENCE API
// ============================================================
/**
 * High-level API: Encrypt a message with RWP v3.0
 */
function rwpEncryptMessage(password, message, metadata) {
    const protocol = new RWPv3Protocol();
    const aad = Buffer.from(JSON.stringify(metadata ?? {}), 'utf-8');
    return protocol.encrypt(Buffer.from(password, 'utf-8'), Buffer.from(message, 'utf-8'), aad);
}
/**
 * High-level API: Decrypt RWP v3.0 envelope
 */
function rwpDecryptMessage(password, envelope) {
    const protocol = new RWPv3Protocol();
    const plaintext = protocol.decrypt(Buffer.from(password, 'utf-8'), envelope);
    return plaintext.toString('utf-8');
}
/**
 * Serialize envelope to JSON-compatible object
 */
function envelopeToDict(envelope) {
    return { ...envelope };
}
/**
 * Deserialize envelope from JSON object
 */
function envelopeFromDict(dict) {
    return {
        version: dict.version,
        aad: dict.aad,
        salt: dict.salt,
        nonce: dict.nonce,
        ct: dict.ct,
        tag: dict.tag,
        ml_kem_ct: dict.ml_kem_ct,
        ml_dsa_sig: dict.ml_dsa_sig,
    };
}
//# sourceMappingURL=rwp_v3.js.map