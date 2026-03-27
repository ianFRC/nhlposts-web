"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { SlidersHorizontal } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { DashboardTab } from "@/components/tabs/DashboardTab";
import { PlayersTab } from "@/components/tabs/PlayersTab";
import { ShotAnalysisTab } from "@/components/tabs/ShotAnalysisTab";
import { ShotMapTab } from "@/components/tabs/ShotMapTab";
import { PlayerSpotlightTab } from "@/components/tabs/PlayerSpotlightTab";
import { DataTab } from "@/components/tabs/DataTab";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "players", label: "Players" },
  { id: "shot-analysis", label: "Shot Analysis" },
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
    case "shot-analysis":
      return <ShotAnalysisTab />;
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const activeTabRef = useCallback((node: HTMLAnchorElement | null) => {
    if (node) node.scrollIntoView({ block: "nearest", inline: "center" });
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — drawer on mobile, static on desktop */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 w-72 flex-shrink-0 overflow-y-auto border-r border-border bg-card
          transition-transform duration-200 ease-in-out
          md:static md:w-64 md:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Tab bar */}
        <div className="relative flex-shrink-0 border-b border-border">
          {/* Fade hint — mobile only */}
          <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-8 bg-gradient-to-l from-card to-transparent md:hidden" />
        <nav className="flex items-center gap-1 overflow-x-auto bg-card px-2 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {/* Mobile filter toggle */}
          <button
            className="mr-1 flex-shrink-0 rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open filters"
          >
            <SlidersHorizontal size={16} />
          </button>

          {TABS.map((t) => (
            <Link
              key={t.id}
              href={`/${t.id}`}
              ref={tab === t.id ? activeTabRef : null}
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
        </div>

        {/* Tab content */}
        <main className="flex-1 overflow-y-auto p-2 md:p-4">
          <TabContent tab={tab} />
        </main>
      </div>
    </div>
  );
}
