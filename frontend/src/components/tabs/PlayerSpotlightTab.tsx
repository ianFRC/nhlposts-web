"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export function PlayerSpotlightTab() {
  const params = useFilterStore((s) => s.getParams());
  const [name, setName] = useState("");
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["spotlight", search, params],
    queryFn: () => api.spotlight(search, params),
    enabled: search.length > 2,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(name);
  };

  return (
    <div className="space-y-4">
      {/* Search form */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          placeholder="Player name (e.g. Cole Perfetti)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded border border-border bg-muted px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          type="submit"
          className="rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
        >
          Search
        </button>
      </form>

      {isLoading && <div className="text-muted-foreground">Searching...</div>}
      {error && (
        <div className="text-red-400">
          {(error as Error).message.includes("404")
            ? `No player found for "${search}"`
            : (error as Error).message}
        </div>
      )}

      {data && (
        <div className="space-y-4">
          {/* Player header */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="text-xl font-bold">{data.player.name}</h2>
            <p className="text-sm text-muted-foreground">
              {data.player.team} · {data.player.position} · Shoots {data.player.shoots}
            </p>
          </div>

          {/* Stats grid */}
          {data.stats && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Post Shots", value: data.stats.post_shots },
                { label: "GP", value: data.stats.games_played ?? "—" },
                { label: "P/GP", value: data.stats.post_per_game?.toFixed(3) ?? "—" },
                { label: "Crossbar", value: data.stats.crossbar },
                { label: "Left Post", value: data.stats.left_post },
                { label: "Right Post", value: data.stats.right_post },
                { label: "EV", value: data.stats.ev },
                { label: "PP", value: data.stats.pp },
              ].map((s) => (
                <div key={s.label} className="rounded border border-border bg-card p-3">
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="mt-0.5 text-lg font-bold">{s.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Game log */}
          {data.game_log.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-3 text-sm font-semibold">Post Shots Per Game</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart
                  data={data.game_log.slice(0, 30).reverse()}
                  margin={{ left: 5, right: 10, top: 5, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="game_date" angle={-45} textAnchor="end" tick={{ fontSize: 9 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="post_shots" name="Post Shots" fill="#60a5fa" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Shot locations on rink */}
          {data.locations.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-2 text-sm font-semibold">
                Shot Locations ({data.locations.length} shots)
              </h3>
              <p className="text-xs text-muted-foreground">
                Yellow = Crossbar · Cyan = Left Post · Lime = Right Post
              </p>
            </div>
          )}
        </div>
      )}

      {!search && (
        <p className="text-muted-foreground">
          Enter a player name above to view their post shot profile.
        </p>
      )}
    </div>
  );
}
