"use client";

import { useEffect, useState } from "react";
import {
  BookOpen,
  Filter,
  Layers,
  Search,
  Tag,
  X,
} from "lucide-react";
import { Badge } from "@/components/Badge";
import type { VocabTerm } from "@/lib/types";

const FACETS = [
  "all",
  "asset_class",
  "indicator",
  "pattern",
  "order_flow",
  "market_structure",
  "metric",
  "timeframe",
  "risk",
];

export default function VocabPage() {
  const [terms, setTerms] = useState<VocabTerm[]>([]);
  const [facet, setFacet] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchTerms = (f = facet, q = search) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (f !== "all") params.set("facet", f);
    if (q.trim()) params.set("query", q.trim());

    fetch(`/api/vocab?${params.toString()}`)
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setTerms(r.terms || []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTerms(facet, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facet]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTerms(facet, search);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Controlled Financial Vocabulary
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Standardized trading ontology terms, facets, and multilingual aliases ensuring consistent retrieval
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{terms.length} terms loaded</Badge>
        </div>
      </div>

      {/* Search & Facet Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Lookup vocabulary phrase or alias (e.g. EMA, absorption)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-8 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
            />
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  fetchTerms(facet, "");
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
            Lookup
          </button>
        </form>

        {/* Facet Selectors */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs font-mono text-zinc-500 mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" />
            <span>Facet:</span>
          </span>
          {FACETS.map((f) => (
            <button
              key={f}
              onClick={() => setFacet(f)}
              className={`rounded-md px-2.5 py-1 text-xs font-mono transition-colors cursor-pointer ${
                facet === f
                  ? "bg-zinc-100 text-zinc-950 font-bold"
                  : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 border border-zinc-700/50"
              }`}
            >
              {f.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Terms Grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : terms.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
          No vocabulary terms match your search.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {terms.map((term) => (
            <div
              key={term.term}
              className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-mono text-sm font-bold text-emerald-400">
                    #{term.term}
                  </h3>
                  <span className="text-xs text-zinc-400 font-mono">
                    {term.label}
                  </span>
                </div>
                <Badge variant="blue">{term.facet}</Badge>
              </div>

              {term.definition && (
                <p className="text-xs text-zinc-300 font-mono line-clamp-2 leading-relaxed">
                  {term.definition}
                </p>
              )}

              {term.broader && (
                <div className="text-[11px] font-mono text-zinc-400">
                  <span className="text-zinc-500">broader:</span> #{term.broader}
                </div>
              )}

              {/* Aliases */}
              {term.aliases && term.aliases.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-zinc-800/60">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                    Recognized Aliases ({term.aliases.length})
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {term.aliases.map((alias, idx) => (
                      <span
                        key={idx}
                        className="rounded bg-zinc-800/60 px-1.5 py-0.5 text-[10px] font-mono text-zinc-300"
                      >
                        {alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
