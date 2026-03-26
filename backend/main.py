"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.postgres import PostgresStore
from routers.deps import set_store
from routers import dashboard, players, teams, shots, spotlight, shotmap, trend, data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.environ["DATABASE_URL"]
    store = PostgresStore(database_url)
    store.ensure_schema()
    set_store(store)
    logger.info("PostgresStore ready")
    yield
    set_store(None)
    store.close()
    logger.info("PostgresStore closed")


app = FastAPI(title="NHL Post & Crossbar Shot Analyzer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Routers                                                              #
# ------------------------------------------------------------------ #

app.include_router(dashboard.router, prefix="/api")
app.include_router(players.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(shots.router, prefix="/api")
app.include_router(spotlight.router, prefix="/api")
app.include_router(shotmap.router, prefix="/api")
app.include_router(trend.router, prefix="/api")
app.include_router(data.router, prefix="/api")


@app.get("/")
def health():
    return {"status": "ok"}
