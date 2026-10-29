"use client";

import { Markdown } from "@/components/Markdown";
import { useEffect, useState } from "react";
import {
  BookOpen,
  Cpu,
  FileCode,
  Layers,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Badge } from "@/components/Badge";
import type { SkillItem } from "@/lib/types";

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [search, setSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("all");
  const [selectedSkill, setSelectedSkill] = useState<{
    name: string;
    markdown: string;
    platformNotes?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetch("/api/skills")
      .then((r) => r.json())
      .then((r) => {
        if (r.ok) setSkills(r.skills || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const groups = [
    "all",
    "Core Knowledge Engine",
    "Orchestration & Automation",
    "Platform Explorers (P1-P3)",
  ];

  const filtered = skills.filter((s) => {
    if (selectedGroup !== "all" && s.categoryGroup !== selectedGroup) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q)
    );
  });

  const openSkillDetail = (name: string) => {
    setDetailLoading(true);
    fetch(`/api/skills/${name}`)
      .then((r) => r.json())
      .then((r) => {
        if (r.ok && r.skill) {
          setSelectedSkill(r.skill);
        }
      })
      .finally(() => setDetailLoading(false));
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Agent Skills Catalog
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            45 standardized skills conforming to the Agent Skills Specification (agentskills.io)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="emerald">{skills.length} skills loaded</Badge>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search skills by name or capability description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-4 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-500 focus:border-emerald-500 focus:outline-hidden"
          />
        </div>

        {/* Group Selector */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {groups.map((grp) => (
            <button
              key={grp}
              onClick={() => setSelectedGroup(grp)}
              className={`rounded-md px-2.5 py-1 text-xs font-mono transition-colors cursor-pointer ${
                selectedGroup === grp
                  ? "bg-zinc-100 text-zinc-950 font-bold"
                  : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 border border-zinc-700/50"
              }`}
            >
              {grp}
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-12 text-center text-xs font-mono text-zinc-500">
          No skills match your search.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((skill) => (
            <div
              key={skill.name}
              onClick={() => openSkillDetail(skill.name)}
              className="group rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400 group-hover:text-emerald-300 transition-colors">
                    {skill.name}
                  </span>
                  <Badge
                    variant={
                      skill.type === "core"
                        ? "emerald"
                        : skill.type === "orchestration"
                        ? "purple"
                        : "blue"
                    }
                  >
                    {skill.type}
                  </Badge>
                </div>

                <p className="text-xs text-zinc-300 font-mono line-clamp-3 leading-relaxed">
                  {skill.description || "Skill instruction definition"}
                </p>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-2 border-t border-zinc-800/60">
                <span>v{skill.version}</span>
                <span className="text-emerald-400 group-hover:translate-x-0.5 transition-transform">
                  view spec →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Slideover / Modal */}
      {(selectedSkill || detailLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
          <div
            className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-zinc-800/80 px-6 py-4 bg-zinc-900/50">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-emerald-400" />
                <h2 className="text-sm font-bold font-mono text-zinc-100">
                  {selectedSkill?.name || "Loading skill..."}
                </h2>
              </div>
              <button
                onClick={() => setSelectedSkill(null)}
                className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {detailLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
                </div>
              ) : selectedSkill ? (
                <div className="space-y-6">
                  {/* SKILL.md */}
                  <div className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                      SKILL.md Specification
                    </span>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 max-h-[50vh] overflow-y-auto">
                      <Markdown>{selectedSkill.markdown}</Markdown>
                    </div>
                  </div>

                  {/* Platform Notes if available */}
                  {selectedSkill.platformNotes && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                        Platform Notes (references/platform_notes.md)
                      </span>
                      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 max-h-[30vh] overflow-y-auto">
                        <Markdown>{selectedSkill.platformNotes}</Markdown>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
