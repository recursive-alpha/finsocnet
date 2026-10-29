import type { CardCitation } from "./types";

/** Seconds into a media item, from a citation locator (`start_sec`) when present. */
export function startSeconds(locator?: Record<string, unknown> | string | null): number | null {
  if (!locator || typeof locator === "string") return null;
  const v = locator["start_sec"];
  return typeof v === "number" && v >= 0 ? Math.floor(v) : null;
}

export function formatTime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

/** A link that opens the cited place: YouTube at the second, a PDF at the page, otherwise the page itself. */
export function citationLink(c: Pick<CardCitation, "content_url" | "locator" | "content_platform">): { href: string; label: string } | null {
  const url = c.content_url;
  if (!url) return null;
  const loc = c.locator as Record<string, unknown> | undefined;
  const t = startSeconds(loc);
  if (t !== null && /youtube\.com|youtu\.be/.test(url)) {
    return { href: `${url}${url.includes("?") ? "&" : "?"}t=${t}s`, label: `open at ${formatTime(t)}` };
  }
  const page = loc && typeof loc["page"] === "number" ? (loc["page"] as number) : null;
  if (page !== null && /\.pdf(\?|$)/i.test(url)) return { href: `${url}#page=${page}`, label: `open page ${page}` };
  return { href: url, label: "open source" };
}

export function hostOf(url?: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}
