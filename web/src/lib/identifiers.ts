import type { Person } from "./types";

export interface ResourceLink {
  label: string;
  value: string;
  href: string;
  /** `identifier`: an id from a scholar or reference database; `account`: a handle on a platform; `site`: a web address. */
  kind: "identifier" | "account" | "site";
}

const IDENTIFIERS: Record<string, { label: string; url: (v: string) => string }> = {
  openalex: { label: "OpenAlex", url: (v) => `https://openalex.org/${v}` },
  orcid: { label: "ORCID", url: (v) => `https://orcid.org/${v}` },
  google_scholar: { label: "Google Scholar", url: (v) => `https://scholar.google.com/citations?user=${v}` },
  semantic_scholar: { label: "Semantic Scholar", url: (v) => `https://www.semanticscholar.org/author/${v}` },
  ssrn: { label: "SSRN", url: (v) => `https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=${v}` },
  repec: { label: "RePEc", url: (v) => `https://ideas.repec.org/e/${v}.html` },
  nber: { label: "NBER", url: (v) => `https://www.nber.org/people/${v}` },
  wikipedia: { label: "Wikipedia", url: (v) => `https://en.wikipedia.org/wiki/${encodeURI(v)}` },
  wikidata: { label: "Wikidata", url: (v) => `https://www.wikidata.org/wiki/${v}` },
  dblp: { label: "dblp", url: (v) => `https://dblp.org/pid/${v}` },
  arxiv: { label: "arXiv author", url: (v) => `https://arxiv.org/a/${v}` },
  github: { label: "GitHub", url: (v) => `https://github.com/${v.replace(/^@/, "")}` },
  isni: { label: "ISNI", url: (v) => `https://isni.org/isni/${v.replace(/\s/g, "")}` },
  viaf: { label: "VIAF", url: (v) => `https://viaf.org/viaf/${v}` },
};

const HANDLES: Record<string, { label: string; url: (h: string) => string }> = {
  x: { label: "X", url: (h) => `https://x.com/${h}` },
  twitter: { label: "X", url: (h) => `https://x.com/${h}` },
  youtube: { label: "YouTube", url: (h) => (h.startsWith("UC") && h.length > 20 ? `https://www.youtube.com/channel/${h}` : `https://www.youtube.com/@${h}`) },
  instagram: { label: "Instagram", url: (h) => `https://www.instagram.com/${h}` },
  tiktok: { label: "TikTok", url: (h) => `https://www.tiktok.com/@${h}` },
  threads: { label: "Threads", url: (h) => `https://www.threads.net/@${h}` },
  bluesky: { label: "Bluesky", url: (h) => `https://bsky.app/profile/${h}` },
  reddit: { label: "Reddit", url: (h) => `https://www.reddit.com/user/${h}` },
  substack: { label: "Substack", url: (h) => `https://${h}.substack.com` },
  medium: { label: "Medium", url: (h) => `https://medium.com/@${h}` },
  stocktwits: { label: "StockTwits", url: (h) => `https://stocktwits.com/${h}` },
  tradingview: { label: "TradingView", url: (h) => `https://www.tradingview.com/u/${h}` },
  telegram: { label: "Telegram", url: (h) => `https://t.me/${h}` },
  linkedin: { label: "LinkedIn", url: (h) => `https://www.linkedin.com/in/${h}` },
  github: { label: "GitHub", url: (h) => `https://github.com/${h}` },
};

const clean = (h: string) => h.replace(/^@/, "").trim();
const isUrl = (v: string) => /^https?:\/\//i.test(v);

/**
 * Every resource a person record mentions, as clickable links: homepage, external ids (OpenAlex, ORCID, Scholar, SSRN, Wikipedia, ...)
 * and platform aliases (handle + platform). Stored profile links (kind, evidence) are shown separately; entries whose URL already
 * appears there are left out so nothing is listed twice.
 */
export function mentionedResources(p: Person): ResourceLink[] {
  const seen = new Set((p.links || []).map((l) => l.url.replace(/\/$/, "").toLowerCase()));
  const out: ResourceLink[] = [];
  const add = (r: ResourceLink) => {
    const key = r.href.replace(/\/$/, "").toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push(r);
  };
  if (p.homepage) add({ label: "Homepage", value: p.homepage.replace(/^https?:\/\//, "").replace(/\/$/, ""), href: p.homepage, kind: "site" });
  for (const [k, v] of Object.entries(p.external_ids || {})) {
    if (!v) continue;
    const spec = IDENTIFIERS[k.toLowerCase()];
    if (isUrl(v)) add({ label: spec?.label || k, value: v.replace(/^https?:\/\//, ""), href: v, kind: "identifier" });
    else if (spec) add({ label: spec.label, value: v, href: spec.url(v), kind: "identifier" });
  }
  for (const a of p.aliases || []) {
    const platform = (a.platform || "").toLowerCase();
    const spec = HANDLES[platform];
    const handle = clean(a.alias);
    if (!spec || !handle || /\s/.test(handle)) continue;
    add({ label: spec.label, value: `@${handle}`, href: spec.url(handle), kind: "account" });
  }
  return out;
}
