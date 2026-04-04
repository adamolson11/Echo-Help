import { apiFetch } from "./client";
import type {
  AskEchoRequest,
  AskEchoResponse,
  AskEchoFeedbackCreate,
  AskEchoFeedbackRead,
  AskEchoFeedbackResponse,
  AskEchoLogDetailResponse,
  AskEchoLogsResponse,
  FeedbackPatternsSummary,
  FeedbackClustersResponse,
  IntakeRequest,
  IntakeResponse,
  FlywheelOutcomeRequest,
  FlywheelOutcomeResponse,
  FlywheelRecommendRequest,
  FlywheelRecommendResponse,
  LegacyFeedbackRequest,
  LegacyFeedbackResponse,
  SearchPatternsSummary,
  TicketFeedbackInsights,
  TicketPatternRadarResponse,
  Ticket,
  TicketCreateRequest,
  SemanticSearchResult,
  SearchTicketResult,
  SnippetFeedbackRequest,
  SnippetFeedbackResponse,
  SnippetSearchResult,
  TicketFeedbackCreate,
  TicketFeedbackRead,
} from "./types";

export function getTicketFeedbackInsights() {
  return apiFetch<TicketFeedbackInsights>("/api/insights/feedback");
}

export function getTicketFeedbackClusters(params: {
  n_clusters?: number;
  max_examples_per_cluster?: number;
}) {
  const qs = new URLSearchParams();
  qs.set("n_clusters", String(params.n_clusters ?? 5));
  qs.set("max_examples_per_cluster", String(params.max_examples_per_cluster ?? 3));
  return apiFetch<FeedbackClustersResponse>(`/api/insights/feedback/clusters?${qs.toString()}`);
}

export function getFeedbackPatternsSummary(days: number) {
  return apiFetch<FeedbackPatternsSummary>(`/api/patterns/summary?days=${encodeURIComponent(String(days))}`);
}

export async function getSearchPatternsSummary(days: number): Promise<SearchPatternsSummary> {
  const data = await getFeedbackPatternsSummary(days);
  return {
    total_feedback: (data?.stats?.total_feedback ?? 0) as number,
    by_ticket: [],
    top_unresolved: [],
  };
}

export function getTicketPatternRadar(days: number) {
  return apiFetch<TicketPatternRadarResponse>(`/api/insights/ticket-pattern-radar?days=${encodeURIComponent(String(days))}`);
}

export function getInsightsAskEchoLogs(limit: number) {
  return apiFetch<AskEchoLogsResponse>(`/api/insights/ask-echo-logs?limit=${encodeURIComponent(String(limit))}`);
}

export function getInsightsAskEchoLogDetail(logId: number) {
  return apiFetch<AskEchoLogDetailResponse>(`/api/insights/ask-echo-logs/${encodeURIComponent(String(logId))}`);
}

export function getInsightsAskEchoFeedback(limit: number) {
  return apiFetch<AskEchoFeedbackResponse>(`/api/insights/ask-echo-feedback?limit=${encodeURIComponent(String(limit))}`);
}

export function getTicketById(ticketId: number, signal?: AbortSignal) {
  return apiFetch<Ticket>(`/api/tickets/${encodeURIComponent(String(ticketId))}`, { signal });
}

export function createTicket(payload: TicketCreateRequest, signal?: AbortSignal) {
  return apiFetch<Ticket>("/api/tickets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function searchSnippets(query: string, limit = 30) {
  const q = (query || "").trim();
  return apiFetch<SnippetSearchResult[]>(`/api/snippets/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(String(limit))}`);
}

export function postAskEcho(payload: AskEchoRequest, signal?: AbortSignal) {
  return apiFetch<AskEchoResponse>("/api/ask-echo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q: payload.q, limit: payload.limit ?? 5 }),
    signal,
  });
}

export function postFlywheelRecommend(payload: FlywheelRecommendRequest, signal?: AbortSignal) {
  return apiFetch<FlywheelRecommendResponse>("/api/flywheel/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function postFlywheelOutcome(payload: FlywheelOutcomeRequest, signal?: AbortSignal) {
  return apiFetch<FlywheelOutcomeResponse>("/api/flywheel/outcome", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function postAskEchoFeedback(payload: AskEchoFeedbackCreate, signal?: AbortSignal) {
  return apiFetch<AskEchoFeedbackRead>("/api/ask-echo/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function postSnippetFeedback(payload: SnippetFeedbackRequest, signal?: AbortSignal) {
  return apiFetch<SnippetFeedbackResponse>("/api/snippets/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function createTicketFeedback(payload: TicketFeedbackCreate, signal?: AbortSignal) {
  return apiFetch<TicketFeedbackRead>("/api/ticket-feedback/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function listTicketFeedback(ticketId?: number, signal?: AbortSignal) {
  const qs = new URLSearchParams();
  if (ticketId !== undefined && ticketId !== null) {
    qs.set("ticket_id", String(ticketId));
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<TicketFeedbackRead[]>(`/api/ticket-feedback/${suffix}`, {
    signal,
  });
}

export async function searchTicketsText(q: string, signal?: AbortSignal): Promise<SearchTicketResult[]> {
  const data = await apiFetch<Ticket[]>("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q }),
    signal,
  });

  // Pass-through: backend returns Ticket rows; the UI consumes a subset.
  return (Array.isArray(data) ? data : []) as unknown as SearchTicketResult[];
}

export async function searchTicketsSemantic(
  params: { q: string; status?: string; priority?: string; limit?: number },
  signal?: AbortSignal
): Promise<SearchTicketResult[]> {
  const data = await apiFetch<SemanticSearchResult[]>("/api/semantic-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      q: params.q,
      status: params.status,
      priority: params.priority,
      limit: params.limit ?? 5,
    }),
    signal,
  });

  return (Array.isArray(data) ? data : []).map((item) => ({
    ...item,
    id: item.ticket_id,
    summary: item.summary,
    description: item.description ?? undefined,
    ai_score: typeof item.score === "number" ? item.score : undefined,
  })) as SearchTicketResult[];
}

export function postIntake(payload: IntakeRequest, signal?: AbortSignal) {
  return apiFetch<IntakeResponse>("/api/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function postLegacyFeedback(payload: LegacyFeedbackRequest, signal?: AbortSignal) {
  return apiFetch<LegacyFeedbackResponse>("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}
