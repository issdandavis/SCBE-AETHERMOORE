import { performance } from 'node:perf_hooks';
import { metricsLogger } from '../utils/logger.js';

type Tags = Record<string, string | number | boolean | undefined>;

export type MetricsBackend = 'stdout' | 'datadog' | 'prom' | 'otlp';
const backend: MetricsBackend = (process.env.SCBE_METRICS_BACKEND as MetricsBackend) || 'stdout';

/**
 * Filter out undefined values from tags
 */
function filterTags(tags?: Tags): Record<string, string | number | boolean> | undefined {
  if (!tags) return undefined;
  const filtered: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(tags)) {
    if (v !== undefined) {
      filtered[k] = v;
    }
  }
  return Object.keys(filtered).length > 0 ? filtered : undefined;
}

export const metrics = {
  timing(name: string, valueMs: number, tags?: Tags) {
    if (backend === 'stdout') {
      metricsLogger.timing(name, valueMs, filterTags(tags));
    }
    // Future: implement datadog/prom/otlp exporters
  },
  incr(name: string, value = 1, tags?: Tags) {
    if (backend === 'stdout') {
      metricsLogger.incr(name, value, filterTags(tags));
    }
  },
  now() {
    return performance.now();
  },
};
