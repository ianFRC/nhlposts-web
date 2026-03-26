"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export function TrendTab() {
  const params = useFilterStore((s) => s.getParams());
  const [granularity, setGranularity] = useState<"month" | "week">("month");

  const { data, isLoading } = useQuery({
    queryKey: ["trend", params, granularity],
    queryFn: () => api.trend({ ...params, granularity }),
  });

  const xKey = granularity === "month" ? "month" : "week";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Granularity:</span>
        {(["month", "week"] as const).map((g) => (
          <button
            key={g}
            onClick={() => setGranularity(g)}
            className={`rounded px-3 py-1 text-xs ${
              granularity === g
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {g.charAt(0).toUpperCase() + g.slice(1)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading...</div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Post Shots Over Time</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart
              data={data?.rows ?? []}
              margin={{ left: 5, right: 20, top: 5, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey={xKey}
                angle={-45}
                textAnchor="end"
                tick={{ fontSize: 10 }}
                interval={granularity === "month" ? 0 : "preserveStartEnd"}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="post_shots" name="Total" stroke="#60a5fa" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="crossbar" name="Crossbar" stroke="#facc15" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="left_post" name="Left Post" stroke="#22d3ee" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="right_post" name="Right Post" stroke="#a3e635" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
