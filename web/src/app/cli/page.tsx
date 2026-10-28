"use client";

import { useState } from "react";
import {
  Clock,
  Code2,
  Copy,
  CornerDownLeft,
  Play,
  Terminal,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/Badge";

const PRESETS = [
  "kb stats",
  "kb doctor",
  "kb card search --text VCP --limit 3",
  "kb person list",
  "kb person get mark-minervini",
  "kb content list --platform youtube --limit 3",
  "kb vocab lookup EMA",
  "skills",
];

export default function CliPage() {
  const [command, setCommand] = useState("kb stats");
  const [output, setOutput] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ elapsed_ms?: number; api_elapsed_ms?: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async (cmd = command) => {
    if (!cmd.trim()) return;
    setLoading(true);
    setError(null);
    setOutput(null);
    setMeta(null);

    try {
      const res = await fetch("/api/cli", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await res.json();
      if (data.ok !== undefined) {
        setOutput(JSON.stringify(data, null, 2));
        setMeta(data.meta || null);
      } else {
        setError(data.error || "Failed to execute command");
      }
    } catch (err: unknown) {
      const e = err as Error;
      setError(e.message || "Failed to contact CLI API");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (output) {
      navigator.clipboard.writeText(output);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Interactive CLI Console
            </h1>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Execute any finsocnet kb command directly against the SQLite knowledge engine
          </p>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="space-y-2">
        <span className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider">
          Quick Command Presets:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((preset) => (
            <button
              key={preset}
              onClick={() => {
                setCommand(preset);
                handleRun(preset);
              }}
              className="rounded-md border border-zinc-800 bg-zinc-900/60 px-2.5 py-1 text-xs font-mono text-zinc-300 hover:border-emerald-500/50 hover:text-emerald-400 transition-colors cursor-pointer"
            >
              finsocnet {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Command Input Box */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4 space-y-3 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRun();
          }}
          className="flex items-center gap-3"
        >
          <span className="font-mono text-sm font-bold text-emerald-400 select-none">
            finsocnet&gt;
          </span>
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="e.g. kb card get 6 --citations"
            className="flex-1 bg-transparent font-mono text-xs sm:text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-hidden"
          />
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-mono font-medium text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {loading ? (
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Run</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Output Console */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-2xl space-y-0">
        <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-2.5 text-xs font-mono">
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-emerald-400" />
            <span className="text-zinc-300 font-semibold">JSON Output</span>
            {meta && (
              <span className="text-zinc-500 text-[11px] flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{meta.elapsed_ms || meta.api_elapsed_ms || 0}ms</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {output && (
              <>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy</span>
                </button>
                <button
                  onClick={() => setOutput(null)}
                  className="flex items-center gap-1 text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer ml-2"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Clear</span>
                </button>
              </>
            )}
          </div>
        </div>

        <div className="p-4 max-h-[65vh] overflow-y-auto font-mono text-xs">
          {loading ? (
            <div className="flex h-48 items-center justify-center text-zinc-500 gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
              <span>Executing finsocnet {command}...</span>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-4 text-rose-400 space-y-1">
              <span className="font-bold">Execution Error:</span>
              <p>{error}</p>
            </div>
          ) : output ? (
            <pre className="text-zinc-300 whitespace-pre-wrap leading-relaxed">
              {output}
            </pre>
          ) : (
            <div className="py-16 text-center text-zinc-600">
              Run a command or click a preset above to inspect live CLI output.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
