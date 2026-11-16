# src/metrics/

`telemetry.ts` — metrics emitter. The backend is chosen by `SCBE_METRICS_BACKEND` (`stdout`, `datadog`, `prom`, `otlp`); **only `stdout` is implemented**, and any other value logs a warning and falls back to stdout.

File-by-file descriptions: [`docs/file-index/src.md`](../../docs/file-index/src.md).
