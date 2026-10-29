"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Brain, ExternalLink, Eye, Layers, User, X } from "lucide-react";
import { CardDetail } from "./CardModal";
import { ContentDetail } from "./ContentViewerModal";
import { ModalFrame } from "./ModalFrame";
import { mentionedResources } from "@/lib/identifiers";
import { Avatar } from "./Avatar";
import { Badge, CategoryBadge, PlatformBadge } from "./Badge";
import { Markdown } from "./Markdown";
import { ListSkeleton, Skeleton } from "./Loading";
import { hostOf } from "@/lib/links";
import type { KnowledgeCard, Person, PersonSkill } from "@/lib/types";

interface PersonModalProps {
  personId: string | null;
  onClose: () => void;
  onSelectCard?: (id: number) => void;
}

type Tab = "overview" | "cards" | "sources" | "rulebook";

const KIND_ORDER = ["website", "social", "video", "audio", "newsletter", "book", "course", "paper", "scholar", "wiki", "code", "store", "other"];
const KIND_LABEL: Record<string, string> = {
  website: "Websites", social: "Social networks", video: "Video", audio: "Podcasts & audio", newsletter: "Newsletters & blogs", book: "Books",
  course: "Courses & communities", paper: "Papers", scholar: "Scholar profiles", wiki: "Encyclopedia", code: "Code", store: "Stores", other: "Other",
};

export function PersonModal(props: PersonModalProps) {
  // Remount per person: state starts clean without resetting it inside an effect.
  if (!props.personId) return null;
  return <PersonPopup key={props.personId} {...props} personId={props.personId} />;
}

/** The frame and the inner views live together so Escape steps back (card/content -> profile) before it closes. */
function PersonPopup({ personId, onClose }: PersonModalProps & { personId: string }) {
  const [view, setView] = useState<View>({ kind: "tabs" });
  return (
    <ModalFrame onClose={onClose} onEscape={() => (view.kind === "tabs" ? onClose() : setView({ kind: "tabs" }))} width="max-w-5xl" label="Person">
      <PersonModalBody personId={personId} onClose={onClose} view={view} setView={setView} />
    </ModalFrame>
  );
}

type View = { kind: "tabs" } | { kind: "card"; id: number } | { kind: "content"; id: string };

function PersonModalBody({ personId, onClose, view, setView }: PersonModalProps & { personId: string; view: View; setView: (v: View) => void }) {
  const [person, setPerson] = useState<Person | null>(null);
  const [cardsByCategory, setCardsByCategory] = useState<Record<string, KnowledgeCard[]>>({});
  const [rulebook, setRulebook] = useState<{ markdown: string; skills: PersonSkill[] } | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/persons/${personId}`)
      .then((res) => res.json())
      .then((res) => {
        if (cancelled) return;
        if (res.ok) {
          setPerson(res.person);
          setCardsByCategory(res.cards?.categories || {});
          setRulebook(res.rulebook || null);
        } else {
          setError(res.error || "Failed to load person");
        }
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [personId]);

  const totalCards = Object.values(cardsByCategory).reduce((acc, list) => acc + list.length, 0);
  const hasRulebook = Boolean(rulebook?.markdown || (rulebook?.skills && rulebook.skills.length > 0));

  const resources = useMemo(() => (person ? mentionedResources(person) : []), [person]);

  const linkGroups = useMemo(() => {
    const groups: Record<string, NonNullable<Person["links"]>> = {};
    (person?.links || []).forEach((l) => {
      if (l.match_status === "rejected") return;
      (groups[l.kind] = groups[l.kind] || []).push(l);
    });
    return KIND_ORDER.filter((k) => groups[k]).map((k) => [k, groups[k]] as const);
  }, [person]);

  const tabs: Array<{ id: Tab; label: string; icon: typeof User; count?: number }> = [
    { id: "overview", label: "Overview", icon: User },
    { id: "cards", label: "Knowledge cards", icon: Brain, count: totalCards },
    { id: "sources", label: "Sources", icon: Layers, count: person?.sources?.length },
    { id: "rulebook", label: "Rulebook", icon: BookOpen },
  ];

  const back = { label: person?.canonical_name || "Back", run: () => setView({ kind: "tabs" }) };
  if (view.kind === "card") {
    return <CardDetail key={view.id} cardId={view.id} onClose={onClose} onBack={back} onSelectCard={(id) => setView({ kind: "card", id })} />;
  }
  if (view.kind === "content") {
    return <ContentDetail key={view.id} contentId={view.id} onClose={onClose} onBack={back} />;
  }

  return (
    <>
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-zinc-800/80 bg-zinc-900/50 px-6 py-5">
          <div className="flex min-w-0 items-center gap-4">
            <Avatar name={person?.canonical_name || personId} path={person?.avatar_path} size={72} className="rounded-2xl" />
            <div className="min-w-0 space-y-1">
              {person ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-bold text-zinc-100">{person.canonical_name}</h2>
                    {person.moniker && <span className="text-xs font-mono text-zinc-400">({person.moniker})</span>}
                    {person.profession && <Badge variant="emerald">{person.profession.replace(/_/g, " ")}</Badge>}
                  </div>
                  {person.affiliation && <p className="text-xs font-mono text-zinc-400">{person.affiliation}</p>}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {person.homepage && (
                      <a href={person.homepage} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 rounded-md border border-zinc-800 px-2 py-0.5 text-[11px] font-mono text-zinc-300 hover:border-emerald-500/50 hover:text-emerald-400">
                        <ExternalLink className="h-3 w-3" />
                        {hostOf(person.homepage)}
                      </a>
                    )}
                    {(person.links || [])
                      .filter((l) => l.kind === "social" && l.match_status === "confirmed")
                      .slice(0, 6)
                      .map((l) => (
                        <a key={l.id} href={l.url} target="_blank" rel="noopener noreferrer" title={l.evidence || ""} className="rounded-md border border-zinc-800 px-2 py-0.5 text-[11px] font-mono text-zinc-400 hover:border-emerald-500/50 hover:text-emerald-400">
                          {l.platform || hostOf(l.url)}
                        </a>
                      ))}
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-3 w-64" />
                </div>
              )}
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex shrink-0 gap-1 overflow-x-auto overflow-y-hidden border-b border-zinc-800 bg-zinc-900/40 px-4 pt-2">
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono font-medium transition-colors ${
                  activeTab === t.id ? "border-emerald-500 text-emerald-400" : "border-transparent text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{t.label}</span>
                {t.count !== undefined && <span className="text-zinc-500">{t.count}</span>}
              </button>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-sm text-rose-400">{error}</div>}
          {loading && !person && <ListSkeleton rows={6} />}

          {person && activeTab === "overview" && (
            <div className="space-y-6">
              {person.bio && (
                <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
                  <Markdown>{person.bio}</Markdown>
                </section>
              )}

              <section className="grid grid-cols-1 gap-3 text-xs font-mono sm:grid-cols-2">
                {[
                  ["Profession", person.profession?.replace(/_/g, " ")],
                  ["Affiliation", person.affiliation],
                  ["Fields", person.domains],
                  ["Markets", person.primary_markets],
                  ["Style", person.trading_style],
                  ["Why in scope", person.relevance],
                ]
                  .filter(([, v]) => v)
                  .map(([k, v]) => (
                    <div key={k as string} className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-3">
                      <div className="mb-1 text-[10px] uppercase tracking-wider text-zinc-500">{k}</div>
                      <div className="leading-relaxed text-zinc-200">{v}</div>
                    </div>
                  ))}
              </section>

              {linkGroups.length > 0 && (
                <section className="space-y-4">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500">Links &amp; social networks ({person.links?.filter((l) => l.match_status !== "rejected").length})</h3>
                  {linkGroups.map(([kind, links]) => (
                    <div key={kind} className="space-y-2">
                      <div className="text-[11px] font-mono text-zinc-400">{KIND_LABEL[kind] || kind}</div>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {links.map((l) => (
                          <a
                            key={l.id}
                            href={l.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={l.evidence || ""}
                            className="group flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 transition-colors hover:border-emerald-500/50"
                          >
                            <span className="min-w-0">
                              <span className="block truncate text-xs font-mono text-zinc-200">{l.label || l.handle || hostOf(l.url) || l.url}</span>
                              <span className="block truncate text-[10px] font-mono text-zinc-500">{[l.platform, hostOf(l.url)].filter(Boolean).join(" · ")}</span>
                            </span>
                            <span className="flex shrink-0 items-center gap-1.5">
                              {l.match_status !== "confirmed" && <Badge variant="amber">to review</Badge>}
                              <ExternalLink className="h-3.5 w-3.5 text-zinc-500 group-hover:text-emerald-400" />
                            </span>
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                  <p className="text-[11px] font-mono text-zinc-600">Hover a link to read the evidence that it belongs to this person.</p>
                </section>
              )}

              {resources.length > 0 && (
                <section className="space-y-2">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500">Other places mentioned in the profile ({resources.length})</h3>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {resources.map((r) => (
                      <a key={r.href} href={r.href} target="_blank" rel="noopener noreferrer" className="group flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 transition-colors hover:border-emerald-500/50">
                        <span className="min-w-0">
                          <span className="block truncate text-xs font-mono text-zinc-200">{r.label}</span>
                          <span className="block truncate text-[10px] font-mono text-zinc-500">{r.value}</span>
                        </span>
                        <span className="flex shrink-0 items-center gap-1.5">
                          <Badge variant="zinc">{r.kind}</Badge>
                          <ExternalLink className="h-3.5 w-3.5 text-zinc-500 group-hover:text-emerald-400" />
                        </span>
                      </a>
                    ))}
                  </div>
                </section>
              )}

              {person.aliases && person.aliases.length > 0 && (
                <section className="space-y-2">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500">Known names &amp; handles ({person.aliases.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {person.aliases.map((a, idx) => (
                      <span key={idx} className="rounded-md border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-xs font-mono text-zinc-300">
                        {a.alias} {a.platform && <span className="text-zinc-500">({a.platform})</span>}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}

          {person && activeTab === "cards" && (
            <div className="space-y-6">
              {totalCards === 0 ? (
                <Empty>No knowledge cards are attributed to this person yet.</Empty>
              ) : (
                Object.entries(cardsByCategory).map(([cat, list]) => (
                  <div key={cat} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <CategoryBadge category={cat} />
                      <span className="text-xs font-mono text-zinc-400">{list.length} cards</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3">
                      {list.map((c) => {
                        const cite = (c.citations || [])[0];
                        return (
                          <div key={c.id} onClick={() => setView({ kind: "card", id: c.id })} className="cursor-pointer space-y-2 rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 transition-colors hover:border-zinc-700">
                            <div className="flex items-center justify-between gap-2 text-xs font-mono">
                              <span className="font-semibold text-emerald-400">#{c.id} {c.subject}</span>
                              <Badge variant="zinc">{c.action}</Badge>
                            </div>
                            <p className="line-clamp-2 text-xs font-mono text-zinc-300">{c.claim}</p>
                            {cite?.content_url && (
                              <a href={cite.content_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-500 hover:text-emerald-400">
                                <ExternalLink className="h-3 w-3" />
                                <span className="max-w-[28rem] truncate">{cite.content_title || cite.content_url}</span>
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {person && activeTab === "sources" && (
            <div className="space-y-6">
              {person.sources && person.sources.length > 0 ? (
                <div className="space-y-2">
                  {person.sources.map((s) => (
                    <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2">
                          <PlatformBadge platform={s.platform} />
                          <span className="truncate text-sm font-semibold text-zinc-100">{s.title || s.id}</span>
                        </div>
                        {s.url && (
                          <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-500 hover:text-emerald-400">
                            <ExternalLink className="h-3 w-3" />
                            {hostOf(s.url)}
                          </a>
                        )}
                      </div>
                      <div className="flex gap-4 text-center font-mono text-xs">
                        <div><div className="text-base font-bold text-zinc-100">{s.contents ?? 0}</div><div className="text-[10px] text-zinc-500">listed</div></div>
                        <div><div className="text-base font-bold text-zinc-100">{s.fetched ?? 0}</div><div className="text-[10px] text-zinc-500">fetched</div></div>
                        <div><div className="text-base font-bold text-emerald-400">{s.mined ?? 0}</div><div className="text-[10px] text-zinc-500">mined</div></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty>No sources are linked to this person yet.</Empty>
              )}

              {person.appearances && person.appearances.filter((a) => a.content_id).length > 0 && (
                <section className="space-y-2">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500">Appearances in content ({person.appearances.filter((a) => a.content_id).length})</h3>
                  {person.appearances.filter((a) => a.content_id).map((a, i) => (
                    <div key={i} className="flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-xs font-mono">
                      <button onClick={() => setView({ kind: "content", id: a.content_id })} className="group min-w-0 flex-1 text-left">
                        <span className="flex items-center gap-1.5 truncate text-zinc-200 group-hover:text-emerald-400">
                          <Eye className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                          <span className="truncate">{a.title || a.content_id}</span>
                        </span>
                        <span className="text-[11px] text-zinc-500">{a.role}{a.match_status && a.match_status !== "confirmed" ? " · to review" : ""}</span>
                      </button>
                      <div className="flex shrink-0 items-center gap-2">
                        {a.platform && <PlatformBadge platform={a.platform} />}
                        {a.url && (
                          <a href={a.url} target="_blank" rel="noopener noreferrer" title="Open the original page" className="rounded-md border border-zinc-800 p-1 text-zinc-400 hover:border-emerald-500/50 hover:text-emerald-400">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </section>
              )}
            </div>
          )}

          {person && activeTab === "rulebook" && (
            <div className="space-y-4">
              {rulebook?.markdown ? (
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
                  <Markdown>{rulebook.markdown}</Markdown>
                </div>
              ) : hasRulebook ? (
                rulebook!.skills.map((skill) => (
                  <div key={skill.id} className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <span className="text-sm font-bold text-zinc-100">{skill.title}</span>
                      <CategoryBadge category={skill.category} />
                    </div>
                    {skill.summary && <p className="text-xs italic text-zinc-400">{skill.summary}</p>}
                    <Markdown>{skill.content_markdown}</Markdown>
                  </div>
                ))
              ) : (
                <Empty>No rulebook yet. It is synthesized once a person has five or more cards.</Empty>
              )}
            </div>
          )}
        </div>
    </>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-zinc-800 py-12 text-center text-xs font-mono text-zinc-500">{children}</div>;
}
