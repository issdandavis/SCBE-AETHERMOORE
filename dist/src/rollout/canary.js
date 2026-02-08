"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CanaryManager = void 0;
class CanaryManager {
    levels = new Map();
    lastChange = new Map();
    soakMs; // min,max
    constructor(soakWindow = [30 * 60_000, 60 * 60_000]) {
        this.soakMs = soakWindow;
    }
    getLevel(id) {
        return this.levels.get(id) ?? 5;
    }
    canAdvance(id) {
        const last = this.lastChange.get(id) ?? 0;
        const elapsed = Date.now() - last;
        return elapsed >= this.soakMs[0];
    }
    advance(id) {
        const order = [5, 25, 50, 100];
        const cur = this.getLevel(id);
        const idx = order.indexOf(cur);
        if (idx < order.length - 1) {
            this.levels.set(id, order[idx + 1]);
            this.lastChange.set(id, Date.now());
        }
    }
    rollback(id) {
        this.levels.set(id, 5);
        this.lastChange.set(id, Date.now());
    }
}
exports.CanaryManager = CanaryManager;
//# sourceMappingURL=canary.js.map