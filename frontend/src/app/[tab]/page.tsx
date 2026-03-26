"use client";

import Link from "next/link";
import { Sidebar } from "@/components/Sidebar";
import { DashboardTab } from "@/components/tabs/DashboardTab";
import { PlayersTab } from "@/components/tabs/PlayersTab";
import { TeamsTab } from "@/components/tabs/TeamsTab";
import { ShotAnalysisTab } from "@/components/tabs/ShotAnalysisTab";
import { TrendTab } from "@/components/tabs/TrendTab";
import { ShotMapTab } from "@/components/tabs/ShotMapTab";
import { PlayerSpotlightTab } from "@/components/tabs/PlayerSpotlightTab";
import { DataTab } from "@/components/tabs/DataTab";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "players", label: "Players" },
  { id: "teams", label: "Teams" },
  { id: "shot-analysis", label: "Shot Analysis" },
  { id: "trend", label: "Trend" },
  { id: "shot-map", label: "Shot Map" },
  { id: "spotlight", label: "Player Spotlight" },
  { id: "data", label: "Data" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function TabContent({ tab }: { tab: string }) {
  switch (tab as TabId) {
    case "dashboard":
      return <DashboardTab />;
    case "players":
      return <PlayersTab />;
    case "teams":
      return <TeamsTab />;
    case "shot-analysis":
      return <ShotAnalysisTab />;
    case "trend":
      return <TrendTab />;
    case "shot-map":
      return <ShotMapTab />;
    case "spotlight":
      return <PlayerSpotlightTab />;
    case "data":
      return <DataTab />;
    default:
      return <DashboardTab />;
  }
}

export default function TabPage({
  params,
}: {
  params: { tab: string };
}) {
  const { tab } = params;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 overflow-y-auto border-r border-border bg-card">
        <Sidebar />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Tab bar */}
        <nav className="flex flex-shrink-0 gap-1 overflow-x-auto border-b border-border bg-card px-4 py-2">
          {TABS.map((t) => (
            <Link
              key={t.id}
              href={`/${t.id}`}
              className={`whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              {t.label}
            </Link>
          ))}
        </nav>

        {/* Tab content */}
        <main className="flex-1 overflow-y-auto p-4">
          <TabContent tab={tab} />
        </main>
      </div>
    </div>
  );
}
