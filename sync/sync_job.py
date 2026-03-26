#!/usr/bin/env python3
"""
Nightly sync job — runs in GitHub Actions.

Usage:
    cd backend
    DATABASE_URL=<supabase_url> python ../sync/sync_job.py
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure backend/ is on the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.postgres import PostgresStore
from api.client import NHLClient
from ingestion.season import SeasonFetcher
from ingestion.games import GameIngester
from ingestion.players import PlayerResolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sync_job")

# Seasons to sync — extend as new seasons begin
SEASONS = os.environ.get("SYNC_SEASONS", "20242025,20252026").split(",")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    logger.info("Connecting to Postgres...")
    store = PostgresStore(database_url)
    store.ensure_schema()
    logger.info("Schema verified")

    with NHLClient(rate_limit=0.5) as client:
        fetcher = SeasonFetcher(store, client)
        ingester = GameIngester(store, client, workers=3)
        resolver = PlayerResolver(store, client)

        # ── Step 1: Discover all games for each season ────────────────── #
        for season in SEASONS:
            logger.info("Discovering games for season %s...", season)
            games = fetcher.fetch_season(season)
            logger.info("Season %s: %d total games known", season, len(games))

        # ── Step 2: Ingest pending (un-ingested, OFF/FINAL) games ──────── #
        all_new_game_ids: list[int] = []
        for season in SEASONS:
            pending = store.get_pending_games(season=season)
            if not pending:
                logger.info("Season %s: no pending games", season)
                continue

            game_ids = [row["game_id"] for row in pending]
            logger.info("Season %s: ingesting %d pending games...", season, len(game_ids))

            result = ingester.ingest_batch(game_ids)
            all_new_game_ids.extend(result.newly_ingested_game_ids)
            logger.info(
                "Season %s: processed=%d  post_shots=%d  failed=%d",
                season, result.games_processed, result.post_shots_found, result.games_failed,
            )

        # ── Step 3: Fetch rosters for all seasons ─────────────────────── #
        for season in SEASONS:
            logger.info("Fetching rosters for season %s...", season)
            n = resolver.fetch_all_rosters(season)
            logger.info("Season %s: %d players upserted", season, n)

        # ── Step 4: Fetch game logs only for players in newly ingested games #
        if all_new_game_ids:
            pairs = store.get_players_in_games(all_new_game_ids)
            logger.info(
                "Fetching GP for %d players across %d newly ingested games...",
                len(pairs), len(all_new_game_ids),
            )
            n = resolver.fetch_games_played_for_players(pairs)
            logger.info("GP fetched for %d players", n)
        else:
            logger.info("No new games ingested, skipping GP fetch")

        # ── Step 5: Resolve any unknown players ───────────────────────── #
        for season in SEASONS:
            n = resolver.resolve_unknown_players(season)
            if n:
                logger.info("Season %s: resolved %d unknown players", season, n)

    # Mark sync complete in DB
    store.mark_sync_complete()
    logger.info("Sync complete")

    # Print summary
    for row in store.cache_summary():
        logger.info(
            "  %s: %d/%d games ingested, %d post shots",
            row["season"], row["ingested_games"], row["total_games"], row["post_shots"],
        )

    store.close()


if __name__ == "__main__":
    main()
