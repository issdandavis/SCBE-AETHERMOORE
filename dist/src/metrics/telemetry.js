"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.metrics = void 0;
const node_perf_hooks_1 = require("node:perf_hooks");
const logger_js_1 = require("../utils/logger.js");
const backend = process.env.SCBE_METRICS_BACKEND || 'stdout';
/**
 * Filter out undefined values from tags
 */
function filterTags(tags) {
    if (!tags)
        return undefined;
    const filtered = {};
    for (const [k, v] of Object.entries(tags)) {
        if (v !== undefined) {
            filtered[k] = v;
        }
    }
    return Object.keys(filtered).length > 0 ? filtered : undefined;
}
exports.metrics = {
    timing(name, valueMs, tags) {
        if (backend === 'stdout') {
            logger_js_1.metricsLogger.timing(name, valueMs, filterTags(tags));
        }
        // Future: implement datadog/prom/otlp exporters
    },
    incr(name, value = 1, tags) {
        if (backend === 'stdout') {
            logger_js_1.metricsLogger.incr(name, value, filterTags(tags));
        }
    },
    now() {
        return node_perf_hooks_1.performance.now();
    },
};
//# sourceMappingURL=telemetry.js.map