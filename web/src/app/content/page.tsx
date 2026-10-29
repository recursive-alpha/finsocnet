"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Calendar,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Layers,
  Search,
  Video,
} from "lucide-react";
import { Badge, PlatformBadge } from "@/components/Badge";
import { ContentViewerModal } from "@/components/ContentViewerModal";
import { FilterChips } from "@/components/FilterChips";
import { useTaxonomy } from "@/lib/taxonomy";
import type { ContentItem } from "@/lib/types";

const PLATFORMS = ["all", "youtube", "substack", "podcast", "book", "medium", "x", "reddit", "arxiv"];
const STATUSES = ["all", "metadata_only", "needs_review", "new", "processed"];

function ContentPageInner() {
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [medium, setMedium] = useState(useSearchParams().get("medium") || "all");
  const [status, setStatus] = useState("all");
    const tax = useTaxonomy();
  const [search, setSearch] = useState("");
  const [selectedContentId, setSelectedContentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchContents = (m = medium, st = status) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (m !== "all") params.set("medium", m);
    if (st !== "all") params.set("status", st);
    params.set("limit", "100");

    fetch(`/api/content?${params.toString()}`)
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setContents(r.contents || []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchContents(medium, status);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medium, status]);

  const filtered = contents.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (c.title && c.title.toLowerCase().includes(q)) ||
      c.id.toLowerCase().includes(q) ||
      (c.author_handle && c.author_handle.toLowerCase().includes(q)) ||
      (c.platform && c.platform.toLowerCase().includes(q))
    );
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Video className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Content & Transcripts Catalog
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Media catalog across platforms with timestamped transcript segment windows
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{contents.length} items loaded</Badge>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search by title, id, author or platform…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-4 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
          />
        </div>

        <div className="space-y-2.5 pt-1">
          <FilterChips label="Medium" items={tax?.["content.medium"]?.items} value={medium} onChange={setMedium} grouped />
          <FilterChips label="Status" items={tax?.["content.status"]?.items} value={status} onChange={setStatus} />
        </div>
      </div>

      {/* Content List Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
          No content matches your filters.
        </div>
      ) : (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-zinc-800 bg-zinc-900/80 text-[11px] uppercase tracking-wider text-zinc-400">
                <tr>
                  <th className="py-3 px-4">Platform</th>
                  <th className="py-3 px-4">Title & ID</th>
                  <th className="py-3 px-4">Author / Handle</th>
                  <th className="py-3 px-4">Segments</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filtered.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedContentId(item.id)}
                    className="hover:bg-zinc-800/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <PlatformBadge platform={item.platform} />
                    </td>
                    <td className="py-3.5 px-4 max-w-md">
                      <div className="font-semibold text-zinc-200 line-clamp-1">
                        {item.title || "Untitled Content"}
                      </div>
                      <div className="text-[11px] text-zinc-500 truncate mt-0.5">
                        {item.id}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-zinc-300">
                      {item.author_handle || item.person_id || "—"}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-zinc-300">
                      <span className="flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5 text-zinc-500" />
                        <span>{item.segments || 0}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <Badge
                        variant={
                          item.process_status === "processed"
                            ? "emerald"
                            : item.process_status === "needs_review"
                            ? "amber"
                            : "zinc"
                        }
                      >
                        {item.process_status}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <span className="text-emerald-400 hover:text-emerald-300 font-semibold">
                        View text →
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Content Viewer Modal */}
      <ContentViewerModal
        contentId={selectedContentId}
        onClose={() => setSelectedContentId(null)}
      />
    </div>
  );
}

export default function ContentPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><div className="h-64 animate-pulse rounded-2xl bg-zinc-900/60" /></div>}>
      <ContentPageInner />
    </Suspense>
  );
}
