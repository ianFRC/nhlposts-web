"use client";

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
  Legend,
  ResponsiveContainer,
} from "recharts";

export function TeamsTab() {
  const params = useFilterStore((s) => s.getParams());
  const { data, isLoading } = useQuery({
    queryKey: ["teams", params],
    queryFn: () => api.teams(params),
  });

  if (isLoading) return <div className="text-muted-foreground">Loading...</div>;

  const teams = data?.teams ?? [];

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-semibold">Teams — Post Shots (stacked by hit location)</h2>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={teams}
            margin={{ bottom: 60, left: 10, right: 10, top: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="team"
              angle={-45}
              textAnchor="end"
              tick={{ fontSize: 11 }}
              interval={0}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="crossbar" name="Crossbar" stackId="a" fill="#facc15" />
            <Bar dataKey="left_post" name="Left Post" stackId="a" fill="#22d3ee" />
            <Bar dataKey="right_post" name="Right Post" stackId="a" fill="#a3e635" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {["Team", "Games", "Post Shots", "P/GP", "Crossbar", "L Post", "R Post", "EV", "PP", "PK"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {teams.map((row, i) => (
              <tr key={row.team_id} className={`border-b border-border ${i % 2 === 0 ? "" : "bg-muted/30"}`}>
                <td className="px-3 py-1.5 font-semibold">{row.team}</td>
                <td className="px-3 py-1.5">{row.games}</td>
                <td className="px-3 py-1.5">{row.post_shots}</td>
                <td className="px-3 py-1.5">{row.post_per_game?.toFixed(3)}</td>
                <td className="px-3 py-1.5 text-yellow-400">{row.crossbar}</td>
                <td className="px-3 py-1.5 text-cyan-400">{row.left_post}</td>
                <td className="px-3 py-1.5 text-lime-400">{row.right_post}</td>
                <td className="px-3 py-1.5">{row.ev}</td>
                <td className="px-3 py-1.5">{row.pp}</td>
                <td className="px-3 py-1.5">{row.pk}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
