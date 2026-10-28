"use client";

import { useEffect, useState } from "react";
import {
  Award,
  BookOpen,
  Brain,
  CheckCircle2,
  ExternalLink,
  Shield,
  TrendingUp,
  User,
  X,
} from "lucide-react";
import { Avatar } from "./Avatar";
import { Badge, CategoryBadge } from "./Badge";
import type { KnowledgeCard, Person, PersonSkill } from "@/lib/types";

interface PersonModalProps {
  personId: string | null;
  onClose: () => void;
  onSelectCard?: (id: number) => void;
}

export function PersonModal({ personId, onClose, onSelectCard }: PersonModalProps) {
  const [person, setPerson] = useState<Person | null>(null);
  const [cardsByCategory, setCardsByCategory] = useState<Record<string, KnowledgeCard[]>>({});
  const [rulebook, setRulebook] = useState<{ markdown: string; skills: PersonSkill[] } | null>(null);
  const [activeTab, setActiveTab] = useState<"rulebook" | "cards" | "profile">("rulebook");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!personId) {
      setPerson(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetch(`/api/persons/${personId}`)
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setPerson(res.person);
          setCardsByCategory(res.cards?.categories || {});
          setRulebook(res.rulebook || null);
        } else {
          setError(res.error || "Failed to load person");
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [personId]);

  if (!personId) return null;

  const totalCards = Object.values(cardsByCategory).reduce((acc, list) => acc + list.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
      <div
        className="relative w-full max-w-5xl max-h-[92vh] flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 px-6 py-4 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <Avatar name={person?.canonical_name || personId || "??"} path={person?.avatar_path} size={44} />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-zinc-100">
                  {person?.canonical_name || personId}
                </h2>
                {person?.moniker && (
                  <span className="text-xs text-zinc-400 font-mono">
                    ({person.moniker})
                  </span>
                )}
                <Badge variant="emerald">{person?.status || "active"}</Badge>
              </div>
              <p className="text-xs text-zinc-400 font-mono line-clamp-1">
                {person?.trading_style || [person?.profession?.replace(/_/g, " "), person?.affiliation].filter(Boolean).join(" · ") || "Market practitioner"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Controls */}
        <div className="flex border-b border-zinc-800 bg-zinc-900/40 px-6 gap-2 pt-2">
          <button
            onClick={() => setActiveTab("rulebook")}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono font-medium transition-colors ${
              activeTab === "rulebook"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span>Strategy Rulebook</span>
          </button>
          <button
            onClick={() => setActiveTab("cards")}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono font-medium transition-colors ${
              activeTab === "cards"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Brain className="h-3.5 w-3.5" />
            <span>Knowledge Cards ({totalCards})</span>
          </button>
          <button
            onClick={() => setActiveTab("profile")}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono font-medium transition-colors ${
              activeTab === "profile"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <User className="h-3.5 w-3.5" />
            <span>Profile & Appearances</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-rose-400 text-sm">
              {error}
            </div>
          )}

          {person && !loading && (
            <>
              {/* TAB 1: Rulebook */}
              {activeTab === "rulebook" && (
                <div className="space-y-6">
                  {rulebook?.markdown ? (
                    <div className="space-y-4">
                      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                        <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                          {rulebook.markdown}
                        </pre>
                      </div>
                    </div>
                  ) : rulebook?.skills && rulebook.skills.length > 0 ? (
                    <div className="space-y-4">
                      {rulebook.skills.map((skill) => (
                        <div
                          key={skill.id}
                          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-3"
                        >
                          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                            <span className="font-bold text-sm text-zinc-100 uppercase tracking-wide font-mono">
                              {skill.title}
                            </span>
                            <CategoryBadge category={skill.category} />
                          </div>
                          <p className="text-xs text-zinc-400 italic">
                            {skill.summary}
                          </p>
                          <div className="rounded-lg bg-zinc-950/60 p-4 text-xs font-mono text-zinc-200 whitespace-pre-wrap">
                            {skill.content_markdown}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-zinc-500 font-mono text-xs">
                      No synthesized rulebook available for this practitioner yet.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Knowledge Cards */}
              {activeTab === "cards" && (
                <div className="space-y-6">
                  {totalCards === 0 ? (
                    <div className="text-center py-12 text-zinc-500 font-mono text-xs">
                      No knowledge cards explicitly attributed yet.
                    </div>
                  ) : (
                    Object.entries(cardsByCategory).map(([cat, list]) => (
                      <div key={cat} className="space-y-3">
                        <div className="flex items-center gap-2">
                          <CategoryBadge category={cat} />
                          <span className="text-xs font-mono text-zinc-400">
                            ({list.length} cards)
                          </span>
                        </div>
                        <div className="grid grid-cols-1 gap-3">
                          {list.map((c) => (
                            <div
                              key={c.id}
                              onClick={() => onSelectCard?.(c.id)}
                              className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 hover:border-zinc-700 cursor-pointer transition-colors space-y-2"
                            >
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="font-semibold text-emerald-400">
                                  #{c.id} {c.subject}
                                </span>
                                <Badge variant="zinc">{c.action}</Badge>
                              </div>
                              <p className="text-xs text-zinc-300 font-mono line-clamp-2">
                                {c.claim}
                              </p>
                              {c.invalidation && (
                                <p className="text-[11px] text-amber-400/80 font-mono line-clamp-1">
                                  Invalidation: {c.invalidation}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* TAB 3: Profile */}
              {activeTab === "profile" && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 uppercase">
                        <TrendingUp className="h-3.5 w-3.5" />
                        <span>Primary Markets</span>
                      </div>
                      <p className="text-sm font-mono text-zinc-200">
                        {person.primary_markets || "Equities, Futures"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 uppercase">
                        <Award className="h-3.5 w-3.5" />
                        <span>Verified Track Records</span>
                      </div>
                      <p className="text-sm font-mono text-zinc-200">
                        {person.verified_records || "Documented empirical history"}
                      </p>
                    </div>
                  </div>

                  {/* Facts */}
                  {(person.profession || person.affiliation || person.domains || person.homepage || person.relevance) && (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-1.5 text-xs font-mono text-zinc-300">
                      {person.profession && <p><span className="text-zinc-500">Profession </span>{person.profession.replace(/_/g, " ")}</p>}
                      {person.affiliation && <p><span className="text-zinc-500">Affiliation </span>{person.affiliation}</p>}
                      {person.domains && <p><span className="text-zinc-500">Fields </span>{person.domains}</p>}
                      {person.relevance && <p><span className="text-zinc-500">Why in scope </span>{person.relevance}</p>}
                      {person.homepage && (
                        <p>
                          <span className="text-zinc-500">Website </span>
                          <a href={person.homepage} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">{person.homepage}</a>
                        </p>
                      )}
                    </div>
                  )}

                  {/* Links and social networks */}
                  {person.links && person.links.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                        Links &amp; social networks ({person.links.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {person.links.map((l) => (
                          <a
                            key={l.id}
                            href={l.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={l.evidence || ""}
                            className="group flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 hover:border-emerald-500/50 transition-colors"
                          >
                            <span className="min-w-0">
                              <span className="block truncate text-xs font-mono text-zinc-200">{l.label || l.handle || l.url.replace(/^https?:\/\//, "")}</span>
                              <span className="block truncate text-[10px] font-mono text-zinc-500">{[l.kind, l.platform].filter(Boolean).join(" · ")}</span>
                            </span>
                            <span className="flex shrink-0 items-center gap-1.5">
                              {l.match_status !== "confirmed" && <Badge variant="amber">to review</Badge>}
                              <ExternalLink className="h-3.5 w-3.5 text-zinc-500 group-hover:text-emerald-400" />
                            </span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Bio */}
                  {person.bio && (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                        Biography & Profile
                      </span>
                      <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                        {person.bio}
                      </p>
                    </div>
                  )}

                  {/* Aliases */}
                  {person.aliases && person.aliases.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                        Known Aliases & Handles ({person.aliases.length})
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {person.aliases.map((a, idx) => (
                          <span
                            key={idx}
                            className="rounded-md border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-xs font-mono text-zinc-300"
                          >
                            {a.alias} {a.platform && `(${a.platform})`}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Appearances */}
                  {person.appearances && person.appearances.length > 0 && (
                    <div className="space-y-3">
                      <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                        Cataloged Appearances ({person.appearances.length})
                      </span>
                      <div className="space-y-2">
                        {person.appearances.map((app, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-xs font-mono"
                          >
                            <div className="space-y-1">
                              <span className="text-zinc-200 font-medium">
                                {app.content_title || app.content_id}
                              </span>
                              <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                                <span>role: {app.role}</span>
                                {app.platform && <span>platform: {app.platform}</span>}
                              </div>
                            </div>
                            <span className="text-zinc-500 text-[11px]">
                              {app.content_id}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
