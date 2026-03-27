#!/usr/bin/env python3
"""
One-off script to re-fetch game log (GP) data for all players who had post shots
on a given date. Useful when the nightly sync already ingested the games but
skipped the GP fetch due to the TTL cache.

Usage:
    DATABASE_URL=<supabase_url> python sync/backfill_gp.py
    DATABASE_URL=<supabase_url> python sync/backfill_gp.py --date 2026-03-26
    DATABASE_URL=<supabase_url> python sync/backfill_gp.py --date 2026-03-26 --date 2026-03-25
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.postgres import PostgresStore
from api.client import NHLClient
from ingestion.players import PlayerResolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("backfill_gp")


def get_players_on_dates(store: PostgresStore, dates: list[str]) -> list[tuple[int, str]]:
    """Return distinct (player_id, season) pairs for post shots on the given dates."""
    placeholders = ",".join(["%s"] * len(dates))
    rows = store._exec(
        f"SELECT DISTINCT shooting_player_id, season FROM post_shots WHERE game_date::date IN ({placeholders})",
        dates,
        fetchall=True,
    ) or []
    return [(r["shooting_player_id"], r["season"]) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill GP data for players on given dates")
    parser.add_argument(
        "--date",
        action="append",
        dest="dates",
        metavar="YYYY-MM-DD",
        help="Date to backfill (can be repeated). Defaults to yesterday.",
    )
    args = parser.parse_args()

    dates = args.dates or [(date.today() - timedelta(days=1)).isoformat()]
    logger.info("Backfilling GP for dates: %s", ", ".join(dates))

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    store = PostgresStore(database_url)
    store.ensure_schema()

    pairs = get_players_on_dates(store, dates)
    if not pairs:
        logger.info("No post shots found for those dates — nothing to do")
        store.close()
        return

    logger.info("Found %d player/season pairs to update", len(pairs))

    with NHLClient(rate_limit=0.5) as client:
        resolver = PlayerResolver(store, client)
        n = resolver.fetch_games_played_for_players(pairs, force=True)

    logger.info("Done — re-fetched game logs for %d players", n)
    store.close()


if __name__ == "__main__":
    main()
