import React from "react";

interface AvatarProps {
  name: string;
  path?: string | null;
  size?: number;
  className?: string;
}

/** Person picture from data/media (served by /api/media) or initials when none is stored. */
export function Avatar({ name, path, size = 40, className = "" }: AvatarProps) {
  const box = { width: size, height: size };
  if (path) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={`/api/media/${path.replace(/^data\/media\//, "")}`}
        alt={name}
        loading="lazy"
        style={box}
        className={`shrink-0 rounded-xl border border-zinc-700 object-cover ${className}`}
      />
    );
  }
  return (
    <div
      style={{ ...box, fontSize: Math.max(10, Math.round(size / 3)) }}
      className={`flex shrink-0 items-center justify-center rounded-xl border border-zinc-700 bg-zinc-800 font-mono font-bold text-zinc-300 ${className}`}
    >
      {name.slice(0, 2).toUpperCase() || "??"}
    </div>
  );
}
