"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  GitBranch,
  Quote,
  Tag,
  X,
} from "lucide-react";
import { Badge, CategoryBadge } from "./Badge";
import type { CardCitation, CardLink, KnowledgeCard } from "@/lib/types";

interface CardModalProps {
  cardId: number | null;
  onClose: () => void;
  onSelectCard?: (id: number) => void;
}

export function CardModal({ cardId, onClose, onSelectCard }: CardModalProps) {
  const [card, setCard] = useState<KnowledgeCard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cardId) {
      setCard(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetch(`/api/cards/${cardId}`)
      .then((res) => res.json())
      .then((res) => {
        if (res.ok && res.card) {
          setCard(res.card);
        } else {
          setError(res.error || "Failed to load card details");
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [cardId]);

  if (!cardId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 px-6 py-4 bg-zinc-900/50">
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-xs text-zinc-400 font-semibold px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700">
              CARD #{cardId}
            </span>
            {card && (
              <>
                <CategoryBadge category={card.category} />
                <Badge variant={card.status === "active" ? "emerald" : "zinc"}>
                  {card.status}
                </Badge>
                <span className="text-xs text-zinc-500 font-mono">
                  v{card.card_version}
                </span>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
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

          {card && !loading && (
            <>
              {/* Subject & Claim */}
              <div className="space-y-3">
                <div className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                  Subject & Formal Claim
                </div>
                <h2 className="text-lg font-bold text-zinc-100 capitalize">
                  {card.subject}
                </h2>
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 font-mono text-sm leading-relaxed text-zinc-200">
                  <div className="text-emerald-400 font-semibold text-xs mb-1">
                    FORMAL CLAIM (CLAIM GRAMMAR):
                  </div>
                  {card.claim}
                </div>
              </div>

              {/* Action, Horizon, Invalidation Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3.5 space-y-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                    Action
                  </span>
                  <p className="font-mono text-sm font-semibold text-zinc-200">
                    {card.action || "NONE"}
                  </p>
                </div>
                <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3.5 space-y-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                    Holding Horizon
                  </span>
                  <p className="font-mono text-sm text-zinc-200">
                    {card.horizon || "unspecified"}
                  </p>
                </div>
                <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3.5 space-y-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                    Evidence Level
                  </span>
                  <p className="font-mono text-sm text-zinc-200">
                    {card.evidence_level || "claimed"}
                  </p>
                </div>
              </div>

              {/* Conditions Checklist */}
              {card.conditions && card.conditions.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-500">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Setup & Execution Conditions ({card.conditions.length})</span>
                  </div>
                  <ul className="space-y-1.5">
                    {card.conditions.map((cond, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2.5 rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-2.5 text-xs text-zinc-300 font-mono"
                      >
                        <span className="text-emerald-500 mt-0.5">•</span>
                        <span>{cond}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Invalidation Risk */}
              {card.invalidation && (
                <div className="rounded-xl border border-amber-900/40 bg-amber-950/15 p-4 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-amber-400 uppercase tracking-wide">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Invalidation Risk</span>
                  </div>
                  <p className="text-xs text-amber-200/90 leading-relaxed font-mono">
                    {card.invalidation}
                  </p>
                </div>
              )}

              {/* Terms & Entities */}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-500">
                  <Tag className="h-3.5 w-3.5" />
                  <span>Controlled Vocabulary & Instruments</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {card.terms?.map((term) => (
                    <span
                      key={term}
                      className="rounded bg-zinc-800/80 px-2 py-0.5 text-xs font-mono text-emerald-300 border border-zinc-700/60"
                    >
                      #{term}
                    </span>
                  ))}
                  {card.instruments?.map((inst) => (
                    <span
                      key={inst}
                      className="rounded bg-blue-950/60 px-2 py-0.5 text-xs font-mono text-blue-300 border border-blue-800/60"
                    >
                      {inst}
                    </span>
                  ))}
                  {card.regime?.map((r) => (
                    <span
                      key={r}
                      className="rounded bg-purple-950/60 px-2 py-0.5 text-xs font-mono text-purple-300 border border-purple-800/60"
                    >
                      regime: {r}
                    </span>
                  ))}
                </div>
              </div>

              {/* Citations & Verbatim Quotes */}
              {card.citations && card.citations.length > 0 && (
                <div className="space-y-3 pt-2 border-t border-zinc-800/60">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-400">
                      <Quote className="h-3.5 w-3.5 text-zinc-400" />
                      <span>Verbatim Ground-Truth Citations ({card.citations.length})</span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {card.citations.map((cite: CardCitation) => (
                      <div
                        key={cite.id}
                        className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2.5"
                      >
                        <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-200 font-semibold">
                              {cite.person_id ? `@${cite.person_id}` : cite.speaker_role}
                            </span>
                            <span className="text-zinc-600">|</span>
                            <span className="text-emerald-400">stance: {cite.stance}</span>
                          </div>
                          <span className="text-zinc-500">
                            content: {cite.content_id}
                          </span>
                        </div>
                        <blockquote className="border-l-2 border-emerald-500/70 pl-3 text-xs italic leading-relaxed text-zinc-200">
                          &ldquo;{cite.quote}&rdquo;
                        </blockquote>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Links to Other Cards */}
              {card.links && card.links.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-zinc-800/60">
                  <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-400">
                    <GitBranch className="h-3.5 w-3.5 text-zinc-400" />
                    <span>Card Relationships & Graph Links ({card.links.length})</span>
                  </div>
                  <div className="space-y-2">
                    {card.links.map((link: CardLink, idx) => (
                      <div
                        key={idx}
                        onClick={() => onSelectCard?.(link.to_card_id)}
                        className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 hover:border-zinc-700 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-2 text-xs font-mono">
                          <Badge
                            variant={
                              link.relation === "contradicts"
                                ? "rose"
                                : link.relation === "refines"
                                ? "blue"
                                : "emerald"
                            }
                          >
                            {link.relation}
                          </Badge>
                          <span className="text-zinc-300">Target Card #{link.to_card_id}</span>
                          {link.reason && (
                            <span className="text-zinc-500 line-clamp-1">— {link.reason}</span>
                          )}
                        </div>
                        <ArrowRight className="h-4 w-4 text-zinc-500" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata Footer */}
              <div className="pt-3 border-t border-zinc-800/60 flex flex-wrap items-center justify-between text-[11px] font-mono text-zinc-500 gap-2">
                <span>Produced by: {card.produced_by}</span>
                <span>Transformer: {card.transformer_version}</span>
                <span>Run ID: #{card.run_id}</span>
                <span>Updated: {new Date(card.updated_at).toLocaleString()}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
