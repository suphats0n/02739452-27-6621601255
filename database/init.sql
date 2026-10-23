CREATE TABLE IF NOT EXISTS games (
    id BIGSERIAL PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    normalized_title TEXT NOT NULL,
    title TEXT NOT NULL,
    genre TEXT,
    developer TEXT,
    publisher TEXT,
    release_date DATE,
    platform TEXT,
    game_url TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_games_normalized_title ON games (normalized_title);
CREATE INDEX IF NOT EXISTS idx_games_genre ON games (genre);

CREATE TABLE IF NOT EXISTS raw_games (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('freetogame', 'cheapshark', 'wikipedia')),
    source_game_id TEXT NOT NULL,
    canonical_key TEXT NOT NULL REFERENCES games(canonical_key) ON UPDATE CASCADE,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    genre TEXT,
    developer TEXT,
    publisher TEXT,
    release_date DATE,
    platform TEXT,
    game_url TEXT,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, source_game_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_games_source ON raw_games (source);
CREATE INDEX IF NOT EXISTS idx_raw_games_canonical_key ON raw_games (canonical_key);

CREATE TABLE IF NOT EXISTS game_offers (
    id BIGSERIAL PRIMARY KEY,
    game_id BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_offer_id TEXT NOT NULL,
    store_name TEXT,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    normal_price NUMERIC(12, 2),
    sale_price NUMERIC(12, 2),
    discount_percent NUMERIC(6, 2),
    deal_rating NUMERIC(6, 2),
    offer_url TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, source_offer_id),
    CHECK (normal_price IS NULL OR normal_price >= 0),
    CHECK (sale_price IS NULL OR sale_price >= 0),
    CHECK (discount_percent IS NULL OR discount_percent BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_game_offers_game_id ON game_offers (game_id);
CREATE INDEX IF NOT EXISTS idx_game_offers_sale_price ON game_offers (sale_price);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    dag_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'partial_success', 'failed')),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_loaded INTEGER NOT NULL DEFAULT 0,
    failed_sources INTEGER NOT NULL DEFAULT 0,
    quality_passed BOOLEAN NOT NULL DEFAULT FALSE,
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_source_runs (
    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'empty')),
    records_extracted INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    PRIMARY KEY (run_id, source)
);
