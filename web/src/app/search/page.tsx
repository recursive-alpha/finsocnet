"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Brain, BookOpen, Search, SlidersHorizontal, Sparkles, UserCheck, Video, X } from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { CardModal } from "@/components/CardModal";
import { ContentViewerModal } from "@/components/ContentViewerModal";
import { PersonModal } from "@/components/PersonModal";
import type { EmbedStatus, SearchHit, SearchMode, SearchResponse, SearchType } from "@/lib/types";

const ALL_TYPES: SearchType[] = ["cards", "contents", "persons", "skills"];
const TYPE_META: Record<SearchType, { label: string; icon: typeof Brain; tone: string }> = {
  cards: { label: "Knowledge cards", icon: Brain, tone: "text-cyan-400 border-cyan-800/60 bg-cyan-950/40" },
  contents: { label: "Content", icon: Video, tone: "text-emerald-400 border-emerald-800/60 bg-emerald-950/40" },
  persons: { label: "Traders", icon: UserCheck, tone: "text-fuchsia-400 border-fuchsia-800/60 bg-fuchsia-950/40" },
  skills: { label: "Rulebooks", icon: BookOpen, tone: "text-amber-400 border-amber-800/60 bg-amber-950/40" },
};
const MODES: Array<{ id: SearchMode; label: string; hint: string }> = [
  { id: "auto", label: "Auto", hint: "Hybrid when embeddings exist, keyword otherwise" },
  { id: "hybrid", label: "Hybrid", hint: "Keyword (BM25) and meaning (embeddings) fused with RRF" },
  { id: "semantic", label: "Semantic", hint: "Meaning only: finds paraphrases that share no words" },
  { id: "lexical", label: "Keyword", hint: "SQLite FTS5 only" },
];
const KINDS = ["rule", "setup", "observation", "mechanism", "definition", "metric", "practice"];
const CATEGORIES = ["setup_and_screening", "entry_and_execution", "trade_management", "risk_and_sizing", "psychology_and_review", "market_dynamics", "concept", "research_method"];
const EVIDENCE = ["anecdotal", "claimed", "backtested", "audited"];
const HORIZONS = ["intraday", "overnight", "swing_days", "swing_weeks", "position", "n/a"];
const PLATFORMS = ["youtube", "podcast", "x", "reddit", "medium", "substack", "web", "stackexchange", "forum", "github", "arxiv", "paper", "book", "file", "hackernews"];
const SKILL_CATEGORIES = ["overview", "setup_and_screening", "entry_and_execution", "trade_management", "risk_and_sizing", "psychology_and_review", "checklists"];
const EXAMPLES = ["how to size a position after a losing streak", "what to do when a breakout fails", "why options lose value over time", "pairs trading cointegration"];

interface Filters {
  kind: string[];
  category: string;
  evidence_min: string;
  horizon: string;
  min_persons: string;
  person: string;
  platform: string[];
  since: string;
  language: string;
  skill_category: string;
}

const EMPTY: Filters = { kind: [], category: "", evidence_min: "", horizon: "", min_persons: "", person: "", platform: [], since: "", language: "", skill_category: "" };

function toggle(list: string[], v: string): string[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function Snippet({ text }: { text: string | null }) {
  if (!text) return null;
  const parts = text.split(/(«[^»]*»)/g);
  return (
    <p className="text-xs leading-relaxed text-zinc-400 line-clamp-3">
      {parts.map((p, i) =>
        p.startsWith("«") ? (
          <mark key={i} className="rounded bg-emerald-500/20 px-0.5 text-emerald-300">
            {p.slice(1, -1)}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </p>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`cursor-pointer rounded-md border px-2 py-1 text-[11px] font-mono transition-colors ${
        active ? "border-zinc-100 bg-zinc-100 font-bold text-zinc-950" : "border-zinc-700/50 bg-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
      }`}
    >
      {children}
    </button>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-[10px] font-mono uppercase tracking-wider text-zinc-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs normal-case tracking-normal text-zinc-200 focus:border-emerald-500 focus:outline-hidden"
      >
        <option value="">any</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o.replace(/_/g, " ")}
          </option>
        ))}
      </select>
    </label>
  );
}

function HitRow({ hit, onOpen }: { hit: SearchHit; onOpen: (h: SearchHit) => void }) {
  const meta = TYPE_META[hit.type];
  const Icon = meta.icon;
  const m = hit.meta as Record<string, string | number | string[] | null | undefined>;
  const chips: string[] = [];
  if (hit.type === "cards") chips.push(String(m.kind ?? ""), String(m.category ?? "").replace(/_/g, " "), `evidence: ${m.evidence_level}`, `${m.persons ?? 0} persons`);
  if (hit.type === "contents") chips.push(String(m.platform ?? ""), String(m.content_type ?? ""), String(m.published_at ?? "").slice(0, 10));
  if (hit.type === "skills") chips.push(String(m.person ?? ""), String(m.category ?? "").replace(/_/g, " "));
  if (hit.type === "persons") chips.push(`${m.cards ?? 0} cards`, String(m.markets ?? ""));
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(hit)}
        className="group flex w-full cursor-pointer gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 text-left transition-all hover:border-zinc-700 hover:bg-zinc-900/70"
      >
        {hit.type === "persons" ? (
          <Avatar name={hit.title} path={m.avatar_path as string | null} size={40} />
        ) : (
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${meta.tone}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="text-sm font-bold text-zinc-100 group-hover:text-emerald-400">{hit.title}</h3>
            <span className="text-[10px] font-mono uppercase tracking-wide text-zinc-500">{meta.label}</span>
          </div>
          <Snippet text={hit.snippet} />
          <div className="flex flex-wrap items-center gap-1.5">
            {chips.filter(Boolean).map((c, i) => (
              <Badge key={i} variant="zinc">
                {c}
              </Badge>
            ))}
            {hit.ranks.vec !== undefined && <Badge variant="purple">meaning #{hit.ranks.vec}</Badge>}
            {hit.ranks.lex !== undefined && <Badge variant="blue">keyword #{hit.ranks.lex}</Badge>}
          </div>
        </div>
        <div className="hidden w-20 shrink-0 flex-col items-end justify-between sm:flex" title={`relevance ${hit.relevance} (score ${hit.score})`}>
          <span className="font-mono text-[11px] text-zinc-400">{hit.relevance.toFixed(2)}</span>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.round(hit.relevance * 100)}%` }} />
          </div>
        </div>
      </button>
    </li>
  );
}

function SearchContent() {
  const router = useRouter();
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") || "");
  const [mode, setMode] = useState<SearchMode>((sp.get("mode") as SearchMode) || "auto");
  const [types, setTypes] = useState<SearchType[]>(((sp.get("types") || "").split(",").filter((t) => ALL_TYPES.includes(t as SearchType)) as SearchType[]) || []);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [showFilters, setShowFilters] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [embed, setEmbed] = useState<EmbedStatus | null>(null);
  const [openCard, setOpenCard] = useState<number | null>(null);
  const [openContent, setOpenContent] = useState<string | null>(null);
  const [openPerson, setOpenPerson] = useState<string | null>(null);

  const active = types.length === 0 ? ALL_TYPES : types;

  useEffect(() => {
    fetch("/api/embed")
      .then((r) => r.json())
      .then((r) => r.ok && setEmbed(r.status))
      .catch(() => undefined);
  }, []);

  const run = useCallback(
    (query: string, m: SearchMode, t: SearchType[], f: Filters) => {
      if (!query.trim()) return;
      setLoading(true);
      setError(null);
      const p = new URLSearchParams({ q: query.trim(), mode: m, limit: "60" });
      if (t.length) p.set("types", t.join(","));
      const add = (k: string, v: string) => v && p.set(k, v);
      if (f.kind.length) p.set("kind", f.kind.join(","));
      add("category", f.category);
      add("evidence_min", f.evidence_min);
      add("horizon", f.horizon);
      add("min_persons", f.min_persons);
      add("since", f.since);
      add("language", f.language);
      f.platform.forEach((v) => p.append("platform", v));
      f.person
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .forEach((v) => p.append("person", v));
      if (f.skill_category && (t.length === 0 || t.includes("skills")) && !f.category) p.set("category", f.skill_category);
      fetch(`/api/search?${p.toString()}`)
        .then((r) => r.json())
        .then((r) => {
          if (!r.ok) {
            setError(r.error || "Search failed");
            setData(null);
            return;
          }
          setData(r as SearchResponse);
          setWarnings(r.warnings || []);
        })
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false));
      const url = new URLSearchParams({ q: query.trim(), mode: m });
      if (t.length) url.set("types", t.join(","));
      router.replace(`/search?${url.toString()}`, { scroll: false });
    },
    [router]
  );

  useEffect(() => {
    // a shared link (?q=…) searches once on arrival; deferred so the effect itself sets no state
    const first = sp.get("q");
    if (!first) return;
    const t = setTimeout(() => run(first, mode, types, filters), 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    run(q, mode, types, filters);
  };

  const flip = (t: SearchType) => {
    const next = types.includes(t) ? types.filter((x) => x !== t) : [...types, t];
    const eff = next.length === ALL_TYPES.length ? [] : next;
    setTypes(eff);
    if (q.trim()) run(q, mode, eff, filters);
  };

  const open = (h: SearchHit) => {
    if (h.type === "cards") setOpenCard(Number(h.id));
    else if (h.type === "contents") setOpenContent(h.id);
    else if (h.type === "persons") setOpenPerson(h.id);
    else setOpenPerson(String((h.meta as { person_id?: string }).person_id || ""));
  };

  const activeFilterCount = useMemo(
    () => Object.entries(filters).reduce((n, [, v]) => n + (Array.isArray(v) ? (v.length ? 1 : 0) : v ? 1 : 0), 0),
    [filters]
  );
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => setFilters((f) => ({ ...f, [k]: v }));
  const cardsOn = active.includes("cards");
  const contentsOn = active.includes("contents");
  const skillsOn = active.includes("skills");
  const embedded = embed ? Object.values(embed.kinds).reduce((n, k) => n + k.embedded, 0) : 0;

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 sm:px-6">
      <div className="flex flex-col justify-between gap-2 border-b border-zinc-800 pb-5 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">Search everything</h1>
          </div>
          <p className="mt-1 font-mono text-xs text-zinc-400">Cards, content text, traders and rulebooks — keyword and meaning together, ranked in one list</p>
        </div>
        {embed && (
          <div className="font-mono text-[11px] text-zinc-500" title="Embeddings are stored in SQLite; run `finsocnet kb embed sync` after new content">
            {embedded > 0 ? (
              <span className="text-emerald-400">semantic index ready</span>
            ) : (
              <span className="text-amber-400">no embeddings yet — keyword only</span>
            )}{" "}
            · {embed.model.split("/").pop()} · {embedded} vectors
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-zinc-500" />
            <input
              autoFocus
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ask in English: how do I size a position after a losing streak?"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 py-2.5 pl-9 pr-8 font-mono text-sm text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
            />
            {q && (
              <button type="button" onClick={() => setQ("")} className="absolute right-2.5 top-3 text-zinc-500 hover:text-zinc-300" aria-label="Clear">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <button type="submit" className="cursor-pointer rounded-lg bg-emerald-600 px-5 py-2 font-mono text-sm font-medium text-white transition-colors hover:bg-emerald-500">
            Search
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="flex items-center gap-1" role="radiogroup" aria-label="Search mode">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                role="radio"
                aria-checked={mode === m.id}
                title={m.hint}
                onClick={() => {
                  setMode(m.id);
                  if (q.trim()) run(q, m.id, types, filters);
                }}
                className={`cursor-pointer rounded-md px-2.5 py-1 font-mono text-xs transition-colors ${
                  mode === m.id ? "bg-emerald-950 text-emerald-300 ring-1 ring-emerald-700" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <span className="hidden h-4 w-px bg-zinc-800 sm:block" />
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Data</span>
            {ALL_TYPES.map((t) => {
              const Icon = TYPE_META[t].icon;
              const on = active.includes(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => flip(t)}
                  aria-pressed={on}
                  className={`flex cursor-pointer items-center gap-1 rounded-md border px-2 py-1 font-mono text-[11px] transition-colors ${
                    on ? TYPE_META[t].tone : "border-zinc-800 text-zinc-600 hover:text-zinc-400"
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  {TYPE_META[t].label}
                  {data && data.facets[t] !== undefined && <span className="text-zinc-500">{data.facets[t]}</span>}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            onClick={() => setShowFilters((s) => !s)}
            className="ml-auto flex cursor-pointer items-center gap-1 rounded-md border border-zinc-800 px-2 py-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200"
            aria-expanded={showFilters}
          >
            <SlidersHorizontal className="h-3 w-3" />
            Filters{activeFilterCount ? ` (${activeFilterCount})` : ""}
          </button>
        </div>

        {showFilters && (
          <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
            {cardsOn && (
              <fieldset className="space-y-2">
                <legend className="font-mono text-[10px] uppercase tracking-wider text-cyan-400">Cards</legend>
                <div className="flex flex-wrap gap-1.5">
                  {KINDS.map((k) => (
                    <Chip key={k} active={filters.kind.includes(k)} onClick={() => set("kind", toggle(filters.kind, k))}>
                      {k}
                    </Chip>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Select label="Category" value={filters.category} options={CATEGORIES} onChange={(v) => set("category", v)} />
                  <Select label="Evidence at least" value={filters.evidence_min} options={EVIDENCE} onChange={(v) => set("evidence_min", v)} />
                  <Select label="Horizon" value={filters.horizon} options={HORIZONS} onChange={(v) => set("horizon", v)} />
                  <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
                    Min. persons
                    <input
                      type="number"
                      min={1}
                      value={filters.min_persons}
                      onChange={(e) => set("min_persons", e.target.value)}
                      className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200 focus:border-emerald-500 focus:outline-hidden"
                    />
                  </label>
                </div>
              </fieldset>
            )}
            {contentsOn && (
              <fieldset className="space-y-2">
                <legend className="font-mono text-[10px] uppercase tracking-wider text-emerald-400">Content</legend>
                <div className="flex flex-wrap gap-1.5">
                  {PLATFORMS.map((p) => (
                    <Chip key={p} active={filters.platform.includes(p)} onClick={() => set("platform", toggle(filters.platform, p))}>
                      {p}
                    </Chip>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
                    Published since
                    <input
                      type="date"
                      value={filters.since}
                      onChange={(e) => set("since", e.target.value)}
                      className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200 focus:border-emerald-500 focus:outline-hidden"
                    />
                  </label>
                  <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
                    Language
                    <input
                      type="text"
                      placeholder="en, vi, …"
                      value={filters.language}
                      onChange={(e) => set("language", e.target.value)}
                      className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200 focus:border-emerald-500 focus:outline-hidden"
                    />
                  </label>
                </div>
              </fieldset>
            )}
            {skillsOn && (
              <fieldset className="space-y-2">
                <legend className="font-mono text-[10px] uppercase tracking-wider text-amber-400">Rulebooks</legend>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Select label="Section" value={filters.skill_category} options={SKILL_CATEGORIES} onChange={(v) => set("skill_category", v)} />
                </div>
              </fieldset>
            )}
            {(cardsOn || contentsOn || skillsOn) && (
              <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
                Trader id(s), comma separated (cards, content, rulebooks)
                <input
                  type="text"
                  placeholder="tim-furey, tom-dante"
                  value={filters.person}
                  onChange={(e) => set("person", e.target.value)}
                  className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200 focus:border-emerald-500 focus:outline-hidden"
                />
              </label>
            )}
            <div className="flex justify-between">
              <button type="button" onClick={() => setFilters(EMPTY)} className="cursor-pointer font-mono text-[11px] text-zinc-500 hover:text-zinc-300">
                Reset filters
              </button>
              <button
                type="button"
                onClick={() => run(q, mode, types, filters)}
                className="cursor-pointer rounded-md bg-zinc-100 px-3 py-1 font-mono text-[11px] font-bold text-zinc-950"
              >
                Apply
              </button>
            </div>
          </div>
        )}
      </form>

      {loading && (
        <div className="flex h-32 items-center justify-center" role="status" aria-label="Searching">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      )}
      {error && <div className="rounded-lg border border-rose-900/60 bg-rose-950/30 p-3 font-mono text-xs text-rose-300">{error}</div>}
      {warnings.map((w, i) => (
        <div key={i} className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-2.5 font-mono text-[11px] text-amber-300">
          {w}
        </div>
      ))}

      {!loading && data && (
        <div className="space-y-3">
          <p className="font-mono text-[11px] text-zinc-500">
            {data.results.length} of {data.total} hits · mode <span className="text-zinc-300">{data.mode}</span>
            {Object.keys(data.filters || {}).length > 0 && <> · filters {Object.keys(data.filters).join(", ")}</>}
          </p>
          {data.results.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center font-mono text-xs text-zinc-500">
              Nothing found. Try Semantic mode, fewer filters, or different words. The knowledge base is matched in English.
            </div>
          ) : (
            <ul className="space-y-2.5">
              {data.results.map((h) => (
                <HitRow key={`${h.type}:${h.id}`} hit={h} onOpen={open} />
              ))}
            </ul>
          )}
        </div>
      )}

      {!loading && !data && !error && (
        <div className="space-y-3 rounded-2xl border border-dashed border-zinc-800 p-8 text-center">
          <p className="font-mono text-xs text-zinc-400">Try a question, a concept or a name:</p>
          <div className="flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQ(ex);
                  run(ex, mode, types, filters);
                }}
                className="cursor-pointer rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 font-mono text-xs text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      <CardModal cardId={openCard} onClose={() => setOpenCard(null)} onSelectCard={(id) => setOpenCard(id)} />
      <ContentViewerModal contentId={openContent} onClose={() => setOpenContent(null)} />
      <PersonModal
        personId={openPerson}
        onClose={() => setOpenPerson(null)}
        onSelectCard={(id) => {
          setOpenPerson(null);
          setOpenCard(id);
        }}
      />
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 font-mono text-xs text-zinc-500">Loading…</div>}>
      <SearchContent />
    </Suspense>
  );
}
