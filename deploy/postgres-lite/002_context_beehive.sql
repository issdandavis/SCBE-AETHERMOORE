-- SCBE context beehive — optional semantic index over raw truth.
-- Stores pointers, hashes, reversible byte evidence, and semantic overlays.
-- Raw files/logs remain authoritative; this table is an agent routing index.

CREATE TABLE IF NOT EXISTS scbe_context_cells (
    cell_id TEXT PRIMARY KEY,
    source_hash TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_span TEXT NOT NULL DEFAULT '',
    surface_text TEXT NOT NULL DEFAULT '',
    byte_hex TEXT NOT NULL DEFAULT '',
    tongue_route TEXT NOT NULL DEFAULT 'KO',
    semantic_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_role TEXT NOT NULL DEFAULT '',
    positive_embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
    negative_embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
    polarity TEXT NOT NULL DEFAULT 'neutral',
    storage_tier TEXT NOT NULL DEFAULT 'hot_index',
    raw_pointer TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT scbe_context_cells_polarity_chk
        CHECK (polarity IN ('neutral','positive','negative','double_positive','double_negative'))
);

CREATE TABLE IF NOT EXISTS scbe_context_edges (
    edge_id TEXT PRIMARY KEY,
    from_cell_id TEXT NOT NULL REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE,
    to_cell_id TEXT NOT NULL REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE,
    edge_kind TEXT NOT NULL,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_source_hash ON scbe_context_cells(source_hash);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_tongue_route ON scbe_context_cells(tongue_route);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_polarity ON scbe_context_cells(polarity);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_semantic_roles
    ON scbe_context_cells USING GIN (semantic_roles);

INSERT INTO scbe_schema_meta (key, value)
VALUES ('context_beehive_schema_version', 'scbe_context_beehive_v1')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
