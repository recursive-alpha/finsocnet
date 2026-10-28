import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?:
    | "default"
    | "emerald"
    | "blue"
    | "amber"
    | "purple"
    | "rose"
    | "zinc"
    | "outline";
  size?: "sm" | "md";
  className?: string;
}

export function Badge({
  children,
  variant = "default",
  size = "sm",
  className = "",
}: BadgeProps) {
  const variantStyles = {
    default: "bg-zinc-800 text-zinc-300 border-zinc-700",
    emerald: "bg-emerald-950/60 text-emerald-400 border-emerald-800/60",
    blue: "bg-blue-950/60 text-blue-400 border-blue-800/60",
    amber: "bg-amber-950/60 text-amber-400 border-amber-800/60",
    purple: "bg-purple-950/60 text-purple-400 border-purple-800/60",
    rose: "bg-rose-950/60 text-rose-400 border-rose-800/60",
    zinc: "bg-zinc-900 text-zinc-400 border-zinc-800",
    outline: "bg-transparent text-zinc-400 border-zinc-700",
  }[variant];

  const sizeStyles = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs font-medium";

  return (
    <span
      className={`inline-flex items-center rounded-md border font-mono tracking-tight transition-colors ${sizeStyles} ${variantStyles} ${className}`}
    >
      {children}
    </span>
  );
}

export function PlatformBadge({ platform }: { platform: string }) {
  const p = platform.toLowerCase();
  let variant: BadgeProps["variant"] = "default";
  if (p === "youtube") variant = "rose";
  else if (p === "x" || p === "twitter") variant = "zinc";
  else if (p === "reddit") variant = "amber";
  else if (p === "medium") variant = "emerald";
  else if (p === "arxiv") variant = "blue";
  else if (p === "book" || p === "annas_archive") variant = "purple";
  else if (p === "podcast") variant = "purple";
  else if (p === "substack") variant = "amber";

  return <Badge variant={variant}>{platform}</Badge>;
}

export function CategoryBadge({ category }: { category: string }) {
  const c = category.toLowerCase();
  let variant: BadgeProps["variant"] = "default";
  if (c.includes("entry") || c.includes("execution")) variant = "emerald";
  else if (c.includes("risk") || c.includes("sizing")) variant = "rose";
  else if (c.includes("setup") || c.includes("screening")) variant = "blue";
  else if (c.includes("trade") || c.includes("management")) variant = "amber";
  else if (c.includes("psychology") || c.includes("review")) variant = "purple";
  else if (c.includes("concept") || c.includes("dynamics")) variant = "zinc";

  return <Badge variant={variant}>{category.replace(/_/g, " ")}</Badge>;
}
