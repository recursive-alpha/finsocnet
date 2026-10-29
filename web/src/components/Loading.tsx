"use client";

import { useEffect, useState } from "react";

export function Spinner({ label = "Loading", className = "" }: { label?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={`flex items-center justify-center gap-3 py-16 text-xs font-mono text-zinc-500 ${className}`}>
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
      <span>{label}…</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-zinc-800/70 ${className}`} />;
}

/** Placeholder rows shaped like the card grid while the list loads. */
export function CardGridSkeleton({ count = 9 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-5 w-24" />
          </div>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <div className="flex items-center gap-2 border-t border-zinc-800/60 pt-3">
            <Skeleton className="h-7 w-7 rounded-lg" />
            <Skeleton className="h-3 w-28" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PersonGridSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-4">
          <Skeleton className="h-14 w-14 rounded-xl" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ListSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full rounded-xl" />
      ))}
    </div>
  );
}

/**
 * A thin progress bar under the header whenever any /api request is in flight, so every page shows that it is loading
 * without each fetch call having to report it.
 */
export function TopLoader() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const original = window.fetch;
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const url = typeof args[0] === "string" ? args[0] : args[0] instanceof URL ? args[0].href : (args[0] as Request).url;
      const tracked = url.includes("/api/");
      if (tracked) setActive((n) => n + 1);
      try {
        return await original(...args);
      } finally {
        if (tracked) setActive((n) => Math.max(0, n - 1));
      }
    };
    return () => {
      window.fetch = original;
    };
  }, []);

  return (
    <div className={`pointer-events-none fixed inset-x-0 top-0 z-[60] h-0.5 overflow-hidden transition-opacity duration-200 ${active > 0 ? "opacity-100" : "opacity-0"}`}>
      <div className="top-loader-bar h-full w-1/3 bg-emerald-400" />
    </div>
  );
}
