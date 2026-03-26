"""PostgresStore: psycopg2-backed data store replacing SQLite CacheStore."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import psycopg2
import psycopg2.extras
import psycopg2.pool

if TYPE_CHECKING:
    from models.event import PostShotEvent
    from models.game import Game
    from models.player import Player

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS sync_metadata (
    key        TEXT        PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL,
    ttl_hours  INTEGER     NOT NULL
);
"""


class PostgresStore:
    """
    Thread-safe data store backed by Postgres (psycopg2).
    Replaces SQLite CacheStore — exposes the same public interface
    used by GameIngester, SeasonFetcher, and PlayerResolver.
    """

    def __init__(self, database_url: str, minconn: int = 1, maxconn: int = 10) -> None:
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn, maxconn, dsn=database_url
        )
        self._lock = threading.Lock()

    def ensure_schema(self) -> None:
        """Create all tables if they don't exist. Safe to call multiple times."""
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                # Execute each statement separately (psycopg2 doesn't support executescript)
                for stmt in _SCHEMA_SQL.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        cur.execute(stmt)
            conn.commit()
        finally:
            self._pool.putconn(conn)

    def acquire(self) -> psycopg2.extensions.connection:
        """Get a connection from the pool. Caller must call release()."""
        return self._pool.getconn()

    def release(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.putconn(conn)

    def get_connection(self) -> psycopg2.extensions.connection:
        """Alias for acquire() — used by Aggregator."""
        return self._pool.getconn()

    def close(self) -> None:
        self._pool.closeall()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _exec(
        self,
        sql: str,
        params: tuple | list | None = None,
        fetchone: bool = False,
        fetchall: bool = False,
    ) -> Any:
        conn = self._pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or ())
                if fetchone:
                    result = cur.fetchone()
                elif fetchall:
                    result = cur.fetchall()
                else:
                    result = None
            conn.commit()
            return result
        finally:
            self._pool.putconn(conn)

    def _execmany(self, sql: str, rows: list) -> None:
        if not rows:
            return
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, sql, rows)
            conn.commit()
        finally:
            self._pool.putconn(conn)

    # ------------------------------------------------------------------ #
    # Games                                                                #
    # ------------------------------------------------------------------ #

    def upsert_game(self, game: "Game") -> None:
        self._exec(
            """
            INSERT INTO games
                (game_id, season, game_type, game_date,
                 home_team_id, home_team_abbrev,
                 away_team_id, away_team_abbrev, game_state)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (game_id) DO NOTHING
            """,
            (
                game.game_id, game.season, game.game_type, game.game_date,
                game.home_team_id, game.home_team_abbrev,
                game.away_team_id, game.away_team_abbrev, game.game_state,
            ),
        )

    def upsert_games(self, games: list["Game"]) -> None:
        rows = [
            (
                g.game_id, g.season, g.game_type, g.game_date,
                g.home_team_id, g.home_team_abbrev,
                g.away_team_id, g.away_team_abbrev, g.game_state,
            )
            for g in games
        ]
        self._execmany(
            """
            INSERT INTO games
                (game_id, season, game_type, game_date,
                 home_team_id, home_team_abbrev,
                 away_team_id, away_team_abbrev, game_state)
            VALUES %s
            ON CONFLICT (game_id) DO UPDATE SET
                game_state = EXCLUDED.game_state
            WHERE games.ingested = false
            """,
            rows,
        )

    def is_game_ingested(self, game_id: int) -> bool:
        row = self._exec(
            "SELECT ingested FROM games WHERE game_id=%s",
            (game_id,),
            fetchone=True,
        )
        return bool(row and row["ingested"])

    def mark_game_ingested(self, game_id: int) -> None:
        self._exec(
            "UPDATE games SET ingested=true WHERE game_id=%s",
            (game_id,),
        )

    def get_pending_games(
        self,
        season: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        clauses = ["ingested=false", "game_state IN ('OFF','FINAL','CRIT')"]
        params: list[Any] = []
        if season:
            clauses.append("season=%s")
            params.append(season)
        if date_from:
            clauses.append("game_date>=%s")
            params.append(date_from)
        if date_to:
            clauses.append("game_date<=%s")
            params.append(date_to)
        sql = f"SELECT * FROM games WHERE {' AND '.join(clauses)} ORDER BY game_date"
        return self._exec(sql, params, fetchall=True) or []

    def get_all_games(
        self,
        season: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if season:
            clauses.append("season=%s")
            params.append(season)
        if date_from:
            clauses.append("game_date>=%s")
            params.append(date_from)
        if date_to:
            clauses.append("game_date<=%s")
            params.append(date_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM games {where} ORDER BY game_date"
        return self._exec(sql, params, fetchall=True) or []

    def season_stats(self, season: str) -> dict[str, int]:
        row = self._exec(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN ingested THEN 1 ELSE 0 END) AS ingested,
                COUNT(*) - SUM(CASE WHEN ingested THEN 1 ELSE 0 END) AS pending
            FROM games WHERE season=%s
            """,
            (season,),
            fetchone=True,
        )
        return dict(row) if row else {"total": 0, "ingested": 0, "pending": 0}

    def cache_summary(self) -> list[dict[str, Any]]:
        rows = self._exec(
            """
            SELECT season,
                   COUNT(*) AS total_games,
                   SUM(CASE WHEN ingested THEN 1 ELSE 0 END) AS ingested_games
            FROM games
            GROUP BY season
            ORDER BY season
            """,
            fetchall=True,
        ) or []
        shot_rows = self._exec(
            "SELECT season, COUNT(*) AS post_shots FROM post_shots GROUP BY season ORDER BY season",
            fetchall=True,
        ) or []
        shot_map = {r["season"]: r["post_shots"] for r in shot_rows}
        return [
            {
                "season": r["season"],
                "total_games": r["total_games"],
                "ingested_games": r["ingested_games"],
                "post_shots": shot_map.get(r["season"], 0),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Players                                                              #
    # ------------------------------------------------------------------ #

    def upsert_player(self, player: "Player") -> None:
        self._exec(
            """
            INSERT INTO players
                (player_id, first_name, last_name, position_code,
                 position_group, team_abbrev, team_id, shoots)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (player_id) DO UPDATE SET
                first_name=EXCLUDED.first_name,
                last_name=EXCLUDED.last_name,
                position_code=EXCLUDED.position_code,
                position_group=EXCLUDED.position_group,
                team_abbrev=EXCLUDED.team_abbrev,
                team_id=EXCLUDED.team_id,
                shoots=EXCLUDED.shoots
            """,
            (
                player.player_id, player.first_name, player.last_name,
                player.position_code, player.position_group,
                player.team_abbrev, player.team_id, player.shoots,
            ),
        )

    def upsert_players(self, players: list["Player"]) -> None:
        rows = [
            (
                p.player_id, p.first_name, p.last_name,
                p.position_code, p.position_group,
                p.team_abbrev, p.team_id, p.shoots,
            )
            for p in players
        ]
        self._execmany(
            """
            INSERT INTO players
                (player_id, first_name, last_name, position_code,
                 position_group, team_abbrev, team_id, shoots)
            VALUES %s
            ON CONFLICT (player_id) DO UPDATE SET
                first_name=EXCLUDED.first_name,
                last_name=EXCLUDED.last_name,
                position_code=EXCLUDED.position_code,
                position_group=EXCLUDED.position_group,
                team_abbrev=EXCLUDED.team_abbrev,
                team_id=EXCLUDED.team_id,
                shoots=EXCLUDED.shoots
            """,
            rows,
        )

    def get_player(self, player_id: int) -> dict | None:
        return self._exec(
            "SELECT * FROM players WHERE player_id=%s",
            (player_id,),
            fetchone=True,
        )

    def get_all_players(self) -> list[dict]:
        return self._exec("SELECT * FROM players", fetchall=True) or []

    def get_unresolved_player_ids(self, season: str | None = None) -> list[int]:
        """Return shooting_player_ids that have no entry in the players table."""
        clauses = ["p.player_id IS NULL"]
        params: list[Any] = []
        if season:
            clauses.append("ps.season=%s")
            params.append(season)
        sql = (
            "SELECT DISTINCT ps.shooting_player_id "
            "FROM post_shots ps "
            "LEFT JOIN players p ON p.player_id = ps.shooting_player_id "
            f"WHERE {' AND '.join(clauses)}"
        )
        rows = self._exec(sql, params, fetchall=True) or []
        return [r["shooting_player_id"] for r in rows]

    # ------------------------------------------------------------------ #
    # Post shots                                                           #
    # ------------------------------------------------------------------ #

    def bulk_upsert_post_shots(self, events: list["PostShotEvent"]) -> None:
        if not events:
            return
        rows = [
            (
                e.event_id, e.game_id, e.season, e.game_date,
                e.period, e.period_type, e.time_in_period, e.time_seconds,
                e.reason, e.shot_type, e.x_coord, e.y_coord, e.zone_code,
                e.away_skaters, e.home_skaters,
                e.away_goalie_in_net, e.home_goalie_in_net,
                e.strength, e.strength_state,
                e.shooting_player_id, e.goalie_in_net_id,
                e.event_owner_team_id, e.home_team_id, e.away_team_id,
                e.is_home,
            )
            for e in events
        ]
        self._execmany(
            """
            INSERT INTO post_shots
                (event_id, game_id, season, game_date,
                 period, period_type, time_in_period, time_seconds,
                 reason, shot_type, x_coord, y_coord, zone_code,
                 away_skaters, home_skaters,
                 away_goalie_in_net, home_goalie_in_net,
                 strength, strength_state,
                 shooting_player_id, goalie_in_net_id,
                 event_owner_team_id, home_team_id, away_team_id,
                 is_home)
            VALUES %s
            ON CONFLICT (event_id, game_id) DO NOTHING
            """,
            rows,
        )

    # ------------------------------------------------------------------ #
    # Player game log                                                      #
    # ------------------------------------------------------------------ #

    def bulk_upsert_player_game_log(
        self, rows: list[tuple[int, int, str, str, int, int, int]]
    ) -> None:
        if not rows:
            return
        self._execmany(
            """
            INSERT INTO player_game_log
                (player_id, game_id, game_date, season, game_type, shots, goals)
            VALUES %s
            ON CONFLICT (player_id, game_id) DO UPDATE SET
                shots=EXCLUDED.shots,
                goals=EXCLUDED.goals
            """,
            rows,
        )

    def is_player_gp_fetched(self, player_id: int, season: str, game_type: int) -> bool:
        key = f"gp:{player_id}:{season}:{game_type}"
        row = self._exec(
            "SELECT fetched_at, ttl_hours FROM sync_metadata WHERE key=%s",
            (key,),
            fetchone=True,
        )
        if row is None:
            return False
        if row["ttl_hours"] == 0:
            return True
        fetched = row["fetched_at"]
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_hours < row["ttl_hours"]

    def mark_player_gp_fetched(self, player_id: int, season: str, game_type: int) -> None:
        key = f"gp:{player_id}:{season}:{game_type}"
        self._exec(
            """
            INSERT INTO sync_metadata (key, fetched_at, ttl_hours)
            VALUES (%s, NOW(), 24)
            ON CONFLICT (key) DO UPDATE SET fetched_at=NOW(), ttl_hours=24
            """,
            (key,),
        )

    def get_distinct_player_seasons(
        self,
        season: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[tuple[int, str]]:
        clauses: list[str] = []
        params: list[Any] = []
        if season:
            clauses.append("season=%s")
            params.append(season)
        if date_from:
            clauses.append("game_date>=%s")
            params.append(date_from)
        if date_to:
            clauses.append("game_date<=%s")
            params.append(date_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT DISTINCT shooting_player_id, season FROM post_shots {where}"
        rows = self._exec(sql, params, fetchall=True) or []
        return [(r["shooting_player_id"], r["season"]) for r in rows]

    def get_players_in_games(self, game_ids: list[int]) -> list[tuple[int, str]]:
        """Return (player_id, season) pairs for players with post shots in these games."""
        if not game_ids:
            return []
        rows = self._exec(
            "SELECT DISTINCT shooting_player_id, season FROM post_shots WHERE game_id = ANY(%s)",
            (game_ids,),
            fetchall=True,
        ) or []
        return [(r["shooting_player_id"], r["season"]) for r in rows]

    # ------------------------------------------------------------------ #
    # Sync metadata (no-op raw cache — not needed in Postgres version)    #
    # ------------------------------------------------------------------ #

    def is_cached(self, key: str, ttl_hours: int | None = None) -> bool:
        """Check sync_metadata for a cached operation."""
        row = self._exec(
            "SELECT fetched_at, ttl_hours FROM sync_metadata WHERE key=%s",
            (key,),
            fetchone=True,
        )
        if row is None:
            return False
        effective_ttl = ttl_hours if ttl_hours is not None else row["ttl_hours"]
        if effective_ttl == 0:
            return True
        fetched = row["fetched_at"]
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_hours < effective_ttl

    def mark_cached(self, key: str, ttl_hours: int = 24) -> None:
        self._exec(
            """
            INSERT INTO sync_metadata (key, fetched_at, ttl_hours)
            VALUES (%s, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET fetched_at=NOW(), ttl_hours=%s
            """,
            (key, ttl_hours, ttl_hours),
        )

    def get_raw(self, key: str) -> dict | None:
        """No persistent raw cache in Postgres version — always returns None."""
        return None

    def put_raw(self, key: str, payload: dict, ttl_hours: int) -> None:
        """Record that a key was fetched (but don't store the payload)."""
        self.mark_cached(key, ttl_hours)

    # ------------------------------------------------------------------ #
    # Filter options (for frontend dropdowns)                             #
    # ------------------------------------------------------------------ #

    def get_filter_options(self) -> dict[str, Any]:
        seasons = [
            r["season"]
            for r in (self._exec(
                "SELECT DISTINCT season FROM post_shots ORDER BY season DESC",
                fetchall=True,
            ) or [])
        ]
        teams = [
            r["team_abbrev"]
            for r in (self._exec(
                "SELECT DISTINCT team_abbrev FROM players WHERE team_abbrev != '' ORDER BY team_abbrev",
                fetchall=True,
            ) or [])
        ]
        players = self._exec(
            """
            SELECT p.player_id,
                   p.first_name || ' ' || p.last_name AS full_name,
                   p.team_abbrev
            FROM players p
            WHERE EXISTS (SELECT 1 FROM post_shots ps WHERE ps.shooting_player_id=p.player_id)
            ORDER BY p.last_name, p.first_name
            """,
            fetchall=True,
        ) or []
        return {
            "seasons": seasons,
            "teams": teams,
            "players": [dict(r) for r in players],
        }

    def get_sync_status(self) -> dict[str, Any]:
        row = self._exec(
            "SELECT fetched_at FROM sync_metadata WHERE key='last_sync'",
            fetchone=True,
        )
        summary = self.cache_summary()
        return {
            "last_sync": row["fetched_at"].isoformat() if row else None,
            "seasons": summary,
        }

    def mark_sync_complete(self) -> None:
        self.mark_cached("last_sync", ttl_hours=0)
