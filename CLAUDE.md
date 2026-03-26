# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A web-hosted version of an NHL Post & Crossbar Shot Analyzer. It tracks every NHL shot that hit the iron (crossbar, left post, right post) using the public NHL API. The stack is:

- **Backend**: FastAPI (Python) → deployed to Render (free tier)
- **Frontend**: Next.js 14 App Router → deployed to Vercel
- **Database**: Supabase (Postgres)
- **Sync**: GitHub Actions cron job runs nightly to ingest new games

## Development commands

### Backend

```bash
cd backend
pip install -r requirements.txt

# Run locally (requires DATABASE_URL env var pointing at Supabase)
DATABASE_URL=<supabase_url> uvicorn main:app --reload

# Run sync job locally
cd D:\ClaudeWorkspace\NHLPosts_web_version
DATABASE_URL=<supabase_url> python sync/sync_job.py
```

### Frontend

```bash
cd frontend
npm install

# Local dev (backend must be running on 8000)
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

npm run build   # Production build
npm run lint
```

### Database

Run `backend/migration.sql` once in the Supabase SQL editor to create all tables.

## Architecture

### Data flow

```
NHL API → sync_job.py → PostgresStore (Supabase)
                                    ↓
             FastAPI routers → Aggregator → Postgres queries
                                    ↓
                           Next.js frontend (React Query + Zustand)
```

### Backend structure

**`db/postgres.py` — `PostgresStore`**
The central data-access layer. Uses `psycopg2.pool.ThreadedConnectionPool`. Replaces the SQLite `CacheStore` from the original app. Key methods: `bulk_upsert_post_shots`, `upsert_games`, `get_pending_games`, `bulk_upsert_player_game_log`, `is_player_gp_fetched`/`mark_player_gp_fetched` (backed by `sync_metadata` table, not raw JSON cache). `get_raw` always returns `None` and `put_raw` is a no-op — raw API responses are not persisted.

**`analysis/filters.py` — `FilterSpec` + `build_where_clause()`**
`FilterSpec` is a dataclass of all possible filter criteria. `build_where_clause()` turns it into a parameterized SQL `WHERE` fragment. All SQL in this file uses `%s` placeholders (psycopg2). The caller must `JOIN post_shots ps LEFT JOIN players p ... LEFT JOIN games g ...`.

**`analysis/aggregator.py` — `Aggregator`**
Takes a raw psycopg2 connection (not a store). All 9 analytical query methods call `_query(conn, sql, params)` which uses a cursor directly and returns a `pd.DataFrame`. Uses `%s` params and Postgres-native date functions (`to_char` instead of SQLite `strftime`). Boolean columns use `= true`/`= false` syntax (not `= 1`/`= 0`).

**`routers/deps.py`**
Shared FastAPI dependencies. `get_aggregator` checks out a connection from the pool, yields an `Aggregator`, then releases the connection. `filter_spec_from_params` maps URL query params to a `FilterSpec`. All routers import `AggDepends`, `StoreDepends`, `FilterDepends` from here.

**Ingestion modules** (`ingestion/games.py`, `season.py`, `players.py`)
Adapted from the original app. `GameIngester` fetches play-by-play, parses `typeCode=507` missed shots with `reason` in `POST_REASONS`, and calls `store.bulk_upsert_post_shots`. `SeasonFetcher` queries all 32 team schedules. `PlayerResolver` handles rosters + game logs + fuzzy name matching (rapidfuzz).

### Frontend structure

**State**: Zustand store in `src/lib/filterStore.ts`. Holds all sidebar filter values. `getParams()` returns a clean `FilterParams` object (omitting empty/default values) to pass to API calls.

**Data fetching**: React Query in each tab component. Query keys include `getParams()` so data refetches automatically when filters change.

**Routing**: Single dynamic route `src/app/[tab]/page.tsx` handles all 8 tabs. Navigation is plain `<a href>` links (no client-side router push needed — the sidebar stays mounted).

**API client**: `src/lib/api.ts` — all typed fetch wrappers. `NEXT_PUBLIC_API_URL` env var points to the backend.

### SQL conventions

- All params use `%s` (psycopg2), never `?`
- Boolean columns (`is_home`, `away_goalie_in_net`, `home_goalie_in_net`): use `= true` / `= false` in WHERE, and `CASE WHEN ps.is_home THEN ...` in SELECT
- `INSERT ... ON CONFLICT DO NOTHING` (not `INSERT OR IGNORE`)
- Date truncation: `to_char(ps.game_date::date, 'YYYY-MM')` for monthly grouping

### Sync job

`sync/sync_job.py` adds `backend/` to `sys.path` so it can import from the backend packages directly. Runs in order: discover games → ingest pending → fetch rosters → fetch GP logs → resolve unknown players. The `SYNC_SEASONS` env var (comma-separated) controls which seasons are synced.

## Key env vars

| Var | Where | Purpose |
|-----|-------|---------|
| `DATABASE_URL` | backend, GitHub Actions | Supabase Postgres connection string |
| `SYNC_SECRET` | backend, GitHub Actions | Protects the `POST /api/sync` endpoint |
| `SYNC_SEASONS` | backend, GitHub Actions | e.g. `20242025,20252026` |
| `NEXT_PUBLIC_API_URL` | frontend (Vercel) | Render backend URL |
| `RENDER_BACKEND_URL` | GitHub Actions | Used by CI to ping backend after sync |
