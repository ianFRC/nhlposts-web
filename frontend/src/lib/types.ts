// TypeScript types mirroring the FastAPI response shapes

export interface FilterParams {
  seasons?: string[];
  date_from?: string;
  date_to?: string;
  teams?: string[];
  players?: number[];
  positions?: string[];
  shoots?: string;
  reasons?: string[];
  shot_types?: string[];
  strength_states?: string[];
  periods?: number[];
  home_away?: string;
  season_type?: number;
  min_events?: number;
  min_gp?: number;
  min_shots?: number;
  min_post_per_game?: number;
  sort_by?: string;
  granularity?: string;
}

export interface FilterOptions {
  seasons: string[];
  teams: string[];
  players: { player_id: number; full_name: string; team_abbrev: string }[];
}

export interface TotalsData {
  total_post_shots: number;
  unique_players: number;
  games_with_posts: number;
  unique_teams: number;
  crossbar: number;
  left_post: number;
  right_post: number;
  ev: number;
  pp: number;
  pk: number;
  total_shots: number | null;
  post_pct_of_shots: number | null;
}

export interface IronSplitEntry {
  name: string;
  value: number;
}

export interface PlayerRow {
  player_id: number;
  player_name: string;
  team: string;
  position: string;
  pos_group: string;
  games_played: number | null;
  games_with_post: number;
  post_shots: number;
  post_per_game: number | null;
  total_shots: number | null;
  post_pct_of_shots: number | null;
  total_goals: number | null;
  posts_per_goal: number | null;
  crossbar: number;
  left_post: number;
  right_post: number;
  crossbar_pct: number;
  left_pct: number;
  right_pct: number;
  ev: number;
  pp: number;
  pk: number;
  en: number;
  wrist: number;
  slap: number;
  snap: number;
  tip_in: number;
  backhand: number;
  home_shots: number;
  away_shots: number;
}

export interface TeamRow {
  team_id: number;
  team: string;
  games: number;
  post_shots: number;
  post_per_game: number;
  crossbar: number;
  left_post: number;
  right_post: number;
  ev: number;
  pp: number;
  pk: number;
  en: number;
}

export interface ShotTypeRow {
  shot_type: string;
  post_shots: number;
  crossbar: number;
  left_post: number;
  right_post: number;
}

export interface SituationRow {
  strength_state: string;
  strength: string;
  post_shots: number;
  crossbar: number;
  left_post: number;
  right_post: number;
}

export interface PeriodRow {
  period: number;
  period_type: string;
  post_shots: number;
  crossbar: number;
  left_post: number;
  right_post: number;
}

export interface HomeAwayRow {
  player_id: number;
  player_name: string;
  team: string;
  home: number;
  away: number;
  total: number;
  home_pct: number;
}

export interface ShotLocation {
  x_coord: number;
  y_coord: number;
  reason: string;
  shot_type: string;
  zone_code: string;
  strength_state: string;
  player_name: string;
  team: string;
}

export interface TrendRow {
  month?: string;
  week?: string;
  post_shots: number;
  crossbar: number;
  left_post: number;
  right_post: number;
}

export interface SpotlightPlayer {
  player_id: number;
  name: string;
  team: string;
  position: string;
  shoots: string;
}

export interface SpotlightGameLogEntry {
  game_date: string;
  matchup: string;
  post_shots: number;
  crossbar: number;
  left_post: number;
  right_post: number;
}

export interface SyncStatus {
  last_sync: string | null;
  seasons: { season: string; total_games: number; ingested_games: number; post_shots: number }[];
}

// Dashboard API response
export interface DashboardData {
  totals: TotalsData;
  iron_split: IronSplitEntry[];
  situation_split: IronSplitEntry[];
  top_players: PlayerRow[];
}
