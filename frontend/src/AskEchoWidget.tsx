import { useEffect, useRef, useState } from "react";
import AskEchoReasoningDetails from "./components/AskEchoReasoning";
import { ApiError, formatApiError } from "./api/client";
import {
  createTicketFeedback,
  postAskEcho,
  postAskEchoFeedback,
  postSnippetFeedback,
} from "./api/endpoints";
import type {
  AskEchoKBEvidence,
  AskEchoReference,
  AskEchoResponse,
  AskEchoTicketSummary,
  SnippetFeedbackRequest,
  SnippetSearchResult,
  TicketFeedbackCreate,
} from "./api/types";

type AskEchoWidgetResponse = AskEchoResponse | { error: string };

type AskEchoErrorInfo = {
  headline: string;
  guidance: string;
  detail: string;
  status?: number;
};

type SourceItem = {
  key: string;
  title: string;
  detail: string;
  kind: "ticket" | "kb" | "snippet";
  confidence: number | null;
  href?: string | null;
};

type ConfidenceTone = "high" | "medium" | "low" | "unknown";

type ConfidenceInfo = {
  value: number | null;
  percent: number | null;
  label: string;
  tone: ConfidenceTone;
  description: string;
  sourceLabel: string;
};

function isAskEchoError(response: AskEchoWidgetResponse): response is { error: string } {
  return typeof (response as { error?: unknown })?.error === "string";
}

function normalizeConfidence(value: number | null | undefined): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  if (value <= 1) return Math.max(0, Math.min(1, value));
  return Math.max(0, Math.min(1, value / 100));
}

function formatConfidence(value: number | null): string {
  if (value === null) return "Unavailable";
  return `${Math.round(value * 100)}%`;
}

function getConfidenceInfo(response: AskEchoResponse): ConfidenceInfo {
  const referenceConfidence = normalizeConfidence(response.references?.[0]?.confidence ?? null);
  const kbConfidence = normalizeConfidence(response.kb_confidence ?? null);
  const reasoningConfidence = normalizeConfidence(response.reasoning?.echo_score ?? null);

  const candidate =
    referenceConfidence ??
    (response.kb_backed ? kbConfidence : null) ??
    reasoningConfidence;

  if (candidate === null) {
    return {
      value: null,
      percent: null,
      label: "Confidence unavailable",
      tone: "unknown",
      description: "Echo returned an answer, but this response did not include a confidence score.",
      sourceLabel: "No confidence field",
    };
  }

  if (candidate >= 0.78) {
    return {
      value: candidate,
      percent: Math.round(candidate * 100),
      label: "High confidence",
      tone: "high",
      description: "The answer is backed by a strong match in past support activity.",
      sourceLabel: referenceConfidence !== null ? "Top ticket match" : response.kb_backed ? "Knowledge base score" : "Reasoning score",
    };
  }

  if (candidate >= 0.52) {
    return {
      value: candidate,
      percent: Math.round(candidate * 100),
      label: "Moderate confidence",
      tone: "medium",
      description: "Useful guidance, but review the sources before acting on it.",
      sourceLabel: referenceConfidence !== null ? "Top ticket match" : response.kb_backed ? "Knowledge base score" : "Reasoning score",
    };
  }

  return {
    value: candidate,
    percent: Math.round(candidate * 100),
    label: "Low confidence",
    tone: "low",
    description: "Echo found a weak match. Use this as a starting point, not a final answer.",
    sourceLabel: referenceConfidence !== null ? "Top ticket match" : response.kb_backed ? "Knowledge base score" : "Reasoning score",
  };
}

function buildTicketSource(reference: AskEchoReference, ticket?: AskEchoTicketSummary): SourceItem {
  const title = ticket?.title?.trim() || ticket?.summary?.trim() || `Ticket #${reference.ticket_id}`;
  return {
    key: `ticket-${reference.ticket_id}`,
    title,
    detail: `Resolved ticket #${reference.ticket_id}`,
    kind: "ticket",
    confidence: normalizeConfidence(reference.confidence ?? null),
  };
}

function buildKbSource(entry: AskEchoKBEvidence): SourceItem {
  return {
    key: `kb-${entry.entry_id}`,
    title: entry.title,
    detail: entry.source_system || "Knowledge base",
    kind: "kb",
    confidence: normalizeConfidence(entry.score ?? null),
    href: entry.source_url,
  };
}

function buildSnippetSource(snippet: SnippetSearchResult): SourceItem {
  return {
    key: `snippet-${snippet.id}`,
    title: snippet.title,
    detail: snippet.summary?.trim() || `Snippet #${snippet.id}`,
    kind: "snippet",
    confidence: normalizeConfidence(snippet.echo_score ?? null),
  };
}

function getSourceItems(response: AskEchoResponse): SourceItem[] {
  const items: SourceItem[] = [];
  const seen = new Set<string>();
  const ticketsById = new Map<number, AskEchoTicketSummary>();

  for (const ticket of response.suggested_tickets ?? []) {
    ticketsById.set(ticket.id, ticket);
  }

  for (const reference of response.references ?? []) {
    const item = buildTicketSource(reference, ticketsById.get(reference.ticket_id));
    if (!seen.has(item.key)) {
      seen.add(item.key);
      items.push(item);
    }
  }

  for (const entry of response.kb_evidence ?? []) {
    const item = buildKbSource(entry);
    if (!seen.has(item.key)) {
      seen.add(item.key);
      items.push(item);
    }
  }

  if (items.length === 0) {
    for (const ticket of response.suggested_tickets ?? []) {
      const item: SourceItem = {
        key: `ticket-${ticket.id}`,
        title: ticket.title?.trim() || ticket.summary?.trim() || `Ticket #${ticket.id}`,
        detail: `Suggested ticket #${ticket.id}`,
        kind: "ticket",
        confidence: null,
      };
      if (!seen.has(item.key)) {
        seen.add(item.key);
        items.push(item);
      }
    }
  }

  if (items.length === 0) {
    for (const snippet of response.suggested_snippets ?? []) {
      const item = buildSnippetSource(snippet);
      if (!seen.has(item.key)) {
        seen.add(item.key);
        items.push(item);
      }
    }
  }

  return items.slice(0, 6);
}

function getAnswerModeLabel(response: AskEchoResponse): { label: string; tone: "default" | "warning" | "success" } {
  if (response.answer_kind === "grounded" || response.mode === "kb_answer") {
    return { label: "Grounded answer", tone: "success" };
  }

  if (response.answer_kind === "ungrounded" || response.mode === "general_answer") {
    return { label: "General guidance", tone: "warning" };
  }

  return { label: `Mode: ${response.mode ?? "unknown"}`, tone: "default" };
}

export default function AskEchoWidget() {
  const [queryText, setQueryText] = useState("");
  const [response, setResponse] = useState<AskEchoWidgetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState<AskEchoErrorInfo | null>(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackNotesVisible, setFeedbackNotesVisible] = useState(false);
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [selectedFeedbackTicketId, setSelectedFeedbackTicketId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  function logDevDebug(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    console.debug("[ask-echo]", { event, ...payload });
  }

  function logDevError(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    console.error("[ask-echo]", { event, ...payload });
  }

  function classifyAskEchoError(error: unknown): AskEchoErrorInfo {
    const detail = formatApiError(error);

    if (error instanceof ApiError) {
      if (error.status >= 500) {
        return {
          headline: "Echo hit an error",
          guidance: "The service is reachable, but the request failed on the server. Try again in a moment.",
          detail,
          status: error.status,
        };
      }

      return {
        headline: "Request failed",
        guidance: "Check the wording of your question and try again.",
        detail,
        status: error.status,
      };
    }

    return {
      headline: "Backend not running",
      guidance: "Start the backend on port 8001, then retry your question.",
      detail,
    };
  }

  async function askWithQuery(nextQuery: string) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) return;

    setLoading(true);
    setResponse(null);
    setErrorInfo(null);
    setShowErrorDetails(false);
    setFeedbackSaved(false);
    setFeedbackError(null);
    setFeedbackNotes("");
    setFeedbackNotesVisible(false);
    setLastQuery(trimmedQuery);

    logDevDebug("submit", {
      source: "ask_echo",
      query: trimmedQuery,
      limit: 5,
    });

    try {
      const data = await postAskEcho({ q: trimmedQuery, limit: 5 });
      if (!data) {
        setResponse({ error: "No response received" });
        setErrorInfo({
          headline: "Request failed",
          guidance: "No response was returned. Please try again.",
          detail: "No response payload",
        });
        return;
      }

      setResponse(data);
    } catch (error: unknown) {
      setResponse({ error: formatApiError(error) });
      const classified = classifyAskEchoError(error);
      setErrorInfo(classified);
      logDevError("request_failed", {
        source: "ask_echo",
        query: trimmedQuery,
        headline: classified.headline,
        status: classified.status ?? null,
        detail: classified.detail,
      });
    } finally {
      setLoading(false);
    }
  }

  function ask() {
    void askWithQuery(queryText).catch((error: unknown) => {
      const fallback = classifyAskEchoError(error);
      setResponse({ error: fallback.detail });
      setErrorInfo(fallback);
      setLoading(false);
      logDevError("unexpected_rejection", {
        source: "ask_echo",
        query: queryText,
        detail: fallback.detail,
      });
    });
  }

  useEffect(() => {
    if (!response || isAskEchoError(response)) {
      setSelectedFeedbackTicketId(null);
      setFeedbackSaved(false);
      return;
    }

    setFeedbackSaved(false);
    setFeedbackError(null);

    let selectedTicketId: number | null = null;

    if (Array.isArray(response.references) && response.references.length > 0) {
      selectedTicketId = response.references[0].ticket_id ?? null;
    }

    if (!selectedTicketId && Array.isArray(response.suggested_tickets) && response.suggested_tickets.length > 0) {
      selectedTicketId = response.suggested_tickets[0]?.id ?? null;
    }

    if (!selectedTicketId && Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0) {
      selectedTicketId = response.suggested_snippets[0]?.ticket_id ?? null;
    }

    setSelectedFeedbackTicketId(selectedTicketId);
  }, [response]);

  async function submitFeedback(helped: boolean) {
    setFeedbackError(null);
    setFeedbackSubmitting(true);

    try {
      if (!response || isAskEchoError(response)) {
        throw new Error("No Ask Echo response to attach feedback to.");
      }

      const askEchoLogId = response.ask_echo_log_id ?? null;
      if (!askEchoLogId) {
        throw new Error("Missing Ask Echo log id; please ask again.");
      }

      const trimmedNotes = feedbackNotes.trim();

      await postAskEchoFeedback({
        ask_echo_log_id: askEchoLogId,
        helped,
        notes: !helped && trimmedNotes.length > 0 ? trimmedNotes : null,
      });

      let ticketId = selectedFeedbackTicketId ?? undefined;

      if (!ticketId) {
        ticketId = response.references?.[0]?.ticket_id;
      }

      if (!ticketId) {
        ticketId = response.suggested_tickets?.[0]?.id;
      }

      if (!ticketId) {
        ticketId = response.suggested_snippets?.[0]?.ticket_id ?? undefined;
      }

      if (ticketId) {
        setSelectedFeedbackTicketId(ticketId);

        const snippetPayload: SnippetFeedbackRequest = {
          helped,
          ticket_id: ticketId,
          source: "ask_echo",
        };

        if (!helped && trimmedNotes.length > 0) {
          snippetPayload.notes = trimmedNotes;
          snippetPayload.resolution_notes = trimmedNotes;
        }

        if (queryText.trim().length > 0) {
          snippetPayload.query_text = queryText.trim();
        }

        await postSnippetFeedback(snippetPayload);

        const ticketFeedbackPayload: TicketFeedbackCreate = {
          ticket_id: ticketId,
          rating: helped ? 5 : 1,
          resolution_notes: trimmedNotes || undefined,
          query_text: queryText.trim() || lastQuery,
          helped,
        };

        try {
          await createTicketFeedback(ticketFeedbackPayload);
        } catch {
          // Keep the Ask Echo feedback flow responsive even if analytics persistence fails.
        }
      }

      setFeedbackNotes("");
      setFeedbackNotesVisible(false);
      setFeedbackSaved(true);
    } catch (error: unknown) {
      setFeedbackError(formatApiError(error));
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  const exampleQueries = [
    "password reset does not work after MFA enrollment",
    "vpn auth_failed after laptop replacement",
    "outlook keeps prompting for credentials",
    "new hire cannot access payroll portal",
  ];

  const retryQuery = (lastQuery || queryText).trim();
  const canRetry = retryQuery.length > 0;
  const showInitialEmptyState = !queryText.trim() && !response && !loading;
  const showNoResponseState = !loading && !response && !!lastQuery.trim() && !errorInfo;
  const responseData = response && !isAskEchoError(response) ? response : null;
  const confidence = responseData ? getConfidenceInfo(responseData) : null;
  const sourceItems = responseData ? getSourceItems(responseData) : [];
  const answerMode = responseData ? getAnswerModeLabel(responseData) : null;

  return (
    <div className="ask-echo-shell">
      <div className="ask-echo">
        <section className="ask-echo__hero">
          <div className="ask-echo__hero-copy">
            <span className="ask-echo__eyebrow">Live Ask Echo</span>
            <h1 className="ask-echo__title">Get the likely fix, plus the evidence behind it.</h1>
            <p className="ask-echo__lede">
              Ask a support question in plain language. Echo returns an answer, shows how confident it is,
              and points to the tickets or knowledge base entries that shaped the response.
            </p>
            <div className="ask-echo__hero-chips" aria-label="Ask Echo workflow">
              <span className="ask-echo__hero-chip">1. Ask a real issue</span>
              <span className="ask-echo__hero-chip">2. Review confidence and sources</span>
              <span className="ask-echo__hero-chip">3. Mark whether it helped</span>
            </div>
          </div>

          <div className="ask-echo__command-wrap">
            <label className="ask-echo__input-label" htmlFor="ask-echo-query">
              Describe the problem
            </label>
            <div className="ask-echo__command">
              <input
                id="ask-echo-query"
                ref={inputRef}
                className="op-input ask-echo__input"
                placeholder="Example: user cannot connect to VPN after password reset"
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && ask()}
              />
              <button
                type="button"
                className="op-button op-button--primary ask-echo__submit"
                onClick={ask}
                disabled={loading || !queryText.trim()}
              >
                {loading ? "Searching..." : "Get answer"}
              </button>
            </div>
            <p className="ask-echo__command-help">Press Enter to ask. Start with the user-visible symptom, not the suspected root cause.</p>
          </div>
        </section>

        {showInitialEmptyState && (
          <section className="ask-echo__empty-grid">
            <div className="ask-echo__card ask-echo__empty-card">
              <div className="ask-echo__card-head">
                <div>
                  <div className="ask-echo__eyebrow">Start here</div>
                  <h2 className="ask-echo__section-title">Ask about the issue exactly as support would hear it.</h2>
                </div>
              </div>
              <p className="ask-echo__empty-copy">
                Good prompts mention the symptom, system, or trigger. Echo will search prior tickets and show its supporting evidence.
              </p>
            </div>

            <div className="ask-echo__card ask-echo__examples-card">
              <div className="ask-echo__card-head">
                <div>
                  <div className="ask-echo__eyebrow">Try one</div>
                  <h2 className="ask-echo__section-title">Example questions</h2>
                </div>
              </div>
              <div className="ask-echo__examples">
                {exampleQueries.map((example) => (
                  <button
                    key={example}
                    type="button"
                    className="operator-pill"
                    onClick={() => {
                      setQueryText(example);
                      setResponse(null);
                      setErrorInfo(null);
                      inputRef.current?.focus();
                    }}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </section>
        )}

        {loading && (
          <section className="ask-echo__loading-card" aria-live="polite">
            <div className="ask-echo__spinner" />
            <div>
              <div className="ask-echo__loading-title">Searching past resolutions...</div>
              <div className="ask-echo__loading-sub">Echo is ranking ticket matches, snippets, and knowledge base evidence.</div>
            </div>
          </section>
        )}

        {response && isAskEchoError(response) && errorInfo && (
          <section className="ask-echo__error" aria-live="polite">
            <div className="ask-echo__error-title">{errorInfo.headline}</div>
            <div className="ask-echo__error-message">{errorInfo.guidance}</div>
            <div className="ask-echo__error-actions">
              <button
                type="button"
                className="op-button op-button--primary"
                onClick={() => askWithQuery(retryQuery)}
                disabled={loading || !canRetry}
              >
                Retry question
              </button>
              <button
                type="button"
                className="ask-echo__link-button"
                onClick={() => setShowErrorDetails((currentValue) => !currentValue)}
              >
                {showErrorDetails ? "Hide technical details" : "Show technical details"}
              </button>
            </div>
            {showErrorDetails && (
              <div className="ask-echo__error-details">
                {typeof errorInfo.status === "number" && (
                  <div>
                    <span className="ask-echo__error-label">HTTP status:</span> {errorInfo.status}
                  </div>
                )}
                <div>
                  <span className="ask-echo__error-label">Error:</span> {errorInfo.detail}
                </div>
              </div>
            )}
          </section>
        )}

        {responseData && confidence && answerMode && (
          <section className="ask-echo__results">
            <div className="ask-echo__results-main">
              <div className="ask-echo__card ask-echo__card--answer">
                <div className="ask-echo__card-head ask-echo__card-head--split">
                  <div>
                    <div className="ask-echo__eyebrow">Answer</div>
                    <h2 className="ask-echo__section-title">Recommended next step</h2>
                    <p className="ask-echo__section-subtitle">For: {lastQuery}</p>
                  </div>
                  <span className={`ask-echo__badge ask-echo__badge--${answerMode.tone}`}>{answerMode.label}</span>
                </div>

                <div className="ask-echo__answer">{responseData.answer || "No answer returned yet."}</div>

                <div className="ask-echo__result-stats" aria-label="response summary">
                  <div className="ask-echo__stat">
                    <span className="ask-echo__stat-label">Confidence</span>
                    <strong>{formatConfidence(confidence.value)}</strong>
                  </div>
                  <div className="ask-echo__stat">
                    <span className="ask-echo__stat-label">Sources</span>
                    <strong>{sourceItems.length}</strong>
                  </div>
                  <div className="ask-echo__stat">
                    <span className="ask-echo__stat-label">Log ID</span>
                    <strong>{responseData.ask_echo_log_id}</strong>
                  </div>
                </div>
              </div>

              <div className="ask-echo__card">
                <div className="ask-echo__card-head ask-echo__card-head--split">
                  <div>
                    <div className="ask-echo__eyebrow">Sources</div>
                    <h2 className="ask-echo__section-title">Why Echo chose this answer</h2>
                  </div>
                  <span className="ask-echo__badge">{sourceItems.length} shown</span>
                </div>

                {sourceItems.length > 0 ? (
                  <div className="ask-echo__sources">
                    {sourceItems.map((item) => (
                      <div key={item.key} className="ask-echo__source-item">
                        <div className="ask-echo__source-topline">
                          <div>
                            <div className="ask-echo__source-title">{item.title}</div>
                            <div className="ask-echo__source-detail">{item.detail}</div>
                          </div>
                          <div className="ask-echo__source-meta">
                            <span className={`ask-echo__badge ask-echo__badge--source-${item.kind}`}>{item.kind}</span>
                            <span className="ask-echo__badge">{formatConfidence(item.confidence)}</span>
                          </div>
                        </div>
                        {item.href ? (
                          <a className="ask-echo__kb-link" href={item.href} target="_blank" rel="noreferrer">
                            Open source document
                          </a>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="state-panel">Echo returned an answer, but there were no explicit sources in this response.</div>
                )}
              </div>

              {Array.isArray(responseData.suggested_snippets) && responseData.suggested_snippets.length > 0 && (
                <div className="ask-echo__card">
                  <div className="ask-echo__card-head">
                    <div>
                      <div className="ask-echo__eyebrow">Supporting evidence</div>
                      <h2 className="ask-echo__section-title">Related snippets</h2>
                    </div>
                  </div>
                  <div className="snippet-list">
                    {responseData.suggested_snippets.slice(0, 4).map((snippet) => (
                      <div key={String(snippet.id)} className="snippet-item">
                        <div className="snippet-item__title">
                          <span>{snippet.title}</span>
                          <span className="ask-echo__badge">{formatConfidence(normalizeConfidence(snippet.echo_score ?? null))}</span>
                        </div>
                        {snippet.summary && <div className="snippet-item__meta">{snippet.summary}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <AskEchoReasoningDetails reasoning={responseData.reasoning} />
            </div>

            <aside className="ask-echo__results-side">
              <div className="ask-echo__card ask-echo__confidence-card">
                <div className="ask-echo__card-head">
                  <div>
                    <div className="ask-echo__eyebrow">Confidence</div>
                    <h2 className="ask-echo__section-title">How strong is this answer?</h2>
                  </div>
                </div>
                <div className="ask-echo__confidence-value">
                  <span>{formatConfidence(confidence.value)}</span>
                  <strong>{confidence.label}</strong>
                </div>
                <div className="ask-echo__confidence-meter" aria-hidden="true">
                  <div
                    className={`ask-echo__confidence-fill ask-echo__confidence-fill--${confidence.tone}`}
                    style={{ width: `${confidence.percent ?? 12}%` }}
                  />
                </div>
                <p className="ask-echo__confidence-copy">{confidence.description}</p>
                <div className="ask-echo__confidence-footnote">Source: {confidence.sourceLabel}</div>
              </div>

              <div className="ask-echo__card ask-echo__feedback-card">
                <div className="ask-echo__card-head">
                  <div>
                    <div className="ask-echo__eyebrow">Feedback</div>
                    <h2 className="ask-echo__section-title">Did this help you move forward?</h2>
                  </div>
                </div>

                <div className="ask-echo__feedback-row">
                  <button
                    type="button"
                    className="op-button op-button--primary ask-echo__feedback-button"
                    onClick={() => submitFeedback(true)}
                    disabled={feedbackSubmitting || feedbackSaved}
                  >
                    <span aria-hidden="true">👍</span>
                    Helpful
                  </button>
                  <button
                    type="button"
                    className="op-button op-button--ghost ask-echo__feedback-button"
                    onClick={() => setFeedbackNotesVisible(true)}
                    disabled={feedbackSubmitting || feedbackSaved}
                  >
                    <span aria-hidden="true">👎</span>
                    Not helpful
                  </button>
                </div>

                {feedbackSaved && <div className="ask-echo__feedback-success">Feedback saved. Future answers can improve from this signal.</div>}

                {!feedbackSaved && !feedbackNotesVisible && (
                  <p className="ask-echo__feedback-hint">Choose “Not helpful” if the answer was misleading, incomplete, or missing key context.</p>
                )}

                {feedbackNotesVisible && !feedbackSaved && (
                  <div className="ask-echo__feedback-form">
                    <label className="ask-echo__input-label" htmlFor="ask-echo-feedback-notes">
                      What was missing or wrong?
                    </label>
                    <textarea
                      id="ask-echo-feedback-notes"
                      rows={4}
                      className="op-input ask-echo__textarea"
                      placeholder="Example: the answer ignored the recent VPN client rollout, and the actual fix was to clear the stale certificate."
                      value={feedbackNotes}
                      onChange={(event) => setFeedbackNotes(event.target.value)}
                    />
                    <div className="ask-echo__feedback-actions">
                      <button
                        type="button"
                        className="op-button op-button--danger"
                        onClick={() => submitFeedback(false)}
                        disabled={feedbackSubmitting}
                      >
                        {feedbackSubmitting ? "Saving..." : "Save negative feedback"}
                      </button>
                      <button
                        type="button"
                        className="op-button op-button--ghost"
                        onClick={() => {
                          setFeedbackNotesVisible(false);
                          setFeedbackNotes("");
                          setFeedbackError(null);
                        }}
                        disabled={feedbackSubmitting}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {feedbackError && <div className="ask-echo__feedback-error">Failed to save feedback: {feedbackError}</div>}
              </div>
            </aside>
          </section>
        )}

        {showNoResponseState && (
          <section className="ask-echo__error">
            <div className="ask-echo__error-title">No answer returned</div>
            <div className="ask-echo__error-message">Echo did not return a usable payload for that question.</div>
            <div className="ask-echo__error-actions">
              <button
                type="button"
                className="op-button op-button--primary"
                onClick={() => askWithQuery(retryQuery)}
                disabled={!canRetry}
              >
                Ask again
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
