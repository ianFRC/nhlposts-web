"""GET /api/players"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from routers.deps import AggDepends, FilterDepends

router = APIRouter()

_VALID_SORT = {
    "post_shots", "post_per_game", "games_played", "crossbar",
    "left_post", "right_post", "total_shots", "post_pct_of_shots",
}


@router.get("/players")
def get_players(
    agg: AggDepends,
    spec: FilterDepends,
    sort_by: str = "post_shots",
    ascending: bool = False,
):
    if sort_by not in _VALID_SORT:
        sort_by = "post_shots"

    df = agg.player_summary(spec)
    if df.empty:
        return {"players": [], "sort_by": sort_by}

    df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    df = df.fillna(0)
    return {
        "players": df.to_dict(orient="records"),
        "sort_by": sort_by,
    }
