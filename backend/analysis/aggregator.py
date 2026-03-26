"""Aggregator — runs SQL queries against Postgres, returns pandas DataFrames."""

from __future__ import annotations

from typing import Any

import pandas as pd
import psycopg2.extensions

from analysis.filters import FilterSpec, build_where_clause

_BASE_JOIN = """
    FROM post_shots ps
    LEFT JOIN players p ON p.player_id = ps.shooting_player_id
    LEFT JOIN games g ON g.game_id = ps.game_id
"""


def _query(conn: psycopg2.extensions.connection, sql: str, params: list[Any]) -> pd.DataFrame:
    """Execute SQL against a psycopg2 connection and return a DataFrame."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return pd.DataFrame()
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def _gp_subquery(spec: FilterSpec) -> tuple[str, list[Any]]:
    """Correlated subquery counting a player's games played from player_game_log."""
    clauses = ["pgl.player_id = ps.shooting_player_id"]
    params: list[Any] = []

    if spec.seasons:
        placeholders = ",".join(["%s"] * len(spec.seasons))
        clauses.append(f"pgl.season IN ({placeholders})")
        params.extend(spec.seasons)
    if spec.date_from:
        clauses.append("pgl.game_date >= %s")
        params.append(spec.date_from)
    if spec.date_to:
        clauses.append("pgl.game_date <= %s")
        params.append(spec.date_to)
    if spec.season_type is not None:
        clauses.append("pgl.game_type = %s")
        params.append(spec.season_type)

    where = " AND ".join(clauses)
    sql = f"(SELECT COUNT(*) FROM player_game_log pgl WHERE {where})"
    return sql, params


def _shots_subquery(spec: FilterSpec) -> tuple[str, list[Any]]:
    """Correlated subquery summing a player's total shots on goal."""
    clauses = ["pgl.player_id = ps.shooting_player_id"]
    params: list[Any] = []

    if spec.seasons:
        placeholders = ",".join(["%s"] * len(spec.seasons))
        clauses.append(f"pgl.season IN ({placeholders})")
        params.extend(spec.seasons)
    if spec.date_from:
        clauses.append("pgl.game_date >= %s")
        params.append(spec.date_from)
    if spec.date_to:
        clauses.append("pgl.game_date <= %s")
        params.append(spec.date_to)
    if spec.season_type is not None:
        clauses.append("pgl.game_type = %s")
        params.append(spec.season_type)

    where = " AND ".join(clauses)
    sql = f"(SELECT NULLIF(SUM(pgl.shots), 0) FROM player_game_log pgl WHERE {where})"
    return sql, params


def _goals_subquery(spec: FilterSpec) -> tuple[str, list[Any]]:
    """Correlated subquery summing a player's total goals."""
    clauses = ["pgl.player_id = ps.shooting_player_id"]
    params: list[Any] = []

    if spec.seasons:
        placeholders = ",".join(["%s"] * len(spec.seasons))
        clauses.append(f"pgl.season IN ({placeholders})")
        params.extend(spec.seasons)
    if spec.date_from:
        clauses.append("pgl.game_date >= %s")
        params.append(spec.date_from)
    if spec.date_to:
        clauses.append("pgl.game_date <= %s")
        params.append(spec.date_to)
    if spec.season_type is not None:
        clauses.append("pgl.game_type = %s")
        params.append(spec.season_type)

    where = " AND ".join(clauses)
    sql = f"(SELECT NULLIF(SUM(pgl.goals), 0) FROM player_game_log pgl WHERE {where})"
    return sql, params


class Aggregator:
    """Runs analytical queries against Postgres."""

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self._conn = conn

    def player_summary(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""

        gp_subquery, gp_params = _gp_subquery(spec)
        shots_subquery, shots_params = _shots_subquery(spec)
        goals_subquery, goals_params = _goals_subquery(spec)

        having_parts = []
        having_params: list[Any] = []
        if spec.min_events > 1:
            having_parts.append(f"COUNT(*) >= {spec.min_events}")
        if spec.min_games_played > 0:
            having_parts.append(f"{gp_subquery} >= %s")
            having_params.extend(gp_params)
            having_params.append(spec.min_games_played)
        if spec.min_shots > 0:
            having_parts.append(f"{shots_subquery} >= %s")
            having_params.extend(shots_params)
            having_params.append(spec.min_shots)
        if spec.min_post_per_game > 0:
            having_parts.append(
                f"ROUND((CAST(COUNT(*) AS FLOAT) / NULLIF({gp_subquery}, 0))::numeric, 3) >= %s"
            )
            having_params.extend(gp_params)
            having_params.append(spec.min_post_per_game)
        having = f"HAVING {' AND '.join(having_parts)}" if having_parts else ""

        all_params = (gp_params + gp_params + shots_params + shots_params
                      + goals_params + goals_params + params + having_params)

        sql = f"""
        SELECT
            ps.shooting_player_id                                   AS player_id,
            COALESCE(p.first_name || ' ' || p.last_name,
                     ps.shooting_player_id::TEXT)                   AS player_name,
            COALESCE(
                MODE() WITHIN GROUP (ORDER BY
                    CASE WHEN ps.is_home THEN g.home_team_abbrev
                         ELSE g.away_team_abbrev END),
                ''
            )                                                       AS team,
            COALESCE(p.position_code, '')                           AS position,
            COALESCE(p.position_group, '')                          AS pos_group,
            NULLIF({gp_subquery}, 0)                                AS games_played,
            COUNT(DISTINCT ps.game_id)                              AS games_with_post,
            COUNT(*)                                                AS post_shots,
            ROUND(
                (CAST(COUNT(*) AS FLOAT) / NULLIF({gp_subquery}, 0))::numeric,
                3
            )                                                       AS post_per_game,
            {shots_subquery}                                        AS total_shots,
            ROUND(
                (CAST(COUNT(*) AS FLOAT) / {shots_subquery} * 100)::numeric,
                2
            )                                                       AS post_pct_of_shots,
            {goals_subquery}                                        AS total_goals,
            ROUND(
                (CAST(COUNT(*) AS FLOAT) / NULLIF({goals_subquery}, 0))::numeric,
                2
            )                                                       AS posts_per_goal,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post,
            SUM(CASE WHEN ps.strength_state='EV' THEN 1 ELSE 0 END)     AS ev,
            SUM(CASE WHEN ps.strength_state='PP' THEN 1 ELSE 0 END)     AS pp,
            SUM(CASE WHEN ps.strength_state='PK' THEN 1 ELSE 0 END)     AS pk,
            SUM(CASE WHEN ps.strength_state='EN' THEN 1 ELSE 0 END)     AS en,
            SUM(CASE WHEN ps.shot_type='wrist'    THEN 1 ELSE 0 END)    AS wrist,
            SUM(CASE WHEN ps.shot_type='slap'     THEN 1 ELSE 0 END)    AS slap,
            SUM(CASE WHEN ps.shot_type='snap'     THEN 1 ELSE 0 END)    AS snap,
            SUM(CASE WHEN ps.shot_type='tip-in'   THEN 1 ELSE 0 END)    AS tip_in,
            SUM(CASE WHEN ps.shot_type='backhand' THEN 1 ELSE 0 END)    AS backhand,
            SUM(CASE WHEN ps.is_home THEN 1 ELSE 0 END)                 AS home_shots,
            SUM(CASE WHEN NOT ps.is_home THEN 1 ELSE 0 END)             AS away_shots
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.shooting_player_id, p.first_name, p.last_name,
                 p.position_code, p.position_group
        {having}
        """
        df = _query(self._conn, sql, all_params)
        if not df.empty:
            df["crossbar_pct"] = (df["crossbar"] / df["post_shots"] * 100).round(1)
            df["left_pct"] = (df["left_post"] / df["post_shots"] * 100).round(1)
            df["right_pct"] = (df["right_post"] / df["post_shots"] * 100).round(1)
        return df

    def team_summary(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        having = f"HAVING COUNT(*) >= {spec.min_events}" if spec.min_events > 1 else ""
        where_clause = f"WHERE {where}" if where else ""

        sql = f"""
        SELECT
            ps.event_owner_team_id                              AS team_id,
            COALESCE(
                CASE WHEN ps.is_home THEN g.home_team_abbrev
                     ELSE g.away_team_abbrev END,
                ps.event_owner_team_id::TEXT
            )                                                   AS team,
            COUNT(DISTINCT ps.game_id)                          AS games,
            COUNT(*)                                            AS post_shots,
            ROUND((CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT ps.game_id))::numeric, 3)
                                                                AS post_per_game,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post,
            SUM(CASE WHEN ps.strength_state='EV' THEN 1 ELSE 0 END)     AS ev,
            SUM(CASE WHEN ps.strength_state='PP' THEN 1 ELSE 0 END)     AS pp,
            SUM(CASE WHEN ps.strength_state='PK' THEN 1 ELSE 0 END)     AS pk,
            SUM(CASE WHEN ps.strength_state='EN' THEN 1 ELSE 0 END)     AS en
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.event_owner_team_id, g.home_team_abbrev, g.away_team_abbrev, ps.is_home
        {having}
        ORDER BY post_shots DESC
        """
        return _query(self._conn, sql, params)

    def by_shot_type(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""
        sql = f"""
        SELECT
            COALESCE(NULLIF(ps.shot_type,''), 'unknown') AS shot_type,
            COUNT(*)                                      AS post_shots,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.shot_type
        ORDER BY post_shots DESC
        """
        return _query(self._conn, sql, params)

    def by_strength(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""
        sql = f"""
        SELECT
            ps.strength_state,
            ps.strength,
            COUNT(*) AS post_shots,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.strength_state, ps.strength
        ORDER BY post_shots DESC
        """
        return _query(self._conn, sql, params)

    def by_period(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""
        sql = f"""
        SELECT
            ps.period,
            ps.period_type,
            COUNT(*) AS post_shots,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.period, ps.period_type
        ORDER BY ps.period_type DESC, ps.period
        """
        return _query(self._conn, sql, params)

    def by_location(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = (
            f"WHERE {where} AND ps.x_coord IS NOT NULL"
            if where
            else "WHERE ps.x_coord IS NOT NULL"
        )
        sql = f"""
        SELECT
            ps.x_coord,
            ps.y_coord,
            ps.reason,
            ps.shot_type,
            ps.zone_code,
            ps.strength_state,
            COALESCE(p.first_name || ' ' || p.last_name, '') AS player_name,
            COALESCE(CASE WHEN ps.is_home THEN g.home_team_abbrev
                          ELSE g.away_team_abbrev END, '')    AS team
        {_BASE_JOIN}
        {where_clause}
        """
        return _query(self._conn, sql, params)

    def home_away_splits(self, spec: FilterSpec) -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""
        sql = f"""
        SELECT
            ps.shooting_player_id                               AS player_id,
            COALESCE(p.first_name || ' ' || p.last_name,
                     ps.shooting_player_id::TEXT)               AS player_name,
            COALESCE(p.team_abbrev, '')                         AS team,
            SUM(CASE WHEN ps.is_home THEN 1 ELSE 0 END)        AS home,
            SUM(CASE WHEN NOT ps.is_home THEN 1 ELSE 0 END)    AS away,
            COUNT(*)                                            AS total
        {_BASE_JOIN}
        {where_clause}
        GROUP BY ps.shooting_player_id, p.first_name, p.last_name, p.team_abbrev
        HAVING COUNT(*) >= {spec.min_events}
        ORDER BY total DESC
        """
        df = _query(self._conn, sql, params)
        if not df.empty:
            df["home_pct"] = (df["home"] / df["total"] * 100).round(1)
        return df

    def season_trend(self, spec: FilterSpec, granularity: str = "month") -> pd.DataFrame:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""

        if granularity == "week":
            date_expr = "to_char(ps.game_date::date, 'IYYY-IW')"
            date_label = "week"
        else:
            date_expr = "to_char(ps.game_date::date, 'YYYY-MM')"
            date_label = "month"

        sql = f"""
        SELECT
            {date_expr} AS {date_label},
            COUNT(*)    AS post_shots,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post
        {_BASE_JOIN}
        {where_clause}
        GROUP BY {date_expr}
        ORDER BY {date_expr}
        """
        return _query(self._conn, sql, params)

    def player_detail(self, player_id: int, spec: FilterSpec) -> pd.DataFrame:
        spec.player_ids = [player_id]
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""
        sql = f"""
        SELECT
            ps.game_date,
            g.home_team_abbrev || ' vs ' || g.away_team_abbrev AS matchup,
            ps.period,
            ps.period_type,
            ps.time_in_period,
            ps.reason,
            ps.shot_type,
            ps.strength_state,
            ps.strength,
            ps.x_coord,
            ps.y_coord,
            ps.zone_code
        {_BASE_JOIN}
        {where_clause}
        ORDER BY ps.game_date, ps.time_seconds
        """
        return _query(self._conn, sql, params)

    def summary_stats(self, spec: FilterSpec) -> dict[str, Any]:
        where, params = build_where_clause(spec)
        where_clause = f"WHERE {where}" if where else ""

        shots_clauses: list[str] = []
        shots_params: list[Any] = []
        if spec.player_ids:
            placeholders = ",".join(["%s"] * len(spec.player_ids))
            shots_clauses.append(f"pgl.player_id IN ({placeholders})")
            shots_params.extend(spec.player_ids)
        if spec.seasons:
            placeholders = ",".join(["%s"] * len(spec.seasons))
            shots_clauses.append(f"pgl.season IN ({placeholders})")
            shots_params.extend(spec.seasons)
        if spec.date_from:
            shots_clauses.append("pgl.game_date >= %s")
            shots_params.append(spec.date_from)
        if spec.date_to:
            shots_clauses.append("pgl.game_date <= %s")
            shots_params.append(spec.date_to)
        if spec.season_type is not None:
            shots_clauses.append("pgl.game_type = %s")
            shots_params.append(spec.season_type)
        shots_where = f"WHERE {' AND '.join(shots_clauses)}" if shots_clauses else ""
        shots_subquery = (
            f"(SELECT NULLIF(SUM(pgl.shots), 0) FROM player_game_log pgl {shots_where})"
        )

        sql = f"""
        SELECT
            COUNT(*)                                        AS total_post_shots,
            COUNT(DISTINCT ps.shooting_player_id)           AS unique_players,
            COUNT(DISTINCT ps.game_id)                      AS games_with_posts,
            COUNT(DISTINCT ps.event_owner_team_id)          AS unique_teams,
            SUM(CASE WHEN ps.reason='hit-crossbar'   THEN 1 ELSE 0 END) AS crossbar,
            SUM(CASE WHEN ps.reason='hit-left-post'  THEN 1 ELSE 0 END) AS left_post,
            SUM(CASE WHEN ps.reason='hit-right-post' THEN 1 ELSE 0 END) AS right_post,
            SUM(CASE WHEN ps.strength_state='EV' THEN 1 ELSE 0 END)     AS ev,
            SUM(CASE WHEN ps.strength_state='PP' THEN 1 ELSE 0 END)     AS pp,
            SUM(CASE WHEN ps.strength_state='PK' THEN 1 ELSE 0 END)     AS pk,
            {shots_subquery}                                AS total_shots
        {_BASE_JOIN}
        {where_clause}
        """
        df = _query(self._conn, sql, shots_params + params)
        if df.empty:
            return {}
        row = df.iloc[0].to_dict()
        total = row.get("total_post_shots") or 0
        shots = row.get("total_shots")
        row["post_pct_of_shots"] = round(total / shots * 100, 2) if shots else None
        return row
