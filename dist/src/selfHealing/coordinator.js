"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.HealingCoordinator = void 0;
const quickFixBot_js_1 = require("./quickFixBot.js");
const deepHealing_js_1 = require("./deepHealing.js");
class HealingCoordinator {
    quick = new quickFixBot_js_1.QuickFixBot();
    deep = new deepHealing_js_1.DeepHealing();
    async handleFailure(failure) {
        const quick = await this.quick.attemptFix(failure);
        const deep = await this.deep.diagnose(failure);
        // Coordination policy: prefer deep when available; cherry-pick quick successes
        return { quick, deep, decision: 'prefer_deep_if_ready' };
    }
}
exports.HealingCoordinator = HealingCoordinator;
//# sourceMappingURL=coordinator.js.map