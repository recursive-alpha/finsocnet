"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  Brain,
  CheckCircle,
  Database,
  GitCommit,
  GitPullRequest,
  ListFilter,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/Badge";
import type {
  AgentRun,
  DedupDecision,
  DoctorReport,
  ExploreQueueItem,
  KnowledgeGap,
} from "@/lib/types";

export default function OperationsPage() {
  const [activeTab, setActiveTab] = useState<
    "runs" | "decisions" | "doctor" | "gaps" | "queue"
  >("runs");
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [decisions, setDecisions] = useState<DedupDecision[]>([]);
  const [gaps, setGaps] = useState<KnowledgeGap[]>([]);
  const [queue, setQueue] = useState<ExploreQueueItem[]>([]);
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/operations")
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) {
          setRuns(r.runs || []);
          setDecisions(r.decisions || []);
          setGaps(r.gaps || []);
          setQueue(r.queue || []);
          setDoctor(r.doctor || null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Operations & Diagnostics
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Agent execution runs, deduplication audit log, knowledge gaps, and database health
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800 bg-zinc-900/40 rounded-xl p-1 gap-1">
        <button
          onClick={() => setActiveTab("runs")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-mono font-medium transition-colors cursor-pointer ${
            activeTab === "runs"
              ? "bg-zinc-800 text-emerald-400"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Zap className="h-3.5 w-3.5" />
          <span>Agent Runs ({runs.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("decisions")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-mono font-medium transition-colors cursor-pointer ${
            activeTab === "decisions"
              ? "bg-zinc-800 text-emerald-400"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <GitCommit className="h-3.5 w-3.5" />
          <span>Dedup Decisions ({decisions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("doctor")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-mono font-medium transition-colors cursor-pointer ${
            activeTab === "doctor"
              ? "bg-zinc-800 text-emerald-400"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>Database Doctor</span>
        </button>

        <button
          onClick={() => setActiveTab("gaps")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-mono font-medium transition-colors cursor-pointer ${
            activeTab === "gaps"
              ? "bg-zinc-800 text-emerald-400"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <AlertCircle className="h-3.5 w-3.5" />
          <span>Knowledge Gaps ({gaps.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("queue")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-mono font-medium transition-colors cursor-pointer ${
            activeTab === "queue"
              ? "bg-zinc-800 text-emerald-400"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <ListFilter className="h-3.5 w-3.5" />
          <span>Explore Queue ({queue.length})</span>
        </button>
      </div>

      {/* Tab Panels */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : (
        <>
          {/* TAB 1: Agent Runs */}
          {activeTab === "runs" && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="border-b border-zinc-800 bg-zinc-900/80 text-[11px] uppercase tracking-wider text-zinc-400">
                    <tr>
                      <th className="py-3 px-4">Run ID</th>
                      <th className="py-3 px-4">Skill</th>
                      <th className="py-3 px-4">Harness & Model</th>
                      <th className="py-3 px-4">Goal / Description</th>
                      <th className="py-3 px-4">Outcome</th>
                      <th className="py-3 px-4">Elapsed</th>
                      <th className="py-3 px-4 text-right">Started</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {runs.map((r) => (
                      <tr key={r.id} className="hover:bg-zinc-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-bold text-emerald-400 whitespace-nowrap">
                          #{r.id}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-zinc-200 whitespace-nowrap">
                          {r.skill}
                        </td>
                        <td className="py-3.5 px-4 text-zinc-400 whitespace-nowrap">
                          {r.harness} {r.model && `(${r.model})`}
                        </td>
                        <td className="py-3.5 px-4 max-w-sm text-zinc-300">
                          <p className="line-clamp-1">{r.goal}</p>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <Badge
                            variant={
                              r.outcome === "success" || r.outcome === "completed"
                                ? "emerald"
                                : r.outcome === "failed"
                                ? "rose"
                                : "zinc"
                            }
                          >
                            {r.outcome || "in_progress"}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-400 whitespace-nowrap">
                          {r.elapsed_ms ? `${(r.elapsed_ms / 1000).toFixed(1)}s` : "—"}
                        </td>
                        <td className="py-3.5 px-4 text-right text-zinc-500 whitespace-nowrap">
                          {new Date(r.started_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: Dedup Decisions */}
          {activeTab === "decisions" && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="border-b border-zinc-800 bg-zinc-900/80 text-[11px] uppercase tracking-wider text-zinc-400">
                    <tr>
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Run</th>
                      <th className="py-3 px-4">Decision</th>
                      <th className="py-3 px-4">Target Card</th>
                      <th className="py-3 px-4">Agent Rationale</th>
                      <th className="py-3 px-4 text-right">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60">
                    {decisions.map((d) => (
                      <tr key={d.id} className="hover:bg-zinc-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-bold text-zinc-400 whitespace-nowrap">
                          #{d.id}
                        </td>
                        <td className="py-3.5 px-4 text-emerald-400 whitespace-nowrap">
                          #{d.run_id}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <Badge
                            variant={
                              d.decision === "same"
                                ? "emerald"
                                : d.decision === "refines"
                                ? "blue"
                                : d.decision === "contradicts"
                                ? "rose"
                                : "amber"
                            }
                          >
                            {d.decision}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-300 whitespace-nowrap">
                          {d.target_card_id ? `Card #${d.target_card_id}` : "— (new)"}
                        </td>
                        <td className="py-3.5 px-4 max-w-md text-zinc-300">
                          <p className="line-clamp-2 leading-relaxed">
                            {d.rationale}
                          </p>
                        </td>
                        <td className="py-3.5 px-4 text-right text-zinc-500 whitespace-nowrap">
                          {new Date(d.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: Doctor */}
          {activeTab === "doctor" && (
            <div className="space-y-6">
              {doctor ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Integrity & Versions */}
                  <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4 font-mono text-xs">
                    <h3 className="font-bold text-sm text-zinc-100 uppercase tracking-wide">
                      Core Database Health
                    </h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-950/60">
                        <span className="text-zinc-400">PRAGMA Integrity Check</span>
                        <Badge variant={doctor.integrity === "ok" ? "emerald" : "rose"}>
                          {doctor.integrity}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-950/60">
                        <span className="text-zinc-400">SQLite Engine Version</span>
                        <span className="text-zinc-200">{doctor.sqlite_version}</span>
                      </div>

                      <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-950/60">
                        <span className="text-zinc-400">Current Migration</span>
                        <span className="text-emerald-400">
                          {doctor.schema?.current_migration || "003_v2_schema"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-950/60">
                        <span className="text-zinc-400">Applied Migrations Count</span>
                        <span className="text-zinc-200">
                          {doctor.schema?.applied_count || 3}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* FTS5 Tables */}
                  <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4 font-mono text-xs">
                    <h3 className="font-bold text-sm text-zinc-100 uppercase tracking-wide">
                      FTS5 Full-Text Index Integrity
                    </h3>
                    <div className="space-y-2">
                      {doctor.fts_integrity &&
                        Object.entries(doctor.fts_integrity).map(([tbl, res]) => (
                          <div
                            key={tbl}
                            className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-950/60"
                          >
                            <span className="text-zinc-300 font-semibold">{tbl}</span>
                            <Badge variant={res === "ok" ? "emerald" : "rose"}>
                              {res}
                            </Badge>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-zinc-500 font-mono text-xs">
                  Doctor report unavailable.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Gaps */}
          {activeTab === "gaps" && (
            <div className="space-y-4">
              {gaps.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
                  No open knowledge gaps recorded.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {gaps.map((g) => (
                    <div
                      key={g.id}
                      className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-2 font-mono text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-zinc-200">{g.query}</span>
                        <Badge variant="amber">{g.verdict}</Badge>
                      </div>
                      <div className="flex items-center justify-between text-zinc-500 text-[11px]">
                        <span>Asked {g.asked_count} times</span>
                        <span>Status: {g.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: Queue */}
          {activeTab === "queue" && (
            <div className="space-y-4">
              {queue.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
                  Exploration queue is empty. Use finsocnet explore add &lt;target&gt; to enqueue sources.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {queue.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-2 font-mono text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-zinc-200">{item.target}</span>
                        <Badge variant="blue">{item.status}</Badge>
                      </div>
                      <div className="flex items-center justify-between text-zinc-500 text-[11px]">
                        <span>kind: {item.target_kind}</span>
                        <span>priority: {item.priority}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
