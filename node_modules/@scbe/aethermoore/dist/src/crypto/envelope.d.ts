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
    body: any;
};
export declare function createEnvelope(p: CreateParams): Promise<Envelope>;
export type VerifyParams = {
    envelope: Envelope;
    session_id: string;
    allowSkewMs?: number;
};
export declare function verifyEnvelope(p: VerifyParams): Promise<{
    body: any;
}>;
//# sourceMappingURL=envelope.d.ts.map