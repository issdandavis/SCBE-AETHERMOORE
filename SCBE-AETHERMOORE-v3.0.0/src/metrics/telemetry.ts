import { performance } from 'node:perf_hooks';

type Tags = Record<string, string | number | boolean | undefined>;

export type MetricsBackend = 'stdout' | 'datadog' | 'prom' | 'otlp';
const backend: MetricsBackend = (process.env.SCBE_METRICS_BACKEND as MetricsBackend) || 'stdout';

function fmt(name: string, value: number, tags?: Tags) {
  const t = tags ? Object.entries(tags).map(([k,v]) => `${k}=${v}`).join(' ') : '';
  return `[metric] ${name}=${value} ${t}`.trim();
}

export const metrics = {
  timing(name: string, valueMs: number, tags?: Tags) {
    if (backend === 'stdout') console.log(fmt(name, valueMs, tags));
    // TODO: implement datadog/prom/otlp exporters
  },
  incr(name: string, value = 1, tags?: Tags) {
    if (backend === 'stdout') console.log(fmt(name, value, tags));
  },
  now() { return performance.now(); }
};
