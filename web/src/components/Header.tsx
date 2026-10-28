"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  BookOpen,
  Brain,
  Cpu,
  Database,
  Layers,
  Search,
  Terminal,
  UserCheck,
  Video,
} from "lucide-react";
import type { StatsData } from "@/lib/types";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: Activity },
  { href: "/search", label: "Search", icon: Search },
  { href: "/cards", label: "Cards", icon: Brain },
  { href: "/persons", label: "Traders", icon: UserCheck },
  { href: "/content", label: "Content", icon: Video },
  { href: "/sources", label: "Sources", icon: Layers },
  { href: "/skills", label: "Skills", icon: Cpu },
  { href: "/vocab", label: "Vocabulary", icon: BookOpen },
  { href: "/operations", label: "Operations", icon: Database },
  { href: "/cli", label: "Terminal", icon: Terminal },
];

export function Header() {
  const pathname = usePathname();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [isHealthy, setIsHealthy] = useState<boolean>(true);

  useEffect(() => {
    fetch("/api/stats")
      .then((res) => res.json())
      .then((res) => {
        if (res.ok && res.stats) {
          setStats(res.stats);
          setIsHealthy(res.doctor ? res.doctor.ok : true);
        }
      })
      .catch(() => setIsHealthy(false));
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-2.5 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 group-hover:border-emerald-500/60 transition-colors">
              <span className="font-mono font-bold text-sm">α</span>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold tracking-tight text-zinc-100 text-sm">
                  FinSocNet
                </span>
                <span className="rounded bg-emerald-950 px-1 py-0.2 text-[10px] font-mono font-medium text-emerald-400 border border-emerald-800/50">
                  v2
                </span>
              </div>
              <p className="text-[10px] text-zinc-500 font-mono -mt-0.5">
                Financial Social Intelligence
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="hidden lg:flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-zinc-800 text-emerald-400 shadow-xs"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-emerald-400" : "text-zinc-500"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Status Indicator & Quick Stats */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/80 px-2.5 py-1 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] animate-pulse"
                  : "bg-rose-500"
              }`}
            />
            <span className="text-[11px] font-mono text-zinc-300">
              SQLite FTS5
            </span>
            {stats && (
              <>
                <span className="text-zinc-600">|</span>
                <span className="font-mono text-[11px] text-emerald-400">
                  {stats.tables.knowledge_cards || 0} cards
                </span>
              </>
            )}
          </div>

          <Link
            href="/search"
            className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs font-mono text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 transition-colors"
          >
            <Search className="h-3 w-3" />
            <span className="text-[10px] hidden sm:inline">search</span>
          </Link>
        </div>
      </div>

      {/* Mobile navigation bar */}
      <div className="flex lg:hidden overflow-x-auto border-t border-zinc-900 px-4 py-1.5 gap-1 scrollbar-none">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${
                isActive
                  ? "bg-zinc-800 text-emerald-400"
                  : "text-zinc-400 hover:bg-zinc-900"
              }`}
            >
              <Icon className="h-3 w-3" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </header>
  );
}
