#!/usr/bin/env python3
"""
One-time migration: SQLite cache.db → Supabase Postgres.

Usage:
    DATABASE_URL=postgresql://... SQLITE_PATH=C:/Users/ian/.nhlposts/cache.db python sync/migrate_sqlite_to_postgres.py

The script is idempotent (ON CONFLICT DO NOTHING) so it's safe to re-run.
"""
import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras

SQLITE_PATH = os.environ.get("SQLITE_PATH", "C:/Users/ian/.nhlposts/cache.db")
DATABASE_URL = os.environ["DATABASE_URL"]

# Boolean columns stored as INTEGER (0/1) in SQLite → convert to Python bool for Postgres
POST_SHOTS_BOOL_COLS = {"is_home", "away_goalie_in_net", "home_goalie_in_net"}


def migrate_games(sqlite_cur, pg_cur):
    sqlite_cur.execute(
        "SELECT game_id, season, game_type, game_date, home_team_id, home_team_abbrev, "
        "away_team_id, away_team_abbrev, game_state, ingested FROM games"
    )
    raw_rows = sqlite_cur.fetchall()
    # ingested is INTEGER (0/1) in SQLite → BOOLEAN in Postgres
    rows = [tuple(r[:-1]) + (bool(r[-1]),) for r in raw_rows]
    psycopg2.extras.execute_values(
        pg_cur,
        """
        INSERT INTO games
            (game_id, season, game_type, game_date, home_team_id, home_team_abbrev,
             away_team_id, away_team_abbrev, game_state, ingested)
        VALUES %s
        ON CONFLICT (game_id) DO NOTHING
        """,
        rows,
        page_size=500,
    )
    print(f"  games: {len(rows)} rows")


def migrate_players(sqlite_cur, pg_cur):
    sqlite_cur.execute(
        "SELECT player_id, first_name, last_name, position_code, position_group, "
        "team_abbrev, team_id, shoots FROM players"
    )
    rows = sqlite_cur.fetchall()
    psycopg2.extras.execute_values(
        pg_cur,
        """
        INSERT INTO players
            (player_id, first_name, last_name, position_code, position_group,
             team_abbrev, team_id, shoots)
        VALUES %s
        ON CONFLICT (player_id) DO NOTHING
        """,
        rows,
        page_size=500,
    )
    print(f"  players: {len(rows)} rows")


def migrate_post_shots(sqlite_cur, pg_cur):
    sqlite_cur.execute(
        "SELECT event_id, game_id, season, game_date, period, period_type, "
        "time_in_period, time_seconds, reason, shot_type, x_coord, y_coord, zone_code, "
        "away_skaters, home_skaters, away_goalie_in_net, home_goalie_in_net, "
        "strength, strength_state, shooting_player_id, goalie_in_net_id, "
        "event_owner_team_id, home_team_id, away_team_id, is_home "
        "FROM post_shots"
    )
    raw_rows = sqlite_cur.fetchall()
    # Convert 0/1 integers to Python bool for boolean columns
    # Indices: away_goalie_in_net=15, home_goalie_in_net=16, is_home=24
    rows = []
    for r in raw_rows:
        r = list(r)
        r[15] = bool(r[15])  # away_goalie_in_net
        r[16] = bool(r[16])  # home_goalie_in_net
        r[24] = bool(r[24])  # is_home
        rows.append(tuple(r))

    psycopg2.extras.execute_values(
        pg_cur,
        """
        INSERT INTO post_shots
            (event_id, game_id, season, game_date, period, period_type,
             time_in_period, time_seconds, reason, shot_type, x_coord, y_coord, zone_code,
             away_skaters, home_skaters, away_goalie_in_net, home_goalie_in_net,
             strength, strength_state, shooting_player_id, goalie_in_net_id,
             event_owner_team_id, home_team_id, away_team_id, is_home)
        VALUES %s
        ON CONFLICT (event_id, game_id) DO NOTHING
        """,
        rows,
        page_size=500,
    )
    print(f"  post_shots: {len(rows)} rows")


def migrate_player_game_log(sqlite_cur, pg_cur):
    sqlite_cur.execute(
        "SELECT player_id, game_id, game_date, season, game_type, shots, goals "
        "FROM player_game_log"
    )
    rows = sqlite_cur.fetchall()
    # Chunk into batches of 2000 to avoid memory issues
    batch_size = 2000
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        psycopg2.extras.execute_values(
            pg_cur,
            """
            INSERT INTO player_game_log
                (player_id, game_id, game_date, season, game_type, shots, goals)
            VALUES %s
            ON CONFLICT (player_id, game_id) DO NOTHING
            """,
            batch,
            page_size=500,
        )
        total += len(batch)
        print(f"  player_game_log: {total}/{len(rows)} rows...", end="\r")
    print(f"  player_game_log: {len(rows)} rows")


def main():
    print(f"Reading from: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    print(f"Connecting to Postgres...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cur = pg_conn.cursor()

    try:
        print("Migrating games...")
        migrate_games(sqlite_cur, pg_cur)

        print("Migrating players...")
        migrate_players(sqlite_cur, pg_cur)

        print("Migrating post_shots...")
        migrate_post_shots(sqlite_cur, pg_cur)

        print("Migrating player_game_log...")
        migrate_player_game_log(sqlite_cur, pg_cur)

        pg_conn.commit()
        print("\nDone! All data committed.")
    except Exception as e:
        pg_conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        sqlite_cur.close()
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
