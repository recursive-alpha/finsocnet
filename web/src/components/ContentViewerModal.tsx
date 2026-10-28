"use client";

import { useEffect, useState } from "react";
import {
  Calendar,
  Clock,
  Eye,
  ExternalLink,
  FileText,
  User,
  X,
} from "lucide-react";
import { Badge, PlatformBadge } from "./Badge";
import type { ContentItem, ContentSegmentView } from "@/lib/types";

interface ContentViewerModalProps {
  contentId: string | null;
  onClose: () => void;
}

export function ContentViewerModal({ contentId, onClose }: ContentViewerModalProps) {
  const [content, setContent] = useState<ContentItem | null>(null);
  const [view, setView] = useState<ContentSegmentView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!contentId) {
      setContent(null);
      setView(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetch(`/api/content/${contentId}`)
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setContent(res.content);
          setView(res.view);
        } else {
          setError(res.error || "Failed to load content");
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [contentId]);

  if (!contentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
      <div
        className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 px-6 py-4 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <PlatformBadge platform={content?.platform || "media"} />
            <div>
              <h2 className="text-sm font-bold text-zinc-100 line-clamp-1">
                {content?.title || contentId}
              </h2>
              <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
                <span>{contentId}</span>
                {content?.content_type && <span>• {content.content_type}</span>}
              </div>
            </div>
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

          {content && !loading && (
            <>
              {/* Metadata Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500 uppercase">
                    <User className="h-3 w-3" />
                    <span>Author</span>
                  </div>
                  <p className="text-xs font-mono text-zinc-200 truncate">
                    {content.author_handle || content.person_id || "Unknown"}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500 uppercase">
                    <Clock className="h-3 w-3" />
                    <span>Duration</span>
                  </div>
                  <p className="text-xs font-mono text-zinc-200">
                    {content.duration_sec
                      ? `${Math.floor(content.duration_sec / 60)}m ${content.duration_sec % 60}s`
                      : "n/a"}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500 uppercase">
                    <Calendar className="h-3 w-3" />
                    <span>Published</span>
                  </div>
                  <p className="text-xs font-mono text-zinc-200">
                    {content.published_at
                      ? new Date(content.published_at).toLocaleDateString()
                      : "n/a"}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500 uppercase">
                    <FileText className="h-3 w-3" />
                    <span>Segments</span>
                  </div>
                  <p className="text-xs font-mono text-zinc-200">
                    {content.segments || 0} segments
                  </p>
                </div>
              </div>

              {/* Description */}
              {content.description && (
                <div className="space-y-1.5 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
                  <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                    Description / Abstract
                  </span>
                  <p className="text-xs text-zinc-300 font-mono line-clamp-4 leading-relaxed">
                    {content.description}
                  </p>
                </div>
              )}

              {/* URL */}
              {content.url && (
                <a
                  href={content.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-mono text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Open original URL ({content.url})</span>
                </a>
              )}

              {/* Interactive Transcript / Segments View */}
              <div className="space-y-3 pt-2 border-t border-zinc-800/80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                    Transcript & Content Segments Viewer ({view?.segments || 0} segments)
                  </span>
                  <span className="text-[11px] font-mono text-zinc-500">
                    Rendered via kb content view
                  </span>
                </div>

                {view?.text ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 max-h-[50vh] overflow-y-auto font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                    {view.text}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center text-xs font-mono text-zinc-500">
                    {content.process_status === "metadata_only"
                      ? "This content item was ingested as metadata-only (no full transcript or text segments captured yet)."
                      : "No text segments extracted for this item."}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
