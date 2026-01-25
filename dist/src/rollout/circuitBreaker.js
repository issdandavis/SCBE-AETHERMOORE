"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CircuitBreaker = void 0;
class CircuitBreaker {
    failRateThreshold;
    windowMs;
    state = 'closed';
    openedAt = 0;
    constructor(failRateThreshold = 0.005, windowMs = 300_000) {
        this.failRateThreshold = failRateThreshold;
        this.windowMs = windowMs;
    }
    getState() { return this.state; }
    evaluate(failureRate) {
        if (this.state === 'open')
            return;
        if (failureRate > this.failRateThreshold) {
            this.state = 'open';
            this.openedAt = Date.now();
        }
    }
    halfOpenIfReady() {
        if (this.state === 'open' && Date.now() - this.openedAt > this.windowMs) {
            this.state = 'half-open';
        }
    }
    close() { this.state = 'closed'; this.openedAt = 0; }
}
exports.CircuitBreaker = CircuitBreaker;
//# sourceMappingURL=circuitBreaker.js.map