import React from "react";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  badge?: string;
  trend?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  className = "",
}: StatCardProps) {
  return (
    <div
      className={`rounded-xl border border-zinc-800/80 bg-zinc-900/50 p-4 backdrop-blur-xs transition-all hover:border-zinc-700/80 ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-400 font-mono tracking-tight uppercase">
          {title}
        </span>
        {Icon && (
          <div className="rounded-lg bg-zinc-800/60 p-1.5 text-zinc-400">
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-zinc-100 font-mono">
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {badge && (
          <span className="rounded bg-emerald-950/80 px-1.5 py-0.5 text-[10px] font-mono font-medium text-emerald-400 border border-emerald-800/50">
            {badge}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-zinc-500 line-clamp-1">{subtitle}</p>
      )}
    </div>
  );
}
