"""Data management endpoints: filter options, sync status, manual sync trigger."""

from __future__ import annotations

import logging
import os
import threading

from fastapi import APIRouter, Header, HTTPException

from routers.deps import StoreDepends

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/filter-options")
def get_filter_options(store: StoreDepends):
    return store.get_filter_options()


@router.get("/sync/status")
def get_sync_status(store: StoreDepends):
    return store.get_sync_status()


@router.post("/sync")
def trigger_sync(
    store: StoreDepends,
    x_sync_secret: str | None = Header(default=None),
):
    """Trigger an incremental sync in a background thread. Protected by secret header."""
    expected = os.environ.get("SYNC_SECRET")
    if expected and x_sync_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid sync secret")

    def _run_sync():
        try:
            from api.client import NHLClient
            from ingestion.season import SeasonFetcher
            from ingestion.games import GameIngester
            from ingestion.players import PlayerResolver

            seasons = os.environ.get("SYNC_SEASONS", "20242025,20252026").split(",")

            with NHLClient() as client:
                fetcher = SeasonFetcher(store, client)
                ingester = GameIngester(store, client)
                resolver = PlayerResolver(store, client)

                for season in seasons:
                    logger.info("Sync: discovering games for %s", season)
                    fetcher.fetch_season(season)

                    pending = store.get_pending_games(season=season)
                    if pending:
                        game_ids = [row["game_id"] for row in pending]
                        result = ingester.ingest_batch(game_ids)
                        logger.info(
                            "Sync: ingested %d games, %d post shots",
                            result.games_processed, result.post_shots_found,
                        )

                for season in seasons:
                    resolver.fetch_all_rosters(season)
                    pairs = store.get_distinct_player_seasons(season=season)
                    resolver.fetch_games_played_for_players(pairs)
                    resolver.resolve_unknown_players(season)

            store.mark_sync_complete()
            logger.info("Sync complete")
        except Exception as exc:
            logger.error("Sync failed: %s", exc, exc_info=True)

    thread = threading.Thread(target=_run_sync, daemon=True)
    thread.start()
    return {"status": "sync started"}
