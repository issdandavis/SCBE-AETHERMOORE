import { performance } from 'node:perf_hooks';

type Tags = Record<string, string | number | boolean | undefined>;

export type MetricsBackend = 'stdout' | 'datadog' | 'prom' | 'otlp';
const backend: MetricsBackend = (process.env.SCBE_METRICS_BACKEND as MetricsBackend) || 'stdout';
let warnedUnsupportedBackend = false;

function warnUnsupportedBackendOnce() {
  if (backend === 'stdout' || warnedUnsupportedBackend) return;
  warnedUnsupportedBackend = true;
  console.warn(
    `[metrics] Backend '${backend}' is configured but not implemented. ` +
      'Metrics will be dropped. Use SCBE_METRICS_BACKEND=stdout or configure an exporter.'
  );
}

function fmt(name: string, value: number, tags?: Tags) {
  const t = tags
    ? Object.entries(tags)
        .map(([k, v]) => `${k}=${v}`)
        .join(' ')
    : '';
  return `[metric] ${name}=${value} ${t}`.trim();
}

export const metrics = {
  timing(name: string, valueMs: number, tags?: Tags) {
    if (backend === 'stdout') console.log(fmt(name, valueMs, tags));
    warnUnsupportedBackendOnce();
  },
  incr(name: string, value = 1, tags?: Tags) {
    if (backend === 'stdout') console.log(fmt(name, value, tags));
    warnUnsupportedBackendOnce();
  },
  now() {
    return performance.now();
  },
};
