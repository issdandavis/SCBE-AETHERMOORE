type State = 'closed' | 'open' | 'half-open';
export declare class CircuitBreaker {
    private failRateThreshold;
    private windowMs;
    private state;
    private openedAt;
    constructor(failRateThreshold?: number, windowMs?: number);
    getState(): State;
    evaluate(failureRate: number): void;
    halfOpenIfReady(): void;
    close(): void;
}
export {};
//# sourceMappingURL=circuitBreaker.d.ts.map