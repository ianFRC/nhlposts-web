"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function DataTab() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["sync-status"],
    queryFn: api.syncStatus,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Data Sync Status</h2>
        <button
          onClick={() => refetch()}
          className="rounded bg-muted px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading...</div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Last Sync</p>
            <p className="mt-1 font-semibold">
              {data?.last_sync
                ? new Date(data.last_sync).toLocaleString()
                : "Never synced"}
            </p>
          </div>

          {data?.seasons && data.seasons.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border bg-card">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Season</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Games Ingested</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Total Games</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Post Shots</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground">Progress</th>
                  </tr>
                </thead>
                <tbody>
                  {data.seasons.map((row) => {
                    const pct = row.total_games
                      ? Math.round((row.ingested_games / row.total_games) * 100)
                      : 0;
                    return (
                      <tr key={row.season} className="border-b border-border">
                        <td className="px-4 py-2 font-semibold">{row.season}</td>
                        <td className="px-4 py-2">{row.ingested_games}</td>
                        <td className="px-4 py-2">{row.total_games}</td>
                        <td className="px-4 py-2">{row.post_shots}</td>
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
                              <div
                                className="h-full bg-primary"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
