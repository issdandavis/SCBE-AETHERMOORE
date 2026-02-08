import { JsonValue } from './jcs.js';
import { type RedisClient } from './replayGuard.js';
export interface AAD {
    envelope_version: string;
    env: string;
    provider_id: string;
    model_id: string;
    intent_id: string;
    phase: string;
    ts: number;
    ttl: number;
    content_type: string;
    schema_hash: string;
    canonical_body_hash: string;
    request_id: string;
    replay_nonce: string;
}
export interface Envelope {
    aad: AAD;
    kid: string;
    nonce: string;
    tag: string;
    ciphertext: string;
    salt: string;
}
/** Body type for envelope payloads - JSON-compatible value or string */
export type EnvelopeBody = JsonValue | string;
export type CreateParams = {
    kid: string;
    env: string;
    provider_id: string;
    model_id: string;
    intent_id: string;
    phase: string;
    ttlMs: number;
    content_type: string;
    schema_hash: string;
    request_id: string;
    session_id: string;
    body: EnvelopeBody;
};
/**
 * Configure distributed replay protection with Redis.
 * Call this at startup when deploying multiple instances.
 *
 * @example
 * import Redis from 'ioredis';
 * import { configureReplayGuard } from './crypto/envelope.js';
 *
 * const redis = new Redis(process.env.REDIS_URL);
 * await configureReplayGuard(redis);
 */
export declare function configureReplayGuard(client: RedisClient): Promise<void>;
/**
 * Check if Redis replay protection is configured.
 */
export declare function isDistributedReplayEnabled(): boolean;
export declare function createEnvelope(p: CreateParams): Promise<Envelope>;
export type VerifyParams = {
    envelope: Envelope;
    session_id: string;
    allowSkewMs?: number;
};
export declare function verifyEnvelope(p: VerifyParams): Promise<{
    body: EnvelopeBody;
}>;
//# sourceMappingURL=envelope.d.ts.map