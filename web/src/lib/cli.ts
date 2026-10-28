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
  Envelope,
  ExploreQueueItem,
  KnowledgeCard,
  KnowledgeGap,
  Person,
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

/**
 * Execute a finsocnet CLI command and parse the JSON envelope
 */
export async function runCliCommand<T = unknown>(
  args: string[],
  timeoutMs: number = 30000
): Promise<Envelope<T>> {
  const repoRoot = getRepoRoot();
  try {
    const { stdout, stderr } = await execFileAsync(
      "uv",
      ["run", "finsocnet", ...args],
      {
        cwd: repoRoot,
        timeout: timeoutMs,
        maxBuffer: 32 * 1024 * 1024,
        env: {
          ...process.env,
          FINSOCNET_HOME: repoRoot,
          PYTHONUNBUFFERED: "1",
        },
      }
    );

    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new Error(`Empty response from CLI. stderr: ${stderr}`);
    }

    try {
      return JSON.parse(trimmed) as Envelope<T>;
    } catch {
      // If output is not JSON (e.g., text command or markdown), wrap in synthetic envelope
      return {
        ok: true,
        command: args.join(" "),
        data: trimmed as unknown as T,
      };
    }
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
  args: string[]
): Promise<Envelope<T>> {
  return runCliCommand<T>(["kb", ...args]);
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
  const res = await runKbCommand<{ persons: Person[] }>(["person", "list"]);
  if (!res.ok) {
    throw new Error(res.error?.message || "Failed to list persons");
  }
  return res.data.persons || [];
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
}): Promise<Source[]> {
  const args = ["source", "list"];
  if (params?.platform) args.push("--platform", params.platform);
  if (params?.person) args.push("--person", params.person);
  if (params?.status) args.push("--status", params.status);

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
}): Promise<ContentItem[]> {
  const args = ["content", "list", "--limit", String(params?.limit || 50)];
  if (params?.platform) args.push("--platform", params.platform);
  if (params?.status) args.push("--status", params.status);
  if (params?.person) args.push("--person", params.person);
  if (params?.source) args.push("--source", params.source);

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

  if (fs.existsSync(skillsDir)) {
    const entries = fs.readdirSync(skillsDir, { withFileTypes: true });
    for (const ent of entries) {
      if (!ent.isDirectory()) continue;
      const skillName = ent.name;
      const skillMdPath = path.join(skillsDir, skillName, "SKILL.md");
      let description = "";
      let version = "2.0.0";
      let type: SkillItem["type"] = "core";

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

      // Categorize
      let categoryGroup = "Other";
      if (
        [
          "knowledge-db",
          "knowledge-transformer",
          "knowledge-dedup",
          "knowledge-search",
          "market-idea-miner",
          "person-matcher",
          "person-skill-synthesizer",
          "person-skills-explorer",
        ].includes(skillName)
      ) {
        type = "core";
        categoryGroup = "Core Knowledge Engine";
      } else if (
        [
          "agent-browser",
          "session-bridge",
          "source-explorer",
          "self-improver",
          "skill-installer",
          "finsocnet",
        ].includes(skillName)
      ) {
        type = "orchestration";
        categoryGroup = "Orchestration & Automation";
      } else if (skillName.endsWith("-explorer") || skillName.endsWith("-extractor") || skillName.endsWith("-reader") || skillName.endsWith("-transcriber") || skillName.endsWith("-searcher")) {
        type = "platform";
        categoryGroup = "Platform Explorers (P1-P3)";
      }

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
