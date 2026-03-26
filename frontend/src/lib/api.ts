import type {
  DashboardData,
  FilterOptions,
  FilterParams,
  HomeAwayRow,
  PeriodRow,
  PlayerRow,
  ShotLocation,
  ShotTypeRow,
  SituationRow,
  SyncStatus,
  TeamRow,
  TrendRow,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function toQueryString(params: FilterParams): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const v of value) {
        if (v !== undefined && v !== null && v !== "") {
          parts.push(`${key}=${encodeURIComponent(v)}`);
        }
      }
    } else {
      parts.push(`${key}=${encodeURIComponent(value as string | number)}`);
    }
  }
  return parts.length ? `?${parts.join("&")}` : "";
}

async function apiFetch<T>(path: string, params?: FilterParams): Promise<T> {
  const qs = params ? toQueryString(params) : "";
  const res = await fetch(`${BASE}${path}${qs}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  filterOptions: () =>
    apiFetch<FilterOptions>("/api/filter-options"),

  dashboard: (params: FilterParams) =>
    apiFetch<DashboardData>("/api/dashboard", params),

  players: (params: FilterParams) =>
    apiFetch<{ players: PlayerRow[]; sort_by: string }>("/api/players", params),

  teams: (params: FilterParams) =>
    apiFetch<{ teams: TeamRow[] }>("/api/teams", params),

  shotsByType: (params: FilterParams) =>
    apiFetch<{ rows: ShotTypeRow[] }>("/api/shots/by-type", params),

  shotsBySituation: (params: FilterParams) =>
    apiFetch<{ rows: SituationRow[] }>("/api/shots/by-situation", params),

  shotsByPeriod: (params: FilterParams) =>
    apiFetch<{ rows: PeriodRow[] }>("/api/shots/by-period", params),

  shotsByHomeAway: (params: FilterParams) =>
    apiFetch<{ rows: HomeAwayRow[] }>("/api/shots/by-home-away", params),

  spotlight: (name: string, params: FilterParams) =>
    apiFetch<{
      player: { player_id: number; name: string; team: string; position: string; shoots: string; headshot_url: string };
      stats: PlayerRow;
      game_log: { game_date: string; matchup: string; post_shots: number }[];
      locations: ShotLocation[];
      shots: { game_date: string; matchup: string; period: number; period_type: string; time_in_period: string; reason: string; shot_type: string; strength_state: string }[];
    }>("/api/spotlight", { ...params, name } as FilterParams),

  shotmap: (params: FilterParams) =>
    apiFetch<{ locations: ShotLocation[]; zone_counts: Record<string, number> }>(
      "/api/shotmap",
      params,
    ),

  trend: (params: FilterParams) =>
    apiFetch<{ rows: TrendRow[] }>("/api/trend", params),

  syncStatus: () => apiFetch<SyncStatus>("/api/sync/status"),
};
