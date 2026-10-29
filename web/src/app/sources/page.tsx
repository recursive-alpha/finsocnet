"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  ExternalLink,
  Filter,
  Layers,
  Search,
  User,
} from "lucide-react";
import { Badge, PlatformBadge } from "@/components/Badge";
import { FilterChips } from "@/components/FilterChips";
import { useTaxonomy } from "@/lib/taxonomy";
import type { Source } from "@/lib/types";

function SourcesPageInner() {
  const [sources, setSources] = useState<Source[]>([]);
  const [medium, setMedium] = useState(useSearchParams().get("medium") || "all");
  const [kind, setKind] = useState("all");
  const [status, setStatus] = useState("all");
  const tax = useTaxonomy();
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (medium !== "all") params.set("medium", medium);
    if (kind !== "all") params.set("kind", kind);
    if (status !== "all") params.set("status", status);
    fetch(`/api/sources?${params.toString()}`)
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setSources(r.sources || []);
      })
      .finally(() => setLoading(false));
  }, [medium, kind, status]);

  const filtered = sources.filter((s) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      s.id.toLowerCase().includes(q) ||
      s.handle_or_name?.toLowerCase().includes(q) ||
      s.platform.toLowerCase().includes(q) ||
      (s.title && s.title.toLowerCase().includes(q))
    );
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Sources & Channels Directory
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Tracked media channels, creator profiles, and feeds across platforms
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{sources.length} sources registered</Badge>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search sources by name, handle, or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-4 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
          />
        </div>

        <div className="space-y-2.5 pt-1">
          <FilterChips label="Medium" items={tax?.["sources.medium"]?.items} value={medium} onChange={(v) => { setLoading(true); setMedium(v); }} grouped />
          <FilterChips label="Kind" items={tax?.["sources.kind"]?.items} value={kind} onChange={(v) => { setLoading(true); setKind(v); }} hideEmpty catchAll="other" />
          <FilterChips label="Status" items={tax?.["sources.status"]?.items} value={status} onChange={(v) => { setLoading(true); setStatus(v); }} />
        </div>
      </div>

      {/* Sources Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
          No sources match your filters.
        </div>
      ) : (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-zinc-800 bg-zinc-900/80 text-[11px] uppercase tracking-wider text-zinc-400">
                <tr>
                  <th className="py-3 px-4">Platform</th>
                  <th className="py-3 px-4">Handle & Title</th>
                  <th className="py-3 px-4">Kind</th>
                  <th className="py-3 px-4">Person ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">URL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filtered.map((s) => (
                  <tr key={s.id} className="hover:bg-zinc-800/40 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <PlatformBadge platform={s.platform} />
                    </td>
                    <td className="py-3.5 px-4 max-w-sm">
                      <div className="font-semibold text-zinc-200 truncate">
                        {s.title || s.handle_or_name}
                      </div>
                      <div className="text-[11px] text-zinc-500 truncate mt-0.5">
                        {s.id}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-zinc-300">
                      <Badge variant="zinc">{s.kind}</Badge>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-zinc-300">
                      {s.person_id ? (
                        <span className="flex items-center gap-1 text-emerald-400">
                          <User className="h-3 w-3" />
                          <span>{s.person_id}</span>
                        </span>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <Badge variant={s.status === "active" ? "emerald" : "amber"}>
                        {s.status}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      {s.url ? (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 transition-colors"
                        >
                          <span>Open</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SourcesPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><div className="h-64 animate-pulse rounded-2xl bg-zinc-900/60" /></div>}>
      <SourcesPageInner />
    </Suspense>
  );
}
