"use client";

import Link from "next/link";
import { useState } from "react";
import { Layers } from "lucide-react";
import type { TaxItem, Taxonomy } from "@/lib/taxonomy";

type Tab = "content" | "sources";
type Item = TaxItem & { fetched?: number; mined?: number; cards?: number };

const STYLE: Record<string, string> = {
  video: "bg-rose-500/80", audio: "bg-purple-500/80", article: "bg-amber-500/80", social: "bg-sky-500/80", paper: "bg-blue-500/80",
  book: "bg-fuchsia-500/80", code: "bg-zinc-400/80", document: "bg-teal-500/80", other: "bg-zinc-600/80",
};

/**
 * What we hold, by kind of thing (video, audio, article, paper, book, ...), not by platform: platforms come and go, formats do not.
 * Content bars split into listed only / fetched / mined; sources and profile links are counted by what they publish or point to.
 */
export function MediumPanel({ tax }: { tax: Taxonomy | null }) {
  const [tab, setTab] = useState<Tab>("content");
  const content = (tax?.["content.medium"]?.items || []) as Item[];
  const sources = (tax?.["sources.medium"]?.items || []) as Item[];
  const links = (tax?.["links.kind"]?.items || []) as Item[];
  const list = tab === "content" ? content : sources;
  const max = Math.max(1, ...list.map((i) => i.count));
  const total = list.reduce((a, i) => a + i.count, 0);

  return (
    <div className="space-y-4 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5">
      <div className="flex flex-col justify-between gap-2 border-b border-zinc-800/80 pb-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-emerald-400" />
          <h3 className="font-mono text-sm font-bold text-zinc-100">{tab === "content" ? "Content by medium" : "Sources by medium"}</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg bg-zinc-800/80 p-0.5 font-mono text-[11px]">
            {(["content", "sources"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-md px-2 py-0.5 transition-colors ${tab === t ? "bg-zinc-700 font-semibold text-zinc-100" : "text-zinc-400 hover:text-zinc-200"}`}
              >
                {t}
              </button>
            ))}
          </div>
          <Link href={tab === "content" ? "/content" : "/sources"} className="font-mono text-xs text-emerald-400 hover:text-emerald-300">
            all {tab} →
          </Link>
        </div>
      </div>

      {!tax ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-6 animate-pulse rounded bg-zinc-800/70" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {list.map((i) => {
            const fetched = tab === "content" ? i.fetched || 0 : 0;
            const mined = tab === "content" ? i.mined || 0 : 0;
            return (
              <Link key={i.id} href={`/${tab}?medium=${i.id}`} className="block space-y-1 rounded-lg px-1 py-0.5 hover:bg-zinc-800/40" title={i.hint}>
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-zinc-300">{i.label}</span>
                  <span className="font-semibold text-zinc-400">
                    {i.count.toLocaleString()}
                    {tab === "content" && i.count > 0 && <span className="ml-2 font-normal text-zinc-500">{fetched} fetched · {mined} mined</span>}
                  </span>
                </div>
                <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                  <div className={`absolute inset-y-0 left-0 rounded-full ${STYLE[i.id] || "bg-emerald-500/80"} opacity-40`} style={{ width: `${i.count ? Math.max((i.count / max) * 100, 2) : 0}%` }} />
                  {tab === "content" && <div className={`absolute inset-y-0 left-0 rounded-full ${STYLE[i.id] || "bg-emerald-500/80"}`} style={{ width: `${i.count ? Math.max((fetched / max) * 100, fetched ? 1.5 : 0) : 0}%` }} />}
                </div>
              </Link>
            );
          })}
          <div className="flex items-center justify-between border-t border-zinc-800/60 pt-2 font-mono text-[11px] text-zinc-500">
            <span>{total.toLocaleString()} {tab} in total</span>
            {tab === "content" && <span>light bar: listed · solid: text fetched</span>}
          </div>
          <div className="space-y-1.5 border-t border-zinc-800/60 pt-3">
            <div className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">Profile links by kind ({links.reduce((a, l) => a + l.count, 0)})</div>
            <div className="flex flex-wrap gap-1.5">
              {links.filter((l) => l.count > 0).map((l) => (
                <span key={l.id} className="inline-flex items-center gap-1 rounded-md border border-zinc-800/80 bg-zinc-900/60 px-2 py-0.5 font-mono text-[11px] text-zinc-300">
                  {l.label}
                  <span className="font-semibold text-emerald-400">{l.count}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
