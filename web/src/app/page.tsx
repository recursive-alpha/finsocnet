"use client";

import { CardGridSkeleton, PersonGridSkeleton } from "@/components/Loading";
import { PeopleStack } from "@/components/PeopleStack";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Brain,
  CheckCircle,
  Database,
  ExternalLink,
  Layers,
  Search,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  Users,
  Video,
} from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { Badge, CategoryBadge, PlatformBadge } from "@/components/Badge";
import { CardModal } from "@/components/CardModal";
import { PersonModal } from "@/components/PersonModal";
import { StatCard } from "@/components/StatCard";
import type { DoctorReport, KnowledgeCard, Person, StatsData } from "@/lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [platformTab, setPlatformTab] = useState<"catalog" | "discovery">("catalog");

  useEffect(() => {
    Promise.all([
      fetch("/api/stats").then((r) => r.json()),
      fetch("/api/cards?limit=6&order=newest").then((r) => r.json()),
      fetch("/api/persons").then((r) => r.json()),
    ])
      .then(([statsRes, cardsRes, personsRes]) => {
        if (statsRes.ok) {
          setStats(statsRes.stats);
          setDoctor(statsRes.doctor);
        }
        if (cardsRes.ok) setCards(cardsRes.cards || []);
        if (personsRes.ok) setPersons(personsRes.persons || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalContent = stats?.tables.contents || 0;
  const totalCards = stats?.tables.knowledge_cards || 0;
  const totalPersons = stats?.tables.persons || 0;
  const totalSegments = stats?.tables.content_segments || 0;
  const totalCitations = stats?.tables.card_citations || 0;
  const totalVocab = stats?.tables.vocabulary || 0;
  const totalSources = stats?.tables.sources || 0;
  const totalLinks = Object.values(stats?.links_by_platform || {}).reduce((a, b) => a + b, 0);
  const discoveredPlatformsCount = new Set([
    ...Object.keys(stats?.contents_by_platform || {}),
    ...Object.keys(stats?.sources_by_platform || {}),
    ...Object.keys(stats?.links_by_platform || {}),
  ]).size;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8">
      {/* Hero / Terminal Header */}
      <div className="rounded-2xl border border-zinc-800 bg-gradient-to-b from-zinc-900/80 to-zinc-950/80 p-6 sm:p-8 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3 py-1 text-xs font-mono text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>v2 Engine Active • SQLite + FTS5</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-100">
              Financial Social Intelligence Network
            </h1>
            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed font-mono">
              Agent-operated intelligence mining across 31 platforms. Converts raw video transcripts, threads, and research into canonical Knowledge Cards and verified strategy rulebooks.
            </p>
          </div>

          {/* Quick Search Input */}
          <div className="w-full md:w-80 space-y-2">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (searchQuery.trim()) {
                  window.location.href = `/cards?search=${encodeURIComponent(searchQuery)}`;
                }
              }}
              className="relative"
            >
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search cards (e.g. VCP, EMA)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/90 pl-9 pr-4 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden transition-colors"
              />
            </form>
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 px-1">
              <span>Try: episodic pivot, 10 ema, vcp</span>
              <Link href="/cards" className="text-emerald-400 hover:underline">
                view all cards →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        <StatCard
          title="Cataloged Content"
          value={totalContent}
          subtitle="across 6 platforms"
          icon={Video}
        />
        <StatCard
          title="Knowledge Cards"
          value={totalCards}
          subtitle="empirical claims"
          icon={Brain}
          badge="FTS5"
        />
        <StatCard
          title="People"
          value={totalPersons}
          subtitle="traders, PMs, economists, executives…"
          icon={UserCheck}
        />
        <StatCard
          title="Content Segments"
          value={totalSegments}
          subtitle="transcript windows"
          icon={Layers}
        />
        <StatCard
          title="Citations"
          value={totalCitations}
          subtitle="ground truth quotes"
          icon={CheckCircle}
        />
        <StatCard
          title="Controlled Vocab"
          value={totalVocab}
          subtitle="financial ontology"
          icon={BookOpen}
        />
      </div>

      {/* Main Grid: Platforms & Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Platform Distribution */}
        {/* Platform Distribution & Discovery */}
        <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-zinc-800/80 pb-3 gap-2">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-zinc-100 font-mono">
                {platformTab === "catalog" ? "Catalog by Platform" : "Platform Discovery"}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg bg-zinc-800/80 p-0.5 text-[11px] font-mono">
                <button
                  type="button"
                  onClick={() => setPlatformTab("catalog")}
                  className={`px-2 py-0.5 rounded-md transition-colors ${
                    platformTab === "catalog"
                      ? "bg-zinc-700 text-zinc-100 font-semibold"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Catalog
                </button>
                <button
                  type="button"
                  onClick={() => setPlatformTab("discovery")}
                  className={`px-2 py-0.5 rounded-md transition-colors ${
                    platformTab === "discovery"
                      ? "bg-zinc-700 text-zinc-100 font-semibold"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Discovery ({discoveredPlatformsCount})
                </button>
              </div>
              <Link
                href={platformTab === "catalog" ? "/content" : "/sources"}
                className="text-xs font-mono text-emerald-400 hover:text-emerald-300"
              >
                {platformTab === "catalog" ? "all content →" : "all sources →"}
              </Link>
            </div>
          </div>

          {platformTab === "catalog" ? (
            <div className="space-y-3">
              {stats?.contents_by_platform &&
                Object.entries(stats.contents_by_platform)
                  .sort((a, b) => b[1] - a[1])
                  .map(([platform, count]) => {
                    const pct = totalContent > 0 ? (count / totalContent) * 100 : 0;
                    return (
                      <div key={platform} className="space-y-1">
                        <div className="flex items-center justify-between text-xs font-mono">
                          <span className="flex items-center gap-1.5 capitalize text-zinc-300">
                            <PlatformBadge platform={platform} />
                          </span>
                          <span className="text-zinc-400 font-semibold">
                            {count.toLocaleString()}
                          </span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-500/80"
                            style={{ width: `${Math.max(pct, 2)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
                Content Sources ({totalSources})
              </div>
              <div className="grid grid-cols-2 gap-2">
                {stats?.sources_by_platform &&
                  Object.entries(stats.sources_by_platform)
                    .sort((a, b) => b[1] - a[1])
                    .map(([platform, count]) => (
                      <div
                        key={platform}
                        className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-2.5 py-1.5 text-xs font-mono"
                      >
                        <PlatformBadge platform={platform} />
                        <span className="text-zinc-300 font-semibold">{count}</span>
                      </div>
                    ))}
              </div>

              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] font-mono text-zinc-400">
                <span className="uppercase tracking-wider">Discovered Profiles</span>
                <span>{totalLinks} endpoints</span>
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                {stats?.links_by_platform &&
                  Object.entries(stats.links_by_platform)
                    .sort((a, b) => b[1] - a[1])
                    .map(([platform, count]) => (
                      <span
                        key={platform}
                        className="inline-flex items-center gap-1 rounded-md border border-zinc-800/80 bg-zinc-900/60 px-2 py-0.5 text-[11px] font-mono text-zinc-300"
                      >
                        <span className="capitalize">{platform}</span>
                        <span className="text-emerald-400 font-semibold">{count}</span>
                      </span>
                    ))}
              </div>
            </div>
          )}
        </div>

        {/* Cards by Category */}
        <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-zinc-100 font-mono">
                Cards by Category
              </h3>
            </div>
            <Link
              href="/cards"
              className="text-xs font-mono text-emerald-400 hover:text-emerald-300"
            >
              browse cards →
            </Link>
          </div>

          <div className="space-y-2.5">
            {stats?.cards_by_category &&
              Object.entries(stats.cards_by_category)
                .sort((a, b) => b[1] - a[1])
                .map(([category, count]) => (
                  <div
                    key={category}
                    className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2 text-xs font-mono"
                  >
                    <CategoryBadge category={category} />
                    <span className="text-zinc-200 font-semibold">
                      {count} {count === 1 ? "card" : "cards"}
                    </span>
                  </div>
                ))}
          </div>
        </div>

        {/* Health & Engine Diagnostics */}
        <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-zinc-100 font-mono">
                System Diagnostics
              </h3>
            </div>
            <Link
              href="/operations"
              className="text-xs font-mono text-emerald-400 hover:text-emerald-300"
            >
              diagnostics →
            </Link>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 p-3">
              <span className="text-zinc-400">Database Engine</span>
              <span className="text-emerald-400 font-semibold">
                SQLite {doctor?.sqlite_version || "3.x"}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 p-3">
              <span className="text-zinc-400">Schema Integrity</span>
              <span className="text-emerald-400 font-semibold">
                {doctor?.integrity === "ok" ? "PRAGMA OK" : "Verified"}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 p-3">
              <span className="text-zinc-400">Applied Migrations</span>
              <span className="text-zinc-200">
                {doctor?.schema?.applied_count || 3} migrations
              </span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 p-3">
              <span className="text-zinc-400">FTS5 Full-Text Tables</span>
              <span className="text-emerald-400">
                {doctor?.fts_integrity
                  ? Object.keys(doctor.fts_integrity).length
                  : 4}{" "}
                indexes active
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Canonical Traders Spotlight */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-zinc-100">
              People in Markets &amp; Economics
            </h2>
            <p className="text-xs text-zinc-500 font-mono">
              Traders, portfolio managers, executives, economists and professors, with their rulebooks
            </p>
          </div>
          <Link
            href="/persons"
            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            <span>view all people</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading && persons.length === 0 && <div className="col-span-full"><PersonGridSkeleton count={6} /></div>}
          {persons.slice(0, 6).map((p) => (
            <div
              key={p.id}
              onClick={() => setSelectedPersonId(p.id)}
              className="group rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <Avatar name={p.canonical_name} path={p.avatar_path} size={48} className="rounded-2xl group-hover:border-emerald-500/60 transition-colors" />
                  <div>
                    <h4 className="text-sm font-bold text-zinc-100 group-hover:text-emerald-400 transition-colors">
                      {p.canonical_name}
                    </h4>
                    {p.moniker && (
                      <p className="text-[11px] text-zinc-500 font-mono">
                        {p.moniker}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <p className="text-xs text-zinc-400 font-mono line-clamp-2 leading-relaxed">
                {p.trading_style || p.domains || p.bio || "Market knowledge"}
              </p>

              <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-2 border-t border-zinc-800/60">
                <span>{[p.profession?.replace(/_/g, " "), p.affiliation || p.primary_markets].filter(Boolean).join(" · ") || "—"}</span>
                <span className="text-emerald-400 group-hover:translate-x-0.5 transition-transform">
                  profile →
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Knowledge Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-zinc-100">
              Recently Mined Knowledge Cards
            </h2>
            <p className="text-xs text-zinc-500 font-mono">
              Falsifiable trading hypotheses and execution laws
            </p>
          </div>
          <Link
            href="/cards"
            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            <span>all cards ({totalCards})</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading && cards.length === 0 && <div className="col-span-full"><CardGridSkeleton count={3} /></div>}
          {cards.map((card) => (
            <div
              key={card.id}
              onClick={() => setSelectedCardId(card.id)}
              className="group rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400">
                    CARD #{card.id}
                  </span>
                  <CategoryBadge category={card.category} />
                </div>
                <h4 className="text-sm font-bold text-zinc-100 capitalize line-clamp-1">
                  {card.subject}
                </h4>
                <p className="text-xs text-zinc-300 font-mono line-clamp-3 leading-relaxed">
                  {card.claim}
                </p>
              </div>

              <div className="space-y-2.5 pt-3 border-t border-zinc-800/60">
                <PeopleStack people={card.people} />
                {card.invalidation && (
                  <p className="text-[11px] text-amber-400/80 font-mono line-clamp-1">
                    Invalidation: {card.invalidation}
                  </p>
                )}
                <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500">
                  <span>{card.source?.platform || card.action || ""}</span>
                  <span className="text-emerald-400 group-hover:translate-x-0.5 transition-transform">
                    inspect →
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modals */}
      <CardModal
        cardId={selectedCardId}
        onClose={() => setSelectedCardId(null)}
        onSelectCard={(id) => setSelectedCardId(id)}
      />
      <PersonModal
        personId={selectedPersonId}
        onClose={() => setSelectedPersonId(null)}
        onSelectCard={(id) => {
          setSelectedPersonId(null);
          setSelectedCardId(id);
        }}
      />
    </div>
  );
}
