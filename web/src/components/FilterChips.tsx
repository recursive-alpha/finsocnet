"use client";

import type { TaxItem } from "@/lib/taxonomy";

interface FilterChipsProps {
  label: string;
  items: TaxItem[] | undefined;
  value: string;
  onChange: (id: string) => void;
  /** Total shown on the "all" chip. */
  total?: number;
  /** Show the group name before each run of chips (the lists are ordered by group). */
  grouped?: boolean;
  /** Hide entries with no rows (the catch-all is always kept). */
  hideEmpty?: boolean;
  catchAll?: string | null;
}

/** A fixed list of filter chips from the static taxonomy, with counts; empty ones are dimmed, never removed (the list does not change with the data). */
export function FilterChips({ label, items, value, onChange, total, grouped = false, hideEmpty = false, catchAll }: FilterChipsProps) {
  if (!items) {
    return (
      <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
        <span className="w-20 shrink-0">{label}</span>
        <span className="h-6 w-48 animate-pulse rounded bg-zinc-800/70" />
      </div>
    );
  }
  const shown = items.filter((i) => !hideEmpty || i.count > 0 || i.id === catchAll || i.id === value);
  const chip = (id: string, text: string, count: number | undefined, hint?: string) => {
    const active = value === id;
    return (
      <button
        key={id}
        onClick={() => onChange(id)}
        title={hint}
        aria-pressed={active}
        className={`rounded-md border px-2 py-0.5 text-[11px] font-mono transition-colors ${
          active
            ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
            : count === 0
              ? "border-zinc-800/60 text-zinc-600 hover:text-zinc-400"
              : "border-zinc-700/60 bg-zinc-800/60 text-zinc-300 hover:border-zinc-600 hover:text-zinc-100"
        }`}
      >
        {text}
        {count !== undefined && <span className="ml-1 text-zinc-500">{count}</span>}
      </button>
    );
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 w-20 shrink-0 text-[11px] font-mono uppercase tracking-wider text-zinc-500">{label}</span>
      {chip("all", "all", total)}
      {shown.map((i, idx) => {
        const header = grouped && i.group && i.group !== (shown[idx - 1]?.group ?? "") ? <span key={`g-${i.group}`} className="ml-2 text-[10px] font-mono uppercase text-zinc-600">{i.group}</span> : null;
        return (
          <span key={i.id} className="contents">
            {header}
            {chip(i.id, i.label, i.count, i.hint)}
          </span>
        );
      })}
    </div>
  );
}
