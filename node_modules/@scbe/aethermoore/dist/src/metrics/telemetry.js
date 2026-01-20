"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.metrics = void 0;
const node_perf_hooks_1 = require("node:perf_hooks");
const backend = process.env.SCBE_METRICS_BACKEND || 'stdout';
function fmt(name, value, tags) {
    const t = tags ? Object.entries(tags).map(([k, v]) => `${k}=${v}`).join(' ') : '';
    return `[metric] ${name}=${value} ${t}`.trim();
}
exports.metrics = {
    timing(name, valueMs, tags) {
        if (backend === 'stdout')
            console.log(fmt(name, valueMs, tags));
        // TODO: implement datadog/prom/otlp exporters
    },
    incr(name, value = 1, tags) {
        if (backend === 'stdout')
            console.log(fmt(name, value, tags));
    },
    now() { return node_perf_hooks_1.performance.now(); }
};
//# sourceMappingURL=telemetry.js.map