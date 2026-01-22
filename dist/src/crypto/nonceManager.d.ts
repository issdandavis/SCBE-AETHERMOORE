export declare function deriveNoncePrefix(kNonce: Buffer, sessionId: string): Buffer;
export declare function nextNonce(prefix: Buffer, sessionId: string): {
    nonce: Buffer;
    counter: number;
};
export declare function resetSessionCounter(sessionId: string): void;
//# sourceMappingURL=nonceManager.d.ts.map