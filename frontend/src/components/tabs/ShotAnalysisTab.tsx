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

function BreakdownChart({
  title,
  data,
  xKey,
}: {
  title: string;
  data: object[];
  xKey: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ left: 5, right: 10, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="crossbar" name="Crossbar" stackId="a" fill="#facc15" />
          <Bar dataKey="left_post" name="Left Post" stackId="a" fill="#22d3ee" />
          <Bar dataKey="right_post" name="Right Post" stackId="a" fill="#a3e635" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ShotAnalysisTab() {
  const params = useFilterStore((s) => s.getParams());

  const byType = useQuery({ queryKey: ["shots-type", params], queryFn: () => api.shotsByType(params) });
  const bySit = useQuery({ queryKey: ["shots-sit", params], queryFn: () => api.shotsBySituation(params) });
  const byPeriod = useQuery({ queryKey: ["shots-period", params], queryFn: () => api.shotsByPeriod(params) });
  const byHA = useQuery({ queryKey: ["shots-ha", params], queryFn: () => api.shotsByHomeAway(params) });

  const periodData = (byPeriod.data?.rows ?? []).map((r) => ({
    ...r,
    label: r.period_type === "REG" ? `P${r.period}` : r.period_type,
  }));

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {!byType.isLoading && (
        <BreakdownChart
          title="By Shot Type"
          data={byType.data?.rows ?? []}
          xKey="shot_type"
        />
      )}
      {!bySit.isLoading && (
        <BreakdownChart
          title="By Game Situation"
          data={bySit.data?.rows ?? []}
          xKey="strength_state"
        />
      )}
      {!byPeriod.isLoading && (
        <BreakdownChart
          title="By Period"
          data={periodData}
          xKey="label"
        />
      )}
      {!byHA.isLoading && byHA.data?.rows && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="mb-3 text-sm font-semibold">Home vs Away (top players)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={byHA.data.rows.slice(0, 15)}
              layout="vertical"
              margin={{ left: 100, right: 10, top: 5, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="player_name" width={95} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="home" name="Home" stackId="a" fill="#60a5fa" />
              <Bar dataKey="away" name="Away" stackId="a" fill="#f97316" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
