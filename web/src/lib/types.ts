export interface Envelope<T = unknown> {
  ok: boolean;
  command: string;
  data: T;
  warnings?: string[];
  error?: {
    code: string;
    message: string;
    hint?: string | null;
  };
  meta?: {
    elapsed_ms: number;
  };
}

export interface StatsData {
  tables: Record<string, number>;
  contents_by_status: Record<string, number>;
  contents_by_platform: Record<string, number>;
  cards_by_status: Record<string, number>;
  cards_by_category: Record<string, number>;
  top_persons: Array<{
    id: string;
    canonical_name: string;
    cards_count: number;
    contents_count: number;
  }>;
  open_gaps: number;
  queue_by_status: Record<string, number>;
  sessions: {
    total: number;
    valid: number;
    expiring_soon: number;
  };
}

export interface DoctorReport {
  ok: boolean;
  sqlite_version: string;
  schema: {
    current_migration: string;
    applied_count: number;
  };
  integrity: string;
  fts_integrity: Record<string, string>;
  orphans: Record<string, number>;
  migrations?: string[];
}

export interface KnowledgeCard {
  id: number;
  card_version: number;
  kind: string;
  domain: string;
  category: string;
  subject: string;
  claim: string;
  action: string;
  horizon: string;
  evidence_level: string;
  invalidation: string | null;
  notes: string | null;
  status: string;
  merged_into: number | null;
  transformer_version: string;
  produced_by: string;
  run_id: number;
  created_at: string;
  updated_at: string;
  conditions: string[];
  instruments: string[];
  regime: string[];
  terms: string[];
  aliases: string[];
  entities: string[];
  numbers: Record<string, unknown>;
  stats?: {
    citations_count: number;
    links_count: number;
    history_count: number;
  };
  citations?: CardCitation[];
  links?: CardLink[];
  history?: CardHistory[];
}

export interface CardCitation {
  id: number;
  card_id: number;
  content_id: string;
  segment_seq: number | null;
  locator_json: string | Record<string, unknown> | null;
  quote: string;
  person_id: string | null;
  speaker_role: string;
  stance: string;
  confidence: number;
  quote_verified: number;
  created_at?: string;
  content_title?: string;
  platform?: string;
  person_name?: string;
}

export interface CardLink {
  id?: number;
  from_card_id: number;
  to_card_id: number;
  relation: "same" | "refines" | "related" | "contradicts";
  reason: string;
  created_at?: string;
  target_card?: Partial<KnowledgeCard>;
}

export interface CardHistory {
  id: number;
  card_id: number;
  version: number;
  snapshot_json: string;
  reason: string;
  created_at: string;
}

export interface PersonAppearance {
  id?: number;
  person_id: string;
  content_id: string;
  source_id?: string | null;
  role: string;
  confidence?: number;
  content_title?: string;
  platform?: string;
}

export interface Person {
  id: string;
  canonical_name: string;
  moniker: string | null;
  bio: string | null;
  avatar_url: string | null;
  avatar_path?: string | null;
  images?: Array<{ id: number; kind: string; platform: string | null; source_url: string; path: string; width: number | null; height: number | null }>;
  trading_style: string | null;
  primary_markets: string | null;
  verified_records: string | null;
  profession?: string | null;
  affiliation?: string | null;
  domains?: string | null;
  homepage?: string | null;
  relevance?: string | null;
  external_ids?: Record<string, string>;
  links?: Array<{ id: number; url: string; kind: string; platform: string; handle: string | null; label: string | null; confidence: number; match_status: string; evidence: string | null }>;
  visibility: string;
  status: string;
  merged_into: string | null;
  created_at: string;
  updated_at: string;
  aliases: Array<{
    alias: string;
    platform?: string;
    alias_key?: string;
  }>;
  stats?: {
    cards_count: number;
    contents_count: number;
    citations_count: number;
  };
  sources?: Source[];
  appearances?: PersonAppearance[];
}

export interface PersonSkill {
  id: number;
  person_id: string;
  skill_name: string;
  category: string;
  title: string;
  summary: string;
  content_markdown: string;
  produced_by: string;
  run_id: number;
  updated_at: string;
}

export interface Source {
  id: string;
  platform: string;
  kind: string;
  handle_or_name: string;
  title: string | null;
  url: string | null;
  person_id: string | null;
  status: string;
  subscriber_count?: number | null;
  content_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ContentItem {
  id: string;
  source_id: string | null;
  platform: string;
  content_type: string;
  url: string | null;
  title: string | null;
  description: string | null;
  author_handle: string | null;
  person_id: string | null;
  published_at: string | null;
  duration_sec: number | null;
  metrics_json?: Record<string, unknown> | null;
  process_status: string;
  cards_count: number;
  segments: number;
  created_at?: string;
  updated_at?: string;
}

export interface ContentSegmentView {
  content_id: string;
  from_seq: number;
  to_seq: number;
  segments: number;
  text: string;
}

export interface VocabTerm {
  term: string;
  label: string;
  facet: string;
  aliases: string[];
  broader: string | null;
  definition: string | null;
  status: string;
  merged_into: string | null;
}

export interface AgentRun {
  id: number;
  parent_run_id: number | null;
  skill: string;
  harness: string;
  model: string | null;
  goal: string;
  outcome: string | null;
  started_at: string;
  ended_at: string | null;
  elapsed_ms: number | null;
  cards_created?: number;
  cards_modified?: number;
  citations_created?: number;
}

export interface DedupDecision {
  id: number;
  run_id: number;
  new_card_id: number;
  decision: string;
  target_card_id: number | null;
  result_card_id: number | null;
  rationale: string;
  reviewer_verdict: string | null;
  reviewer_note: string | null;
  created_at: string;
}

export interface KnowledgeGap {
  id: number;
  query: string;
  asked_count: number;
  verdict: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ExploreQueueItem {
  id: number;
  target: string;
  target_kind: string;
  platform: string | null;
  action: string | null;
  origin: string;
  reason: string | null;
  priority: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SkillItem {
  name: string;
  type: "core" | "installed" | "platform" | "orchestration" | "improved";
  version: string;
  description: string;
  path?: string;
  categoryGroup?: string;
}

// ---- unified search (finsocnet kb search) ----

export type SearchType = "cards" | "contents" | "persons" | "skills";
export type SearchMode = "auto" | "hybrid" | "semantic" | "lexical";

export interface SearchHit {
  type: SearchType;
  id: string;
  title: string;
  snippet: string | null;
  score: number;
  relevance: number;
  ranks: { lex?: number; vec?: number } & Record<string, number>;
  url?: string | null;
  meta: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  mode: string;
  types: SearchType[];
  filters: Record<string, unknown>;
  total: number;
  facets: Record<string, number>;
  results: SearchHit[];
}

export interface EmbedStatus {
  model: string;
  provider: string;
  kinds: Record<string, { embedded: number; pending: number }>;
}
