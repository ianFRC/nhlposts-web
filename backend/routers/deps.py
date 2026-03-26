"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, Query

from analysis.aggregator import Aggregator
from analysis.filters import FilterSpec
from db.postgres import PostgresStore

# Singleton set by main.py during lifespan startup
_store: PostgresStore | None = None


def set_store(store: PostgresStore | None) -> None:
    global _store
    _store = store


def get_store() -> PostgresStore:
    assert _store is not None, "Store not initialised"
    return _store


def get_aggregator(store: PostgresStore = Depends(get_store)) -> Generator[Aggregator, None, None]:
    conn = store.acquire()
    try:
        yield Aggregator(conn)
    finally:
        store.release(conn)


def filter_spec_from_params(
    seasons: Annotated[list[str] | None, Query()] = None,
    date_from: str | None = None,
    date_to: str | None = None,
    teams: Annotated[list[str] | None, Query()] = None,
    players: Annotated[list[int] | None, Query()] = None,
    positions: Annotated[list[str] | None, Query()] = None,
    shoots: str | None = None,
    reasons: Annotated[list[str] | None, Query()] = None,
    shot_types: Annotated[list[str] | None, Query()] = None,
    strength_states: Annotated[list[str] | None, Query()] = None,
    periods: Annotated[list[int] | None, Query()] = None,
    home_away: str | None = None,
    season_type: int | None = None,
    min_events: int = 1,
    min_gp: int = 0,
    min_shots: int = 0,
    min_post_per_game: float = 0.0,
) -> FilterSpec:
    return FilterSpec(
        seasons=seasons or [],
        date_from=date_from,
        date_to=date_to,
        team_abbrevs=teams or [],
        player_ids=players or [],
        position_groups=positions or [],
        shoots=shoots,
        reasons=reasons or [],
        shot_types=shot_types or [],
        strength_states=strength_states or [],
        periods=periods or [],
        home_away=home_away,
        season_type=season_type,
        min_events=min_events,
        min_games_played=min_gp,
        min_shots=min_shots,
        min_post_per_game=min_post_per_game,
    )


StoreDepends = Annotated[PostgresStore, Depends(get_store)]
AggDepends = Annotated[Aggregator, Depends(get_aggregator)]
FilterDepends = Annotated[FilterSpec, Depends(filter_spec_from_params)]
