export declare class ReplayGuard {
    private bloom;
    private ttlMs;
    private map;
    constructor({ ttlSeconds, sizeBits, hashes }?: {
        ttlSeconds?: number | undefined;
        sizeBits?: number | undefined;
        hashes?: number | undefined;
    });
    private key;
    checkAndSet(providerId: string, requestId: string, now?: number): boolean;
}
//# sourceMappingURL=replayGuard.d.ts.map