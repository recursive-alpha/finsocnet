import Link from "next/link";
import { Avatar } from "./Avatar";
import type { CardPerson } from "@/lib/types";

/** Who a card comes from: overlapping pictures and the first names. */
export function PeopleStack({ people, size = 28 }: { people?: CardPerson[]; size?: number }) {
  if (!people || people.length === 0) {
    return <span className="text-[11px] font-mono text-zinc-600">author not identified yet</span>;
  }
  const shown = people.slice(0, 3);
  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="flex shrink-0 -space-x-2">
        {shown.map((p) => (
          <Link key={p.id} href={`/persons?open=${encodeURIComponent(p.id)}`} onClick={(e) => e.stopPropagation()} title={p.name}>
            <Avatar name={p.name} path={p.avatar} size={size} className="ring-2 ring-zinc-950" />
          </Link>
        ))}
      </div>
      <span className="min-w-0 truncate text-[11px] font-mono text-zinc-300">
        {shown.map((p) => p.name).join(", ")}
        {people.length > shown.length && <span className="text-zinc-500"> +{people.length - shown.length}</span>}
      </span>
    </div>
  );
}
