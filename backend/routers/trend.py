"""GET /api/trend"""

from __future__ import annotations

from fastapi import APIRouter

from routers.deps import AggDepends, FilterDepends

router = APIRouter()


@router.get("/trend")
def get_trend(
    agg: AggDepends,
    spec: FilterDepends,
    granularity: str = "month",
):
    if granularity not in ("week", "month"):
        granularity = "month"

    df = agg.season_trend(spec, granularity=granularity)
    return {"rows": df.fillna(0).to_dict(orient="records") if not df.empty else []}
