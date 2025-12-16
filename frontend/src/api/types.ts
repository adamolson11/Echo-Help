export type ApiMeta = {
  kind: string;
  version: string;
};

export type UnhelpfulExample = {
  ticket_id: number;
  resolution_notes: string | null;
  created_at: string;
};

export type TicketFeedbackInsights = {
  meta: ApiMeta;
  total_feedback: number;
  helped_true: number;
  helped_false: number;
  helped_null: number;
  unhelpful_examples: UnhelpfulExample[];
};

export type FeedbackCluster = {
  cluster_index: number;
  size: number;
  example_ticket_ids: number[];
  example_notes: string[];
};

export type FeedbackClustersResponse = {
  meta: ApiMeta;
  clusters: FeedbackCluster[];
};

export type FeedbackPatternsSummary = {
  meta: ApiMeta;
  stats: {
    total_feedback: number;
    positive: number;
    negative: number;
    window_days: number;
  };
  top_comments: unknown[];
};

export type PatternKeyword = { keyword: string; count: number };
export type PatternTitle = { title: string; count: number };

export type TicketPatternRadarResponse = {
  meta: ApiMeta;
  top_keywords: PatternKeyword[];
  frequent_titles: PatternTitle[];
  semantic_clusters: unknown[];
  stats: {
    total_tickets: number;
    window_days: number;
    first_ticket_at?: string | null;
    last_ticket_at?: string | null;
  };
};

export type AskEchoLogSummary = {
  id: number;
  query_text: string;
  ticket_id: number | null;
  echo_score: number | null;
  created_at: string | null;
};

export type ReasoningSnippetCandidate = {
  id: number;
  title?: string | null;
  score?: number | null;
};

export type AskEchoLogDetail = {
  id: number;
  query_text: string;
  answer_text: string;
  ticket_id: number | null;
  echo_score: number | null;
  created_at: string | null;
  reasoning?: {
    candidate_snippets: ReasoningSnippetCandidate[];
    chosen_snippet_ids: number[];
  } | null;
  reasoning_notes?: string | null;
};

export type AskEchoLogsResponse = {
  meta: ApiMeta;
  items: AskEchoLogSummary[];
};

export type AskEchoLogDetailResponse = {
  meta: ApiMeta;
  item: AskEchoLogDetail;
};

export type AskEchoFeedbackRow = {
  id: number;
  ask_echo_log_id: number;
  helped: boolean;
  notes: string | null;
  query_text: string | null;
  created_at: string;
};

export type AskEchoFeedbackResponse = {
  meta: ApiMeta;
  items: AskEchoFeedbackRow[];
};

export type SnippetSearchResult = {
  id: number;
  title: string;
  summary: string | null;
  echo_score: number;
  success_count?: number;
  failure_count?: number;
  ticket_id?: number | null;
};

export type SnippetFeedbackRequest = {
  snippet_id?: number | null;
  ticket_id?: number | null;
  helped: boolean;
  notes?: string | null;
};

export type SnippetFeedbackResponse = {
  snippet_id: number;
  echo_score: number;
};

export type AskEchoRequest = {
  q: string;
  limit?: number;
};

export type AskEchoReference = {
  ticket_id: number;
  confidence?: number | null;
};

export type AskEchoTicketSummary = {
  id: number;
  summary?: string | null;
  title?: string | null;
};

export type AskEchoReasoningSnippet = {
  id: number;
  title?: string | null;
  score?: number | null;
};

export type AskEchoReasoning = {
  candidate_snippets: AskEchoReasoningSnippet[];
  chosen_snippet_ids: number[];
  echo_score?: number | null;
};

export type AskEchoResponse = {
  meta: ApiMeta;
  query: string;
  answer: string;
  answer_kind: "grounded" | "ungrounded";
  ask_echo_log_id: number;
  suggested_tickets: AskEchoTicketSummary[];
  suggested_snippets: SnippetSearchResult[];
  kb_backed: boolean;
  kb_confidence: number;
  mode?: string | null;
  references: AskEchoReference[];
  reasoning?: AskEchoReasoning | null;
};

export type AskEchoFeedbackCreate = {
  ask_echo_log_id: number;
  helped: boolean;
  notes?: string | null;
};

export type AskEchoFeedbackRead = {
  id: number;
  ask_echo_log_id: number;
  helped: boolean;
  notes: string | null;
  created_at: string;
};

export type Ticket = {
  id: number;
  short_id?: string | null;
  external_key: string;
  source: string;
  project_key: string;
  summary: string;
  description: string;
  body_md?: string | null;
  root_cause?: string | null;
  environment?: string | null;
  tags?: string[] | null;
  status: string;
  priority?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  [key: string]: unknown;
};

// UI-friendly ticket row shape returned by the frontend API layer.
// Intentionally permissive so we can normalize /search and /semantic-search
// results in one place without duplicating "TicketResult"-like types in pages.
export type SearchTicketResult = {
  id: number | string;
  summary?: string;
  title?: string;
  description?: string | null;
  source?: string;
  status?: string;
  priority?: string | null;
  created_at?: string;
  updated_at?: string;
  external_key?: string;
  project_key?: string;
  ai_score?: number;
  [key: string]: unknown;
};

export type SemanticSearchResult = {
  ticket_id: number;
  score: number;
  summary: string;
  description?: string | null;
};

export type TicketFeedbackCreate = {
  ticket_id: number;
  query_text: string;
  rating: number;
  helped?: boolean | null;
  resolution_notes?: string | null;
  ai_cluster_id?: string | null;
  ai_summary?: string | null;
};

export type TicketFeedbackRead = {
  id: number;
  ticket_id: number;
  query_text: string;
  rating: number;
  helped: boolean | null;
  resolution_notes: string | null;
  ai_cluster_id: string | null;
  ai_summary: string | null;
  created_at: string;
};

export type IntakeSuggestedTicket = {
  id: number;
  external_key: string;
  summary: string;
  description: string;
  status: string;
  priority?: string | null;
  created_at?: string | null;
  similarity: number;
};

export type IntakeResponse = {
  query: string;
  suggested_tickets: IntakeSuggestedTicket[];
  predicted_category?: string | null;
  predicted_subcategory?: string | null;
};

export type IntakeRequest = {
  text: string;
};

export type LegacyFeedbackRequest = {
  ticket_id: number;
  query_text: string;
  rating: number;
};

export type LegacyFeedbackResponse = {
  id: number;
  ticket_id: number;
  rating: number;
};

// Search tab's legacy patterns UI shape (kept stable to avoid UX churn).
export type SearchPatternsSummary = {
  total_feedback: number;
  by_ticket: Array<{ ticket_id: number; summary?: string; total_feedback: number; unresolved: number }>;
  top_unresolved: Array<{ ticket_id: number; summary?: string; total_feedback: number; unresolved: number }>;
};
