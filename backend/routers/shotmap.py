"""GET /api/shotmap"""

from __future__ import annotations

from fastapi import APIRouter

from routers.deps import AggDepends, FilterDepends

router = APIRouter()


@router.get("/shotmap")
def get_shotmap(agg: AggDepends, spec: FilterDepends):
    df = agg.by_location(spec)
    if df.empty:
        return {"locations": [], "zone_counts": {}}

    df = df.fillna("")
    locations = df.to_dict(orient="records")

    # Zone breakdown
    zone_counts: dict[str, int] = {}
    for _, row in df.iterrows():
        zone = row.get("zone_code") or "unknown"
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    return {"locations": locations, "zone_counts": zone_counts}
