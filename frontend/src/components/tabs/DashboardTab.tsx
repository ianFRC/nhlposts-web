"use client";

import { useQuery } from "@tanstack/react-query";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";

const IRON_COLORS = ["#facc15", "#22d3ee", "#a3e635"];
const SITUATION_COLORS = ["#60a5fa", "#f97316", "#e879f9"];

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

export function DashboardTab() {
  const params = useFilterStore((s) => s.getParams());

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", params],
    queryFn: () => api.dashboard(params),
  });

  if (isLoading)
    return (
      <div className="flex h-48 items-center justify-center text-muted-foreground">
        Loading...
      </div>
    );
  if (error)
    return (
      <div className="text-red-400">
        Error: {(error as Error).message}
      </div>
    );
  if (!data) return null;

  const { totals, iron_split, situation_split, top_players } = data;

  return (
    <div className="space-y-6">
      {/* Summary stat cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total Post Shots" value={totals.total_post_shots} />
        <StatCard label="Unique Players" value={totals.unique_players} />
        <StatCard label="Games w/ Posts" value={totals.games_with_posts} />
        <StatCard
          label="Post % of Shots"
          value={
            totals.post_pct_of_shots != null
              ? `${totals.post_pct_of_shots.toFixed(2)}%`
              : "N/A"
          }
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Iron type split donut */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Hit Location Split</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={iron_split}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {iron_split.map((_, i) => (
                  <Cell key={i} fill={IRON_COLORS[i % IRON_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Situation split donut */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Situation Split</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={situation_split}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {situation_split.map((_, i) => (
                  <Cell key={i} fill={SITUATION_COLORS[i % SITUATION_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top players bar chart */}
      {top_players.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Top 10 Players by Post Shots</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={top_players}
              layout="vertical"
              margin={{ left: 110, right: 20, top: 5, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="player_name"
                width={105}
                tick={{ fontSize: 11 }}
              />
              <Tooltip />
              <Legend />
              <Bar dataKey="crossbar" name="Crossbar" stackId="a" fill="#facc15" />
              <Bar dataKey="left_post" name="Left Post" stackId="a" fill="#22d3ee" />
              <Bar dataKey="right_post" name="Right Post" stackId="a" fill="#a3e635" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
