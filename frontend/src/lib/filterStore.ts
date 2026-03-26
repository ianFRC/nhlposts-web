import { create } from "zustand";
import type { FilterParams } from "./types";

interface FilterState extends FilterParams {
  // Setters
  setSeasons: (v: string[]) => void;
  setDateFrom: (v: string | undefined) => void;
  setDateTo: (v: string | undefined) => void;
  setTeams: (v: string[]) => void;
  setPlayers: (v: number[]) => void;
  setPositions: (v: string[]) => void;
  setShoots: (v: string | undefined) => void;
  setReasons: (v: string[]) => void;
  setShotTypes: (v: string[]) => void;
  setStrengthStates: (v: string[]) => void;
  setPeriods: (v: number[]) => void;
  setHomeAway: (v: string | undefined) => void;
  setSeasonType: (v: number | undefined) => void;
  setMinEvents: (v: number) => void;
  setMinGp: (v: number) => void;
  setMinShots: (v: number) => void;
  setMinPostPerGame: (v: number) => void;
  reset: () => void;
  getParams: () => FilterParams;
}

const defaults: FilterParams = {
  seasons: [],
  date_from: undefined,
  date_to: undefined,
  teams: [],
  players: [],
  positions: [],
  shoots: undefined,
  reasons: [],
  shot_types: [],
  strength_states: [],
  periods: [],
  home_away: undefined,
  season_type: undefined,
  min_events: 1,
  min_gp: 0,
  min_shots: 0,
  min_post_per_game: 0,
};

export const useFilterStore = create<FilterState>((set, get) => ({
  ...defaults,

  setSeasons: (v) => set({ seasons: v }),
  setDateFrom: (v) => set({ date_from: v }),
  setDateTo: (v) => set({ date_to: v }),
  setTeams: (v) => set({ teams: v }),
  setPlayers: (v) => set({ players: v }),
  setPositions: (v) => set({ positions: v }),
  setShoots: (v) => set({ shoots: v }),
  setReasons: (v) => set({ reasons: v }),
  setShotTypes: (v) => set({ shot_types: v }),
  setStrengthStates: (v) => set({ strength_states: v }),
  setPeriods: (v) => set({ periods: v }),
  setHomeAway: (v) => set({ home_away: v }),
  setSeasonType: (v) => set({ season_type: v }),
  setMinEvents: (v) => set({ min_events: v }),
  setMinGp: (v) => set({ min_gp: v }),
  setMinShots: (v) => set({ min_shots: v }),
  setMinPostPerGame: (v) => set({ min_post_per_game: v }),
  reset: () => set(defaults),

  getParams: () => {
    const s = get();
    const p: FilterParams = {};
    if (s.seasons?.length) p.seasons = s.seasons;
    if (s.date_from) p.date_from = s.date_from;
    if (s.date_to) p.date_to = s.date_to;
    if (s.teams?.length) p.teams = s.teams;
    if (s.players?.length) p.players = s.players;
    if (s.positions?.length) p.positions = s.positions;
    if (s.shoots) p.shoots = s.shoots;
    if (s.reasons?.length) p.reasons = s.reasons;
    if (s.shot_types?.length) p.shot_types = s.shot_types;
    if (s.strength_states?.length) p.strength_states = s.strength_states;
    if (s.periods?.length) p.periods = s.periods;
    if (s.home_away) p.home_away = s.home_away;
    if (s.season_type) p.season_type = s.season_type;
    if (s.min_events && s.min_events > 1) p.min_events = s.min_events;
    if (s.min_gp && s.min_gp > 0) p.min_gp = s.min_gp;
    if (s.min_shots && s.min_shots > 0) p.min_shots = s.min_shots;
    if (s.min_post_per_game && s.min_post_per_game > 0) p.min_post_per_game = s.min_post_per_game;
    return p;
  },
}));
