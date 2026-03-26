"""GET /api/spotlight?name=<player_name>"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from routers.deps import AggDepends, StoreDepends, FilterDepends
from analysis.filters import FilterSpec
from ingestion.players import PlayerResolver
from api.client import NHLClient

router = APIRouter()


@router.get("/spotlight")
def get_spotlight(
    name: str,
    agg: AggDepends,
    store: StoreDepends,
    spec: FilterDepends,
):
    # Fuzzy-match the player name against known players
    with NHLClient() as client:
        resolver = PlayerResolver(store, client)
        matches = resolver.resolve_name(name, threshold=60)

    if not matches:
        raise HTTPException(status_code=404, detail=f"No player found matching '{name}'")

    player = matches[0]
    player_id = player.player_id

    # Per-player summary stats
    player_spec = FilterSpec(
        seasons=spec.seasons,
        date_from=spec.date_from,
        date_to=spec.date_to,
        season_type=spec.season_type,
        player_ids=[player_id],
    )
    summary_df = agg.player_summary(player_spec)
    stats = summary_df.fillna(0).to_dict(orient="records")[0] if not summary_df.empty else {}

    # Raw event log (for game-by-game + shot map)
    detail_df = agg.player_detail(player_id, player_spec)

    if not detail_df.empty:
        detail_df = detail_df.fillna("")
        game_log = (
            detail_df.groupby("game_date")
            .agg(
                matchup=("matchup", "first"),
                post_shots=("reason", "count"),
                crossbar=("reason", lambda x: (x == "hit-crossbar").sum()),
                left_post=("reason", lambda x: (x == "hit-left-post").sum()),
                right_post=("reason", lambda x: (x == "hit-right-post").sum()),
            )
            .reset_index()
            .sort_values("game_date", ascending=False)
            .to_dict(orient="records")
        )
        locations = detail_df[detail_df["x_coord"] != ""][
            ["x_coord", "y_coord", "reason", "shot_type", "strength_state"]
        ].to_dict(orient="records")
    else:
        game_log = []
        locations = []

    return {
        "player": {
            "player_id": player.player_id,
            "name": player.full_name,
            "team": player.team_abbrev,
            "position": player.position_code,
            "shoots": player.shoots,
        },
        "stats": stats,
        "game_log": game_log,
        "locations": locations,
    }
