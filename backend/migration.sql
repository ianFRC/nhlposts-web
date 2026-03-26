-- Supabase / Postgres migration for NHL Post & Crossbar Shot Analyzer
-- Run once in the Supabase SQL editor to create all tables.

CREATE TABLE IF NOT EXISTS games (
    game_id          BIGINT  PRIMARY KEY,
    season           TEXT    NOT NULL,
    game_type        INTEGER NOT NULL,
    game_date        TEXT    NOT NULL,
    home_team_id     INTEGER NOT NULL,
    home_team_abbrev TEXT    NOT NULL,
    away_team_id     INTEGER NOT NULL,
    away_team_abbrev TEXT    NOT NULL,
    game_state       TEXT    NOT NULL,
    ingested         BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_games_season   ON games(season);
CREATE INDEX IF NOT EXISTS idx_games_date     ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_ingested ON games(ingested);

CREATE TABLE IF NOT EXISTS players (
    player_id      BIGINT  PRIMARY KEY,
    first_name     TEXT    NOT NULL,
    last_name      TEXT    NOT NULL,
    position_code  TEXT    NOT NULL,
    position_group TEXT    NOT NULL,
    team_abbrev    TEXT    NOT NULL DEFAULT '',
    team_id        INTEGER NOT NULL DEFAULT 0,
    shoots         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS post_shots (
    id                  BIGSERIAL PRIMARY KEY,
    event_id            BIGINT           NOT NULL,
    game_id             BIGINT           NOT NULL,
    season              TEXT             NOT NULL,
    game_date           TEXT             NOT NULL,
    period              INTEGER          NOT NULL,
    period_type         TEXT             NOT NULL,
    time_in_period      TEXT             NOT NULL,
    time_seconds        INTEGER          NOT NULL,
    reason              TEXT             NOT NULL,
    shot_type           TEXT             NOT NULL DEFAULT '',
    x_coord             DOUBLE PRECISION,
    y_coord             DOUBLE PRECISION,
    zone_code           TEXT             NOT NULL DEFAULT '',
    away_skaters        INTEGER          NOT NULL DEFAULT 5,
    home_skaters        INTEGER          NOT NULL DEFAULT 5,
    away_goalie_in_net  BOOLEAN          NOT NULL DEFAULT true,
    home_goalie_in_net  BOOLEAN          NOT NULL DEFAULT true,
    strength            TEXT             NOT NULL DEFAULT '5v5',
    strength_state      TEXT             NOT NULL DEFAULT 'EV',
    shooting_player_id  BIGINT           NOT NULL,
    goalie_in_net_id    BIGINT,
    event_owner_team_id INTEGER          NOT NULL,
    home_team_id        INTEGER          NOT NULL,
    away_team_id        INTEGER          NOT NULL,
    is_home             BOOLEAN          NOT NULL DEFAULT false,
    UNIQUE(event_id, game_id)
);

CREATE INDEX IF NOT EXISTS idx_ps_player   ON post_shots(shooting_player_id);
CREATE INDEX IF NOT EXISTS idx_ps_season   ON post_shots(season);
CREATE INDEX IF NOT EXISTS idx_ps_date     ON post_shots(game_date);
CREATE INDEX IF NOT EXISTS idx_ps_team     ON post_shots(event_owner_team_id);
CREATE INDEX IF NOT EXISTS idx_ps_strength ON post_shots(strength_state);
CREATE INDEX IF NOT EXISTS idx_ps_reason   ON post_shots(reason);

CREATE TABLE IF NOT EXISTS player_game_log (
    player_id  BIGINT  NOT NULL,
    game_id    BIGINT  NOT NULL,
    game_date  TEXT    NOT NULL,
    season     TEXT    NOT NULL,
    game_type  INTEGER NOT NULL,
    shots      INTEGER NOT NULL DEFAULT 0,
    goals      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, game_id)
);

CREATE INDEX IF NOT EXISTS idx_pgl_player_season ON player_game_log(player_id, season);
CREATE INDEX IF NOT EXISTS idx_pgl_date          ON player_game_log(game_date);

-- Used to track sync state (e.g. "GP fetched for player X in season Y")
CREATE TABLE IF NOT EXISTS sync_metadata (
    key        TEXT        PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL,
    ttl_hours  INTEGER     NOT NULL
);
