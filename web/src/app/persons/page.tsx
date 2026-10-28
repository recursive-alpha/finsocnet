"use client";

import { useEffect, useState } from "react";
import {
  Award,
  BookOpen,
  Brain,
  Search,
  TrendingUp,
  UserCheck,
  Video,
} from "lucide-react";
import { Badge } from "@/components/Badge";
import { Avatar } from "@/components/Avatar";
import { CardModal } from "@/components/CardModal";
import { PersonModal } from "@/components/PersonModal";
import type { Person } from "@/lib/types";

export default function PersonsPage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [search, setSearch] = useState("");
  const [profession, setProfession] = useState("");
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/persons")
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setPersons(r.persons || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const professions = Array.from(new Set(persons.map((p) => p.profession).filter(Boolean))) as string[];
  const filtered = persons.filter((p) => {
    if (profession && p.profession !== profession) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (p.affiliation && p.affiliation.toLowerCase().includes(q)) ||
      (p.domains && p.domains.toLowerCase().includes(q)) ||
      p.canonical_name.toLowerCase().includes(q) ||
      (p.moniker && p.moniker.toLowerCase().includes(q)) ||
      (p.trading_style && p.trading_style.toLowerCase().includes(q)) ||
      (p.primary_markets && p.primary_markets.toLowerCase().includes(q))
    );
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              People in Markets &amp; Economics
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Traders, portfolio managers, executives, economists and professors, with what they published and their rulebooks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{persons.length} people</Badge>
        </div>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Filter by name, affiliation, field, style or market..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl border border-zinc-800 bg-zinc-900/60 pl-9 pr-4 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
        />
      </div>

      {professions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {["", ...professions].map((pr) => (
            <button
              key={pr || "all"}
              onClick={() => setProfession(pr)}
              className={`rounded-full border px-3 py-1 text-[11px] font-mono transition-colors ${
                profession === pr ? "border-emerald-500 text-emerald-300" : "border-zinc-800 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {pr ? pr.replace(/_/g, " ") : "all"}
            </button>
          ))}
        </div>
      )}

      {/* People grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
          No people match your search.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((person) => (
            <div
              key={person.id}
              onClick={() => setSelectedPersonId(person.id)}
              className="group rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-6 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <Avatar name={person.canonical_name} path={person.avatar_path} size={48} className="rounded-2xl group-hover:border-emerald-500/60 transition-colors" />
                    <div>
                      <h3 className="text-base font-bold text-zinc-100 group-hover:text-emerald-400 transition-colors">
                        {person.canonical_name}
                      </h3>
                      {person.moniker && (
                        <p className="text-xs text-zinc-400 font-mono">
                          ({person.moniker})
                        </p>
                      )}
                    </div>
                  </div>
                  <Badge variant="emerald">{person.status || "active"}</Badge>
                </div>

                {/* Trading Style */}
                <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/40 p-3 space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                    {person.profession ? person.profession.replace(/_/g, " ") : "Focus"}
                    {person.affiliation ? ` · ${person.affiliation}` : ""}
                  </span>
                  <p className="text-xs text-zinc-300 font-mono line-clamp-2 leading-relaxed">
                    {person.trading_style || person.domains || person.relevance || "Market knowledge"}
                  </p>
                </div>

                {/* Primary Markets */}
                {person.primary_markets && (
                  <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                    <TrendingUp className="h-3.5 w-3.5 text-zinc-500" />
                    <span>Markets: {person.primary_markets}</span>
                  </div>
                )}

                {/* Verified Records */}
                {person.verified_records && (
                  <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400/90">
                    <Award className="h-3.5 w-3.5" />
                    <span className="line-clamp-1">{person.verified_records}</span>
                  </div>
                )}
              </div>

              {/* Action Footer */}
              <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs font-mono">
                <span className="text-zinc-500">
                  {person.stats?.cards_count ?? (person as unknown as { cards_count?: number }).cards_count ?? 0} cards attributed
                </span>
                <span className="text-emerald-400 font-medium group-hover:translate-x-1 transition-transform flex items-center gap-1">
                  <span>View Rulebook</span>
                  <BookOpen className="h-3.5 w-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Person Rulebook Modal */}
      <PersonModal
        personId={selectedPersonId}
        onClose={() => setSelectedPersonId(null)}
        onSelectCard={(id) => {
          setSelectedPersonId(null);
          setSelectedCardId(id);
        }}
      />

      {/* Card Modal */}
      <CardModal
        cardId={selectedCardId}
        onClose={() => setSelectedCardId(null)}
      />
    </div>
  );
}
