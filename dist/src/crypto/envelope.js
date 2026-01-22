"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createEnvelope = createEnvelope;
exports.verifyEnvelope = verifyEnvelope;
const node_crypto_1 = __importDefault(require("node:crypto"));
const hkdf_js_1 = require("./hkdf.js");
const jcs_js_1 = require("./jcs.js");
const nonceManager_js_1 = require("./nonceManager.js");
const kms_js_1 = require("./kms.js");
const replayGuard_js_1 = require("./replayGuard.js");
const telemetry_js_1 = require("../metrics/telemetry.js");
function b64u(buf) {
    return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
function fromB64u(s) {
    s = s.replace(/-/g, '+').replace(/_/g, '/');
    while (s.length % 4)
        s += '=';
    return Buffer.from(s, 'base64');
}
const replay = new replayGuard_js_1.ReplayGuard({
    ttlSeconds: Number(process.env.SCBE_REPLAY_TTL_SECONDS || '600'),
    sizeBits: Number(process.env.SCBE_REPLAY_BLOOM_BITS || '2048'),
    hashes: Number(process.env.SCBE_REPLAY_BLOOM_HASHES || '4'),
});
function sha256Hex(buf) {
    return node_crypto_1.default.createHash('sha256').update(buf).digest('hex');
}
async function createEnvelope(p) {
    const t0 = telemetry_js_1.metrics.now();
    // 1) Canonicalize body (JCS) and hash
    const bodyStr = typeof p.body === 'string' ? p.body : (0, jcs_js_1.canonicalize)(p.body);
    const bodyBuf = Buffer.from(bodyStr, 'utf8');
    const canonical_body_hash = sha256Hex(bodyBuf);
    const aad = {
        envelope_version: 'scbe-v1',
        env: p.env,
        provider_id: p.provider_id,
        model_id: p.model_id,
        intent_id: p.intent_id,
        phase: p.phase,
        ts: Date.now(),
        ttl: p.ttlMs,
        content_type: p.content_type,
        schema_hash: p.schema_hash,
        canonical_body_hash,
        request_id: p.request_id,
        replay_nonce: node_crypto_1.default.randomBytes(16).toString('hex'),
    };
    // 2) Derive subkeys via HKDF: k_enc, k_nonce, k_log
    const ikm = await (0, kms_js_1.getMasterKey)(p.kid);
    const salt = node_crypto_1.default.randomBytes(32); // per-envelope salt; in prod you may pin/rotate by policy
    const infoBase = Buffer.from(`scbe:derivation:v1|env=${p.env}|provider=${p.provider_id}|intent=${p.intent_id}`);
    const k_enc = (0, hkdf_js_1.hkdfSha256)(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=enc')]), 32);
    const k_nonce = (0, hkdf_js_1.hkdfSha256)(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=nonce')]), 32);
    const k_log = (0, hkdf_js_1.hkdfSha256)(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=log')]), 32);
    // k_log reserved for future audit record MACs
    // 3) Nonce discipline
    const prefix = (0, nonceManager_js_1.deriveNoncePrefix)(k_nonce, p.session_id); // 64-bit
    const { nonce } = (0, nonceManager_js_1.nextNonce)(prefix, p.session_id); // 64b || 32b counter => 96-bit
    // 4) AAD canonicalization (hashes only logged in prod)
    const aadStr = (0, jcs_js_1.canonicalize)(aad);
    const aadBuf = Buffer.from(aadStr, 'utf8');
    // 5) Encrypt (AES-256-GCM, 96-bit nonce, complete AAD coverage)
    try {
        const cipher = node_crypto_1.default.createCipheriv('aes-256-gcm', k_enc, nonce);
        cipher.setAAD(aadBuf);
        const ct = Buffer.concat([cipher.update(bodyBuf), cipher.final()]);
        const tag = cipher.getAuthTag();
        const envl = {
            aad,
            kid: p.kid,
            nonce: b64u(nonce),
            tag: b64u(tag),
            ciphertext: b64u(ct),
            salt: b64u(salt),
        };
        telemetry_js_1.metrics.timing('envelope_create_ms', telemetry_js_1.metrics.now() - t0, {
            provider_id: p.provider_id,
            model_id: p.model_id,
            intent_id: p.intent_id,
            phase: p.phase,
        });
        return envl;
    }
    catch (e) {
        telemetry_js_1.metrics.incr('gcm_failures', 1, { op: 'create' });
        throw e;
    }
}
async function verifyEnvelope(p) {
    const t0 = telemetry_js_1.metrics.now();
    const { envelope } = p;
    const allowSkew = p.allowSkewMs ?? 120_000;
    const now = Date.now();
    // 1) Skew window
    const skew = Math.abs(now - envelope.aad.ts);
    if (skew > allowSkew) {
        telemetry_js_1.metrics.incr('replay_rejects', 1, { reason: 'skew', skew_ms: skew });
        throw new Error('skew/replay');
    }
    // 2) Replay guard (provider_id, request_id)
    const ok = replay.checkAndSet(envelope.aad.provider_id, envelope.aad.request_id, now);
    if (!ok) {
        telemetry_js_1.metrics.incr('replay_rejects', 1, { reason: 'duplicate' });
        throw new Error('replay');
    }
    // 3) Key derivation (must bind env/provider/intent)
    const ikm = await (0, kms_js_1.getMasterKey)(envelope.kid);
    const salt = fromB64u(envelope.salt);
    if (salt.length !== 32)
        throw new Error('bad salt size');
    const infoBase = Buffer.from(`scbe:derivation:v1|env=${envelope.aad.env}|provider=${envelope.aad.provider_id}|intent=${envelope.aad.intent_id}`);
    const k_enc = (0, hkdf_js_1.hkdfSha256)(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=enc')]), 32);
    const k_nonce = (0, hkdf_js_1.hkdfSha256)(ikm, salt, Buffer.concat([infoBase, Buffer.from('|k=nonce')]), 32);
    // 4) Nonce re-derive prefix to sanity-check session context (optional)
    const prefix = (0, nonceManager_js_1.deriveNoncePrefix)(k_nonce, p.session_id);
    const nonce = fromB64u(envelope.nonce);
    if (nonce.length !== 12)
        throw new Error('bad nonce size');
    if (!nonce.subarray(0, 8).equals(prefix)) {
        telemetry_js_1.metrics.incr('nonce_prefix_mismatch', 1);
        // Not fatal if topologies differ; choose to fail closed:
        throw new Error('nonce/prefix');
    }
    // 5) Verify AAD and decrypt
    const aadStr = (0, jcs_js_1.canonicalize)(envelope.aad);
    const aadBuf = Buffer.from(aadStr, 'utf8');
    const tag = fromB64u(envelope.tag);
    const ct = fromB64u(envelope.ciphertext);
    try {
        const decipher = node_crypto_1.default.createDecipheriv('aes-256-gcm', k_enc, nonce);
        decipher.setAAD(aadBuf);
        decipher.setAuthTag(tag);
        const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
        telemetry_js_1.metrics.timing('envelope_verify_ms', telemetry_js_1.metrics.now() - t0, {
            provider_id: envelope.aad.provider_id,
            model_id: envelope.aad.model_id,
            intent_id: envelope.aad.intent_id,
            phase: envelope.aad.phase,
        });
        // Fail-to-noise policy: return opaque error details (we already threw on failure)
        const contentType = envelope.aad.content_type || 'application/json';
        const body = contentType.includes('json')
            ? JSON.parse(pt.toString('utf8'))
            : pt.toString('utf8');
        return { body };
    }
    catch (e) {
        telemetry_js_1.metrics.incr('gcm_failures', 1, { op: 'verify' });
        // Fail-to-noise: do not expose differentiating details
        throw new Error('auth-failed');
    }
}
//# sourceMappingURL=envelope.js.map