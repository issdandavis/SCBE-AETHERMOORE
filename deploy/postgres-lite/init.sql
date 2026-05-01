-- SCBE Postgres lite — runs once on first container init.
-- Billing and other stores remain SQLite by default; this DB is for optional features.

CREATE TABLE IF NOT EXISTS scbe_schema_meta (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO scbe_schema_meta (key, value)
VALUES ('schema_version', 'scbe_postgres_lite_v1')
ON CONFLICT (key) DO NOTHING;
