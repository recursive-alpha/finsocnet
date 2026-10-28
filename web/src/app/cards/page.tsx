"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  AlertTriangle,
  Brain,
  Filter,
  Layers,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Badge, CategoryBadge } from "@/components/Badge";
import { CardModal } from "@/components/CardModal";
import type { KnowledgeCard } from "@/lib/types";

const CATEGORIES = [
  "all",
  "setup_and_screening",
  "entry_and_execution",
  "trade_management",
  "risk_and_sizing",
  "psychology_and_review",
  "concept",
  "market_dynamics",
  "research_method",
];

function CardsContent() {
  const searchParams = useSearchParams();
  const initialSearch = searchParams.get("search") || "";
  const initialCategory = searchParams.get("category") || "all";

  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [search, setSearch] = useState(initialSearch);
  const [category, setCategory] = useState(initialCategory);
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);

  const fetchCards = (s = search, cat = category, st = status) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (s.trim()) params.set("search", s.trim());
    if (cat !== "all") params.set("category", cat);
    if (st !== "all") params.set("status", st);
    params.set("limit", "150");

    fetch(`/api/cards?${params.toString()}`)
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setCards(r.cards || []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCards(search, category, status);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, status]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCards(search, category, status);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Knowledge Cards Explorer
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Canonical trading claims, setup filters, and risk invariances stored in SQLite FTS5
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{cards.length} cards matched</Badge>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Search claims, subjects, or terms (FTS5 BM25)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-8 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
            />
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  fetchCards("", category, status);
                }}
                className="absolute right-2.5 top-2.5 text-zinc-500 hover:text-zinc-300"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <button
            type="submit"
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-mono font-medium text-white hover:bg-emerald-500 transition-colors cursor-pointer"
          >
            Search
          </button>
        </form>

        {/* Categories Bar */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs font-mono text-zinc-500 mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" />
            <span>Category:</span>
          </span>
          {CATEGORIES.map((cat) => {
            const isSelected = category === cat;
            return (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`rounded-md px-2.5 py-1 text-xs font-mono transition-colors cursor-pointer ${
                  isSelected
                    ? "bg-zinc-100 text-zinc-950 font-bold"
                    : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 border border-zinc-700/50"
                }`}
              >
                {cat.replace(/_/g, " ")}
              </button>
            );
          })}
        </div>
      </div>

      {/* Cards Grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : cards.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center space-y-2">
          <Brain className="mx-auto h-8 w-8 text-zinc-600" />
          <h3 className="text-sm font-mono font-semibold text-zinc-300">
            No knowledge cards match your query
          </h3>
          <p className="text-xs font-mono text-zinc-500">
            Try clearing filters or searching for terms like &quot;EMA&quot;, &quot;breakout&quot;, or &quot;stop loss&quot;.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cards.map((card) => (
            <div
              key={card.id}
              onClick={() => setSelectedCardId(card.id)}
              className="group rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700">
                    CARD #{card.id}
                  </span>
                  <CategoryBadge category={card.category} />
                </div>

                <div>
                  <h3 className="text-sm font-bold text-zinc-100 capitalize line-clamp-1 group-hover:text-emerald-400 transition-colors">
                    {card.subject}
                  </h3>
                  <p className="mt-1.5 text-xs text-zinc-300 font-mono line-clamp-3 leading-relaxed">
                    {card.claim}
                  </p>
                </div>

                {card.conditions && card.conditions.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                      Conditions ({card.conditions.length})
                    </span>
                    <p className="text-[11px] text-zinc-400 font-mono line-clamp-1">
                      • {card.conditions[0]}
                    </p>
                  </div>
                )}

                {card.invalidation && (
                  <div className="rounded-lg bg-amber-950/20 border border-amber-900/40 p-2">
                    <p className="text-[11px] text-amber-300/80 font-mono line-clamp-1">
                      Invalidation: {card.invalidation}
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-2 pt-2 border-t border-zinc-800/60">
                <div className="flex flex-wrap gap-1">
                  {card.terms?.slice(0, 3).map((t) => (
                    <span
                      key={t}
                      className="rounded bg-zinc-800/80 px-1.5 py-0.2 text-[10px] font-mono text-zinc-400"
                    >
                      #{t}
                    </span>
                  ))}
                  {(card.terms?.length || 0) > 3 && (
                    <span className="text-[10px] font-mono text-zinc-500">
                      +{(card.terms?.length || 0) - 3} more
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500">
                  <span>Action: {card.action || "NONE"}</span>
                  <span className="text-emerald-400 group-hover:translate-x-0.5 transition-transform">
                    inspect details →
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Card Inspector Modal */}
      <CardModal
        cardId={selectedCardId}
        onClose={() => setSelectedCardId(null)}
        onSelectCard={(id) => setSelectedCardId(id)}
      />
    </div>
  );
}

export default function CardsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      }
    >
      <CardsContent />
    </Suspense>
  );
}
