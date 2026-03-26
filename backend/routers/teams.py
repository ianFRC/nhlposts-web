"""GET /api/teams"""

from __future__ import annotations

from fastapi import APIRouter

from routers.deps import AggDepends, FilterDepends

router = APIRouter()


@router.get("/teams")
def get_teams(agg: AggDepends, spec: FilterDepends):
    df = agg.team_summary(spec)
    if df.empty:
        return {"teams": []}
    return {"teams": df.fillna(0).to_dict(orient="records")}
