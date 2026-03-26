"""GET /api/shots/* — shot analysis breakdowns."""

from __future__ import annotations

from fastapi import APIRouter

from routers.deps import AggDepends, FilterDepends

router = APIRouter()


@router.get("/shots/by-type")
def by_type(agg: AggDepends, spec: FilterDepends):
    df = agg.by_shot_type(spec)
    return {"rows": df.fillna(0).to_dict(orient="records") if not df.empty else []}


@router.get("/shots/by-situation")
def by_situation(agg: AggDepends, spec: FilterDepends):
    df = agg.by_strength(spec)
    return {"rows": df.fillna(0).to_dict(orient="records") if not df.empty else []}


@router.get("/shots/by-period")
def by_period(agg: AggDepends, spec: FilterDepends):
    df = agg.by_period(spec)
    return {"rows": df.fillna(0).to_dict(orient="records") if not df.empty else []}


@router.get("/shots/by-home-away")
def by_home_away(agg: AggDepends, spec: FilterDepends):
    df = agg.home_away_splits(spec)
    return {"rows": df.fillna(0).to_dict(orient="records") if not df.empty else []}
