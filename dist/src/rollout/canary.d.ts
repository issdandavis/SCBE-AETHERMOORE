type Level = 5 | 25 | 50 | 100;
type ProviderId = string;
export declare class CanaryManager {
    private levels;
    private lastChange;
    private soakMs;
    constructor(soakWindow?: [number, number]);
    getLevel(id: ProviderId): Level;
    canAdvance(id: ProviderId): boolean;
    advance(id: ProviderId): void;
    rollback(id: ProviderId): void;
}
export {};
//# sourceMappingURL=canary.d.ts.map