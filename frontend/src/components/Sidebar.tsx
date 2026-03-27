"use client";

import { useQuery } from "@tanstack/react-query";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import { RotateCcw, X } from "lucide-react";

function MultiSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const toggle = (item: string) => {
    if (value.includes(item)) {
      onChange(value.filter((v) => v !== item));
    } else {
      onChange([...value, item]);
    }
  };

  return (
    <div className="mb-3">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => toggle(opt)}
            className={`rounded px-2 py-0.5 text-xs transition-colors ${
              value.includes(opt)
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function DateInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | undefined;
  onChange: (v: string | undefined) => void;
}) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </label>
      <input
        type="date"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || undefined)}
        className="w-full rounded border border-border bg-muted px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
      />
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
  min = 0,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  step?: number;
}) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </label>
      <input
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded border border-border bg-muted px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
      />
    </div>
  );
}

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const store = useFilterStore();
  const { data: opts } = useQuery({
    queryKey: ["filter-options"],
    queryFn: api.filterOptions,
    staleTime: 10 * 60 * 1000,
  });

  return (
    <div className="p-3">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-sm font-bold text-foreground">NHL Post Tracker</h1>
        <div className="flex items-center gap-1">
          <button
            onClick={store.reset}
            title="Reset filters"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent"
          >
            <RotateCcw size={14} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close filters"
              className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent md:hidden"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Seasons */}
      {opts?.seasons && (
        <MultiSelect
          label="Season"
          options={opts.seasons}
          value={store.seasons ?? []}
          onChange={store.setSeasons}
        />
      )}

      {/* Date range */}
      <DateInput label="From Date" value={store.date_from} onChange={store.setDateFrom} />
      <DateInput label="To Date" value={store.date_to} onChange={store.setDateTo} />

      {/* Teams */}
      {opts?.teams && (
        <MultiSelect
          label="Team"
          options={opts.teams}
          value={store.teams ?? []}
          onChange={store.setTeams}
        />
      )}

      {/* Hit location */}
      <MultiSelect
        label="Hit Location"
        options={["hit-crossbar", "hit-left-post", "hit-right-post"]}
        value={store.reasons ?? []}
        onChange={store.setReasons}
      />

      {/* Strength */}
      <MultiSelect
        label="Strength State"
        options={["EV", "PP", "PK", "EN"]}
        value={store.strength_states ?? []}
        onChange={store.setStrengthStates}
      />

      {/* Shot type */}
      <MultiSelect
        label="Shot Type"
        options={["wrist", "slap", "snap", "tip-in", "backhand", "poke"]}
        value={store.shot_types ?? []}
        onChange={store.setShotTypes}
      />

      {/* Period */}
      <MultiSelect
        label="Period"
        options={["1", "2", "3", "4"]}
        value={(store.periods ?? []).map(String)}
        onChange={(v) => store.setPeriods(v.map(Number))}
      />

      {/* Position */}
      <MultiSelect
        label="Position"
        options={["F", "D", "G"]}
        value={store.positions ?? []}
        onChange={store.setPositions}
      />

      {/* Home/Away */}
      <MultiSelect
        label="Home / Away"
        options={["home", "away"]}
        value={store.home_away ? [store.home_away] : []}
        onChange={(v) => store.setHomeAway(v[v.length - 1])}
      />

      {/* Season type */}
      <div className="mb-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Season Type
        </p>
        <div className="flex gap-1">
          {[
            { label: "All", value: undefined },
            { label: "Regular", value: 2 },
            { label: "Playoffs", value: 3 },
          ].map((opt) => (
            <button
              key={String(opt.value)}
              onClick={() => store.setSeasonType(opt.value)}
              className={`flex-1 rounded px-2 py-0.5 text-xs transition-colors ${
                store.season_type === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Thresholds */}
      <hr className="mb-3 border-border" />
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Thresholds
      </p>
      <NumberInput
        label="Min Post Shots"
        value={store.min_events ?? 1}
        onChange={store.setMinEvents}
        min={1}
      />
      <NumberInput
        label="Min GP"
        value={store.min_gp ?? 0}
        onChange={store.setMinGp}
        min={0}
      />
    </div>
  );
}
