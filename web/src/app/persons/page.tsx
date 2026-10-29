"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Brain, Layers, Search, UserCheck, X } from "lucide-react";
import { FilterChips } from "@/components/FilterChips";
import type { TaxItem } from "@/lib/taxonomy";
import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { PersonGridSkeleton } from "@/components/Loading";
import { PersonModal } from "@/components/PersonModal";
import type { Person } from "@/lib/types";

type Sort = "cards" | "name" | "sources";

function counts(p: Person) {
  const x = p as unknown as { cards?: number; sources?: number; appearances?: number };
  return { cards: x.cards ?? p.stats?.cards_count ?? 0, sources: x.sources ?? 0, appearances: x.appearances ?? 0 };
}

function PeopleContent() {
  const params = useSearchParams();
  const [persons, setPersons] = useState<Person[]>([]);
  const [classes, setClasses] = useState<TaxItem[] | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [profession, setProfession] = useState("");
  const [sort, setSort] = useState<Sort>("cards");
  const [onlyWithCards, setOnlyWithCards] = useState(false);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(params.get("open"));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/persons")
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) {
          setPersons(r.persons || []);
          setClasses(r.classes || []);
        } else setError(r.error || "Failed to load people");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = persons.filter((p) => {
      if (profession && (p.profession || "other") !== profession) return false;
      if (onlyWithCards && counts(p).cards === 0) return false;
      if (!q) return true;
      return [p.canonical_name, p.moniker, p.affiliation, p.domains, p.relevance, p.profession].some((v) => v && String(v).toLowerCase().includes(q));
    });
    return list.sort((a, b) =>
      sort === "name" ? a.canonical_name.localeCompare(b.canonical_name) : counts(b)[sort] - counts(a)[sort] || a.canonical_name.localeCompare(b.canonical_name)
    );
  }, [persons, search, profession, sort, onlyWithCards]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-col justify-between gap-4 border-b border-zinc-800 pb-5 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">People</h1>
          </div>
          <p className="mt-1 text-xs font-mono text-zinc-400">
            Traders, portfolio managers, executives, economists, professors and authors — what they published and where to find them
          </p>
        </div>
        <Badge variant="emerald">
          {filtered.length === persons.length ? `${persons.length} people` : `${filtered.length} of ${persons.length} people`}
        </Badge>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Name, affiliation, field…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-zinc-800 bg-zinc-900/60 py-2 pl-9 pr-8 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2.5 top-2.5 text-zinc-500 hover:text-zinc-300" aria-label="Clear">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono text-zinc-400">
          <span>Sort</span>
          {(["cards", "sources", "name"] as Sort[]).map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={`rounded-md border px-2 py-1 transition-colors ${sort === s ? "border-emerald-500 text-emerald-300" : "border-zinc-800 hover:text-zinc-200"}`}
            >
              {s}
            </button>
          ))}
          <label className="ml-2 flex cursor-pointer items-center gap-1.5">
            <input type="checkbox" checked={onlyWithCards} onChange={(e) => setOnlyWithCards(e.target.checked)} className="accent-emerald-500" />
            with cards
          </label>
        </div>
      </div>

      <FilterChips label="Class" items={classes} value={profession || "all"} onChange={(v) => setProfession(v === "all" ? "" : v)} grouped total={persons.length} />

      {error && <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-sm text-rose-400">{error}</div>}

      {loading ? (
        <PersonGridSkeleton />
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">No people match.</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((person) => {
            const c = counts(person);
            return (
              <button
                key={person.id}
                onClick={() => setSelectedPersonId(person.id)}
                className="group flex flex-col gap-3 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-4 text-left transition-all hover:border-zinc-700 hover:bg-zinc-900/70"
              >
                <div className="flex items-center gap-3">
                  <Avatar name={person.canonical_name} path={person.avatar_path} size={56} className="rounded-2xl transition-colors group-hover:border-emerald-500/60" />
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-bold text-zinc-100 transition-colors group-hover:text-emerald-400">{person.canonical_name}</h3>
                    {person.profession && <p className="truncate text-[11px] font-mono uppercase tracking-wide text-emerald-400/80">{person.profession.replace(/_/g, " ")}</p>}
                    {person.affiliation && <p className="truncate text-[11px] font-mono text-zinc-500">{person.affiliation}</p>}
                  </div>
                </div>
                <p className="line-clamp-2 min-h-[2.5em] text-xs leading-relaxed text-zinc-400">
                  {person.domains || person.relevance || person.trading_style || ""}
                </p>
                <div className="mt-auto flex items-center gap-3 border-t border-zinc-800/70 pt-3 text-[11px] font-mono text-zinc-500">
                  <span className={`flex items-center gap-1 ${c.cards ? "text-emerald-400" : ""}`}>
                    <Brain className="h-3.5 w-3.5" />
                    {c.cards} cards
                  </span>
                  <span className="flex items-center gap-1">
                    <Layers className="h-3.5 w-3.5" />
                    {c.sources} sources
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <PersonModal personId={selectedPersonId} onClose={() => setSelectedPersonId(null)} />
    </div>
  );
}

export default function PersonsPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><PersonGridSkeleton /></div>}>
      <PeopleContent />
    </Suspense>
  );
}
