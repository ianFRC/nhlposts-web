"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import type { PlayerRow } from "@/lib/types";

const COLUMNS: { key: keyof PlayerRow; label: string }[] = [
  { key: "player_name", label: "Player" },
  { key: "team", label: "Team" },
  { key: "position", label: "Pos" },
  { key: "post_shots", label: "Post Shots" },
  { key: "games_played", label: "GP" },
  { key: "post_per_game", label: "P/GP" },
  { key: "crossbar", label: "CB" },
  { key: "left_post", label: "LP" },
  { key: "right_post", label: "RP" },
  { key: "ev", label: "EV" },
  { key: "pp", label: "PP" },
  { key: "total_shots", label: "SOG" },
  { key: "post_pct_of_shots", label: "Post%" },
];

export function PlayersTab() {
  const params = useFilterStore((s) => s.getParams());
  const [sortBy, setSortBy] = useState("post_shots");
  const [asc, setAsc] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["players", params, sortBy, asc],
    queryFn: () => api.players({ ...params, sort_by: sortBy }),
  });

  const handleSort = (key: string) => {
    if (key === sortBy) {
      setAsc(!asc);
    } else {
      setSortBy(key);
      setAsc(false);
    }
  };

  const sorted = data?.players
    ? [...data.players].sort((a, b) => {
        const av = a[sortBy as keyof PlayerRow] ?? 0;
        const bv = b[sortBy as keyof PlayerRow] ?? 0;
        return asc
          ? String(av).localeCompare(String(bv), undefined, { numeric: true })
          : String(bv).localeCompare(String(av), undefined, { numeric: true });
      })
    : [];

  if (isLoading)
    return <div className="text-muted-foreground">Loading...</div>;

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold">Player Leaderboard</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer whitespace-nowrap px-3 py-2 text-left text-xs font-semibold text-muted-foreground hover:text-foreground"
                >
                  {col.label}
                  {sortBy === col.key && (asc ? " ↑" : " ↓")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={row.player_id}
                className={`border-b border-border ${
                  i % 2 === 0 ? "" : "bg-muted/30"
                } hover:bg-muted/60`}
              >
                <td className="px-3 py-1.5 font-medium">{row.player_name}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{row.team}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{row.position}</td>
                <td className="px-3 py-1.5">{row.post_shots}</td>
                <td className="px-3 py-1.5">{row.games_played ?? "—"}</td>
                <td className="px-3 py-1.5">{row.post_per_game?.toFixed(3) ?? "—"}</td>
                <td className="px-3 py-1.5 text-yellow-400">{row.crossbar}</td>
                <td className="px-3 py-1.5 text-cyan-400">{row.left_post}</td>
                <td className="px-3 py-1.5 text-lime-400">{row.right_post}</td>
                <td className="px-3 py-1.5">{row.ev}</td>
                <td className="px-3 py-1.5">{row.pp}</td>
                <td className="px-3 py-1.5">{row.total_shots ?? "—"}</td>
                <td className="px-3 py-1.5">
                  {row.post_pct_of_shots != null
                    ? `${row.post_pct_of_shots.toFixed(2)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="py-8 text-center text-muted-foreground">No data</p>
        )}
      </div>
    </div>
  );
}
