import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import type {
  AgentRun,
  ContentItem,
  ContentSegmentView,
  DedupDecision,
  DoctorReport,
  EmbedStatus,
  Envelope,
  ExploreQueueItem,
  KnowledgeCard,
  KnowledgeGap,
  Person,
  SearchResponse,
  PersonSkill,
  SkillItem,
  Source,
  StatsData,
  VocabTerm,
} from "./types";

const execFileAsync = promisify(execFile);

/**
 * Find the repository root (directory containing pyproject.toml and data/)
 */
export function getRepoRoot(): string {
  let curr = process.cwd();
  for (let i = 0; i < 5; i++) {
    if (fs.existsSync(path.join(curr, "pyproject.toml"))) {
      return curr;
    }
    const parent = path.dirname(curr);
    if (parent === curr) break;
    curr = parent;
  }
  return process.cwd();
}

const SERVE_URL = process.env.FINSOCNET_SERVE_URL || "http://127.0.0.1:8787";

/** Parse what the CLI printed: a JSON envelope, or plain text wrapped in a synthetic one. */
function toEnvelope<T>(args: string[], stdout: string, stderr = ""): Envelope<T> {
  const trimmed = stdout.trim();
  if (!trimmed) {
    throw new Error(`Empty response from CLI. stderr: ${stderr}`);
  }
  try {
    return JSON.parse(trimmed) as Envelope<T>;
  } catch {
    return { ok: true, command: args.join(" "), data: trimmed as unknown as T };
  }
}

// `finsocnet serve` keeps Python and the embedding model warm (about 50 ms per call instead of 1+ s with `uv run`).
let serveDown = 0;
async function viaServe(args: string[], timeoutMs: number): Promise<string | null> {
  if (Date.now() < serveDown) return null;
  try {
    const res = await fetch(`${SERVE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`serve ${res.status}`);
    const body = (await res.json()) as { stdout: string };
    return body.stdout;
  } catch {
    serveDown = Date.now() + 15000; // fall back to spawning the CLI for a while
    return null;
  }
}

// Read results are cached while the database file is unchanged (key: args + mtime of the db and its WAL), so repeated
// page loads cost nothing and a write by an agent is visible on the next request.
const cache = new Map<string, { at: number; value: Envelope<unknown> }>();
const CACHE_MAX = 300;
const READ_ONLY = /^(stats|doctor|audit|taxonomy|person classes|person coverage|query|schema|card (list|get|search)|person (list|get|cards|link list)|skill get|source (list|get)|content (list|get|view)|vocab (list|lookup)|run list|decision list|gap list|queue list|embed status|search)\b/;

function dbStamp(): string {
  const base = process.env.KNOWLEDGE_DB_PATH || path.join(getRepoRoot(), "data", "knowledge.db");
  return ["", "-wal"].map((suffix) => {
    try {
      return String(fs.statSync(base + suffix).mtimeMs);
    } catch {
      return "0";
    }
  }).join(":");
}

/**
 * Execute a finsocnet CLI command and parse the JSON envelope
 */
export async function runCliCommand<T = unknown>(
  args: string[],
  timeoutMs: number = 30000
): Promise<Envelope<T>> {
  const repoRoot = getRepoRoot();
  const cacheable = args[0] === "kb" && READ_ONLY.test(args.slice(1).join(" "));
  const key = cacheable ? `${dbStamp()}|${args.join("\u0000")}` : "";
  if (cacheable) {
    const hit = cache.get(key);
    if (hit) return hit.value as Envelope<T>;
  }
  try {
    let env: Envelope<T>;
    const warm = await viaServe(args, timeoutMs);
    if (warm !== null) {
      env = toEnvelope<T>(args, warm);
    } else {
      const { stdout, stderr } = await execFileAsync("uv", ["run", "finsocnet", ...args], {
        cwd: repoRoot,
        timeout: timeoutMs,
        maxBuffer: 32 * 1024 * 1024,
        env: { ...process.env, FINSOCNET_HOME: repoRoot, PYTHONUNBUFFERED: "1" },
      });
      env = toEnvelope<T>(args, stdout, stderr);
    }
    if (cacheable && env.ok) {
      if (cache.size >= CACHE_MAX) cache.delete(cache.keys().next().value as string);
      cache.set(key, { at: Date.now(), value: env });
    }
    return env;
  } catch (error: unknown) {
    const err = error as { stdout?: string; stderr?: string; message?: string };
    if (err.stdout) {
      try {
        return JSON.parse(err.stdout.trim()) as Envelope<T>;
      } catch {
        // Fall through
      }
    }
    return {
      ok: false,
      command: args.join(" "),
      data: null as unknown as T,
      error: {
        code: "EXEC_ERROR",
        message: err.stderr || err.message || "Failed to execute CLI command",
      },
    };
  }
}

/**
 * Run a finsocnet kb subcommand
 */
export async function runKbCommand<T = unknown>(
  args: string[],
  timeoutMs: number = 30000
): Promise<Envelope<T>> {
  return runCliCommand<T>(["kb", ...args], timeoutMs);
}

// -------------------------------------------------------------
// High-Level Data Accessors
// -------------------------------------------------------------

export async function getStats(): Promise<StatsData> {
  const res = await runKbCommand<StatsData>(["stats"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to load stats");
  }
  return res.data;
}

export async function getDoctor(): Promise<DoctorReport> {
  const res = await runKbCommand<DoctorReport>(["doctor"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to run doctor check");
  }
  return res.data;
}

export async function getCards(params?: {
  limit?: number;
  person?: string;
  category?: string;
  status?: string;
  search?: string;
  newest?: boolean;
  kind?: string;
  domain?: string;
  evidence?: string;
}): Promise<KnowledgeCard[]> {
  if (params?.search && params.search.trim().length > 0) {
    const res = await runKbCommand<{ results: Array<{ card: KnowledgeCard }> }>([
      "card",
      "search",
      "--text",
      params.search.trim(),
      "--limit",
      String(params.limit || 50),
    ]);
    if (res.ok && res.data?.results) {
      return res.data.results.map((r) => r.card);
    }
  }

  const args = ["card", "list", "--limit", String(params?.limit || 100)];
  if (params?.person) args.push("--person", params.person);
  if (params?.category) args.push("--category", params.category);
  if (params?.status) args.push("--status", params.status);
  if (params?.newest) args.push("--newest");
  if (params?.kind) args.push("--kind", params.kind);
  if (params?.domain) args.push("--domain", params.domain);
  if (params?.evidence) args.push("--evidence", params.evidence);

  const res = await runKbCommand<{ cards: KnowledgeCard[] }>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list cards");
  }
  return res.data.cards || [];
}

export async function getCard(id: number | string): Promise<KnowledgeCard> {
  const res = await runKbCommand<KnowledgeCard>([
    "card",
    "get",
    String(id),
    "--citations",
    "--links",
    "--history",
  ]);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to get card ${id}`);
  }
  return res.data;
}

export async function getPersons(): Promise<Person[]> {
  const res = await runKbCommand<{ persons: Person[] }>(["person", "list", "--limit", "1000"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list persons");
  }
  return res.data.persons || [];
}

/** The static classifications with counts (`kb taxonomy`); keys like `cards.category`, `content.platform`, `skills.group`. */
export async function getTaxonomy(entity?: string): Promise<Record<string, unknown>> {
  const res = await runKbCommand<Record<string, unknown>>(["taxonomy", ...(entity ? ["--entity", entity] : [])]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to load taxonomy");
  }
  return res.data;
}

export interface PersonClass {
  id: string;
  group: string;
  label: string;
  hint: string;
  count: number;
}

/** The static classification of people (core/classes.py), with counts; `other` is the catch-all. */
export async function getPersonClasses(): Promise<PersonClass[]> {
  const res = await runKbCommand<{ classes: PersonClass[] }>(["person", "classes"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to load person classes");
  }
  return res.data.classes || [];
}

export async function getPerson(id: string): Promise<Person> {
  const res = await runKbCommand<Person>(["person", "get", id]);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to get person ${id}`);
  }
  return res.data;
}

export async function getPersonCards(
  id: string,
  category?: string
): Promise<{ person_id: string; total: number; categories: Record<string, KnowledgeCard[]> }> {
  const args = ["person", "cards", id];
  if (category) args.push("--category", category);

  const res = await runKbCommand<{
    person_id: string;
    total: number;
    categories: Record<string, KnowledgeCard[]>;
  }>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to get cards for person ${id}`);
  }
  return res.data;
}

export async function getPersonRulebook(id: string): Promise<{
  markdown: string;
  skills: PersonSkill[];
}> {
  // First try structured skills
  const res = await runKbCommand<{ skills: PersonSkill[] }>(["skill", "get", id]);
  const skills = res.ok && res.data?.skills ? res.data.skills : [];

  // Get rendered strategy markdown
  const strategyRes = await runCliCommand<string>(["strategy", id]);
  const markdown = strategyRes.data || "";

  return { markdown, skills };
}

export async function getSources(params?: {
  platform?: string;
  person?: string;
  status?: string;
  kind?: string;
  medium?: string;
}): Promise<Source[]> {
  const args = ["source", "list", "--limit", "1000"];
  if (params?.platform) args.push("--platform", params.platform);
  if (params?.person) args.push("--person", params.person);
  if (params?.status) args.push("--status", params.status);
  if (params?.kind) args.push("--kind", params.kind);
  if (params?.medium) args.push("--medium", params.medium);

  const res = await runKbCommand<{ sources: Source[] }>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list sources");
  }
  return res.data.sources || [];
}

export async function getSource(id: string): Promise<Source> {
  const res = await runKbCommand<Source>(["source", "get", id]);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to get source ${id}`);
  }
  return res.data;
}

export async function getContentList(params?: {
  limit?: number;
  platform?: string;
  status?: string;
  person?: string;
  source?: string;
  type?: string;
  medium?: string;
}): Promise<ContentItem[]> {
  const args = ["content", "list", "--limit", String(params?.limit || 50)];
  if (params?.platform) args.push("--platform", params.platform);
  if (params?.status) args.push("--status", params.status);
  if (params?.person) args.push("--person", params.person);
  if (params?.source) args.push("--source", params.source);
  if (params?.type) args.push("--type", params.type);
  if (params?.medium) args.push("--medium", params.medium);

  const res = await runKbCommand<{ contents: ContentItem[] }>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list content");
  }
  return res.data.contents || [];
}

export async function getContent(id: string): Promise<ContentItem> {
  const res = await runKbCommand<ContentItem>(["content", "get", id]);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to get content ${id}`);
  }
  return res.data;
}

export async function getContentView(
  id: string,
  fromSeq: number = 0,
  toSeq?: number
): Promise<ContentSegmentView> {
  const args = ["content", "view", id, "--from-seq", String(fromSeq)];
  if (toSeq !== undefined) {
    args.push("--to-seq", String(toSeq));
  }
  const res = await runKbCommand<ContentSegmentView>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || `Failed to view content ${id}`);
  }
  return res.data;
}

export async function getSkills(): Promise<SkillItem[]> {
  const repoRoot = getRepoRoot();
  const skillsDir = path.join(repoRoot, ".agents", "skills");
  const items: SkillItem[] = [];
  // Groups are the static classification of skills (core/taxonomy.py), not a list kept in the UI.
  const tax = (await getTaxonomy("skills").catch(() => ({}))) as { _skill_group?: Record<string, string> };
  const groupOf = tax._skill_group || {};

  if (fs.existsSync(skillsDir)) {
    const entries = fs.readdirSync(skillsDir, { withFileTypes: true });
    for (const ent of entries) {
      if (!ent.isDirectory()) continue;
      const skillName = ent.name;
      const skillMdPath = path.join(skillsDir, skillName, "SKILL.md");
      let description = "";
      let version = "2.0.0";

      if (fs.existsSync(skillMdPath)) {
        try {
          const content = fs.readFileSync(skillMdPath, "utf-8");
          const descMatch = content.match(/description:\s*([^\n]+)/);
          if (descMatch) description = descMatch[1].trim();

          const verMatch = content.match(/version:\s*"?([^"\n]+)"?/);
          if (verMatch) version = verMatch[1].trim();
        } catch {
          // ignore
        }
      }

      const categoryGroup = groupOf[skillName] || "Other";
      const type: SkillItem["type"] = categoryGroup === "Knowledge core" || categoryGroup === "People" ? "core" : categoryGroup === "Loop" || categoryGroup === "Access" ? "orchestration" : "platform";

      items.push({
        name: skillName,
        type,
        version,
        description,
        path: path.relative(repoRoot, skillMdPath),
        categoryGroup,
      });
    }
  }

  // Sort by categoryGroup then name
  return items.sort((a, b) => {
    if (a.categoryGroup !== b.categoryGroup) {
      return (a.categoryGroup || "").localeCompare(b.categoryGroup || "");
    }
    return a.name.localeCompare(b.name);
  });
}

export async function getSkillDetail(name: string): Promise<{
  name: string;
  markdown: string;
  platformNotes?: string;
}> {
  const repoRoot = getRepoRoot();
  const skillDir = path.join(repoRoot, ".agents", "skills", name);
  const skillMdPath = path.join(skillDir, "SKILL.md");
  const notesPath = path.join(skillDir, "references", "platform_notes.md");

  let markdown = "";
  let platformNotes: string | undefined;

  if (fs.existsSync(skillMdPath)) {
    markdown = fs.readFileSync(skillMdPath, "utf-8");
  }
  if (fs.existsSync(notesPath)) {
    platformNotes = fs.readFileSync(notesPath, "utf-8");
  }

  return { name, markdown, platformNotes };
}

export async function getVocab(facet?: string): Promise<VocabTerm[]> {
  const args = ["vocab", "list"];
  if (facet) args.push("--facet", facet);

  const res = await runKbCommand<{ terms: VocabTerm[] }>(args);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list vocabulary");
  }
  return res.data.terms || [];
}

export async function lookupVocab(phrase: string): Promise<VocabTerm[]> {
  const res = await runKbCommand<VocabTerm[]>([
    "vocab",
    "lookup",
    phrase,
    "--limit",
    "15",
  ]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to lookup vocabulary");
  }
  return res.data || [];
}

export async function getRuns(limit: number = 50): Promise<AgentRun[]> {
  const res = await runKbCommand<{ runs: AgentRun[] }>([
    "run",
    "list",
    "--limit",
    String(limit),
  ]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list runs");
  }
  return res.data.runs || [];
}

export async function getDecisions(limit: number = 50): Promise<DedupDecision[]> {
  const res = await runKbCommand<{ decisions: DedupDecision[] }>([
    "decision",
    "list",
    "--limit",
    String(limit),
  ]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list decisions");
  }
  return res.data.decisions || [];
}

export async function getGaps(): Promise<KnowledgeGap[]> {
  const res = await runKbCommand<{ gaps: KnowledgeGap[] }>(["gap", "list"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list gaps");
  }
  return res.data.gaps || [];
}

export async function getQueue(): Promise<ExploreQueueItem[]> {
  const res = await runKbCommand<{ items: ExploreQueueItem[] }>(["queue", "list"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list queue");
  }
  return res.data.items || [];
}

// -------------------------------------------------------------
// Unified search (cards, content text, persons, rulebooks)
// -------------------------------------------------------------

export interface SearchParams {
  q: string;
  types?: string[];
  mode?: string;
  limit?: number;
  filters?: Record<string, string | string[] | undefined>;
}

const SEARCH_FLAGS: Record<string, string> = {
  kind: "--kind",
  category: "--category",
  domain: "--domain",
  horizon: "--horizon",
  evidence_min: "--evidence-min",
  person: "--person",
  instrument: "--instrument",
  min_persons: "--min-persons",
  platform: "--platform",
  content_type: "--content-type",
  since: "--since",
  language: "--language",
  status: "--status",
};

export async function searchAll(params: SearchParams): Promise<{ data: SearchResponse; warnings: string[] }> {
  const args = ["search", params.q, "--limit", String(params.limit ?? 40), "--mode", params.mode ?? "auto"];
  if (params.types && params.types.length > 0) args.push("--types", params.types.join(","));
  for (const [key, flag] of Object.entries(SEARCH_FLAGS)) {
    const v = params.filters?.[key];
    if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    for (const one of Array.isArray(v) ? v : [v]) args.push(flag, one);
  }
  // execFile receives an argument vector, never a shell string: the query cannot inject anything.
  // The first semantic query loads the embedding model, so allow more time than the default.
  const res = await runKbCommand<SearchResponse>(args, 90000);
  if (!res.ok) {
    throw new Error(res.error?.message || "Search failed");
  }
  return { data: res.data, warnings: res.warnings || [] };
}

export async function getEmbedStatus(): Promise<EmbedStatus> {
  const res = await runKbCommand<EmbedStatus>(["embed", "status"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to read embedding status");
  }
  return res.data;
}
