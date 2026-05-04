CREATE TABLE IF NOT EXISTS metric_events (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  idempotency_key TEXT,
  name TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  source TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS metric_events_ts_idx ON metric_events (ts);
CREATE INDEX IF NOT EXISTS metric_events_source_idx ON metric_events (source);
CREATE INDEX IF NOT EXISTS metric_events_idempotency_key_idx ON metric_events (idempotency_key);
