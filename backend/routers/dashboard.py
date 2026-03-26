"""GET /api/dashboard"""

from __future__ import annotations

from fastapi import APIRouter

from routers.deps import AggDepends, FilterDepends

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(agg: AggDepends, spec: FilterDepends):
    totals = agg.summary_stats(spec)

    # Iron split (crossbar / left post / right post)
    total = totals.get("total_post_shots") or 0
    iron_split = [
        {"name": "Crossbar", "value": int(totals.get("crossbar") or 0)},
        {"name": "Left Post", "value": int(totals.get("left_post") or 0)},
        {"name": "Right Post", "value": int(totals.get("right_post") or 0)},
    ]

    # Situation split (EV / PP / PK)
    situation_split = [
        {"name": "Even Strength", "value": int(totals.get("ev") or 0)},
        {"name": "Power Play", "value": int(totals.get("pp") or 0)},
        {"name": "Penalty Kill", "value": int(totals.get("pk") or 0)},
    ]

    # Top 10 players
    player_df = agg.player_summary(spec)
    if not player_df.empty:
        top = (
            player_df.sort_values("post_shots", ascending=False)
            .head(10)
            .fillna(0)
        )
        top_players = top.to_dict(orient="records")
    else:
        top_players = []

    return {
        "totals": {k: (v if v is not None else 0) for k, v in totals.items()},
        "iron_split": iron_split,
        "situation_split": situation_split,
        "top_players": top_players,
    }
