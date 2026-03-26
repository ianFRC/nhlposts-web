"use client";

import { useQuery } from "@tanstack/react-query";
import { useFilterStore } from "@/lib/filterStore";
import { api } from "@/lib/api";
import type { ShotLocation } from "@/lib/types";

// Rink dimensions (NHL: 200ft × 85ft). We'll display one zone (offensive).
// Coordinates in NHL data: x ∈ [-100, 100], y ∈ [-42.5, 42.5]
// We map to SVG space.

const SVG_W = 400;
const SVG_H = 340;

// Map NHL coordinates to SVG
// Show the full rink top-down, normalized to SVG space
function toSvgX(x: number): number {
  // x: -100..100 → 0..SVG_W
  return ((x + 100) / 200) * SVG_W;
}
function toSvgY(y: number): number {
  // y: -42.5..42.5 → 0..SVG_H
  return ((y + 42.5) / 85) * SVG_H;
}

const REASON_COLOR: Record<string, string> = {
  "hit-crossbar": "#facc15",
  "hit-left-post": "#22d3ee",
  "hit-right-post": "#a3e635",
};

function RinkSVG({ locations }: { locations: ShotLocation[] }) {
  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      className="w-full max-w-2xl rounded-lg border border-border bg-slate-900"
    >
      {/* Ice surface */}
      <rect x="0" y="0" width={SVG_W} height={SVG_H} fill="#0c1a2e" />

      {/* Centre line */}
      <line
        x1={SVG_W / 2}
        y1={0}
        x2={SVG_W / 2}
        y2={SVG_H}
        stroke="#cc2222"
        strokeWidth={3}
      />

      {/* Blue lines */}
      <line
        x1={SVG_W * 0.25}
        y1={0}
        x2={SVG_W * 0.25}
        y2={SVG_H}
        stroke="#4488ee"
        strokeWidth={2}
      />
      <line
        x1={SVG_W * 0.75}
        y1={0}
        x2={SVG_W * 0.75}
        y2={SVG_H}
        stroke="#4488ee"
        strokeWidth={2}
      />

      {/* Centre ice circle */}
      <circle
        cx={SVG_W / 2}
        cy={SVG_H / 2}
        r={SVG_H * 0.22}
        fill="none"
        stroke="#4488ee"
        strokeWidth={1.5}
      />

      {/* Goal creases (left and right) */}
      <path
        d={`M ${SVG_W * 0.03} ${SVG_H * 0.41}
            A ${SVG_H * 0.09} ${SVG_H * 0.09} 0 0 1 ${SVG_W * 0.03} ${SVG_H * 0.59}`}
        fill="#1a3a5c"
        stroke="#cc2222"
        strokeWidth={1.5}
      />
      <path
        d={`M ${SVG_W * 0.97} ${SVG_H * 0.41}
            A ${SVG_H * 0.09} ${SVG_H * 0.09} 0 0 0 ${SVG_W * 0.97} ${SVG_H * 0.59}`}
        fill="#1a3a5c"
        stroke="#cc2222"
        strokeWidth={1.5}
      />

      {/* Shot dots */}
      {locations.map((loc, i) => (
        <circle
          key={i}
          cx={toSvgX(loc.x_coord)}
          cy={toSvgY(loc.y_coord)}
          r={5}
          fill={REASON_COLOR[loc.reason] ?? "#ffffff"}
          fillOpacity={0.75}
          stroke="#000"
          strokeWidth={0.5}
        >
          <title>{`${loc.player_name} — ${loc.reason} (${loc.shot_type}, ${loc.strength_state})`}</title>
        </circle>
      ))}
    </svg>
  );
}

export function ShotMapTab() {
  const params = useFilterStore((s) => s.getParams());
  const { data, isLoading } = useQuery({
    queryKey: ["shotmap", params],
    queryFn: () => api.shotmap(params),
  });

  if (isLoading) return <div className="text-muted-foreground">Loading...</div>;

  const locations = data?.locations ?? [];
  const zones = data?.zone_counts ?? {};

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-block h-3 w-3 rounded-full bg-yellow-400" />
          Crossbar
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-block h-3 w-3 rounded-full bg-cyan-400" />
          Left Post
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-block h-3 w-3 rounded-full bg-lime-400" />
          Right Post
        </div>
        <span className="ml-4 text-xs text-muted-foreground">
          {locations.length} shots plotted
        </span>
      </div>

      <RinkSVG locations={locations} />

      {Object.keys(zones).length > 0 && (
        <div className="flex gap-4">
          {Object.entries(zones).map(([zone, count]) => (
            <div key={zone} className="rounded border border-border bg-card px-3 py-2 text-xs">
              <span className="text-muted-foreground">{zone}: </span>
              <span className="font-semibold">{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
