#!/usr/bin/env python3
"""
One-off script to re-fetch game log (GP) data for all players who have ever
hit a post. Fixes stale GP counts caused by the nightly sync's TTL cache.

Usage:
    DATABASE_URL=<supabase_url> python sync/backfill_gp.py
"""

from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.postgres import PostgresStore
from api.client import NHLClient
from ingestion.players import PlayerResolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("backfill_gp")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    store = PostgresStore(database_url)
    store.ensure_schema()

    pairs = store.get_distinct_player_seasons()
    logger.info("Found %d player/season pairs to update", len(pairs))

    with NHLClient(rate_limit=0.5) as client:
        resolver = PlayerResolver(store, client)
        n = resolver.fetch_games_played_for_players(pairs, force=True)

    logger.info("Done — re-fetched game logs for %d players", n)
    store.close()


if __name__ == "__main__":
    main()
