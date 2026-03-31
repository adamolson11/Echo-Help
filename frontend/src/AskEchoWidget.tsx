import { useState, useEffect, useRef } from "react";
import type { FormEvent } from "react";
import AskEchoReasoningDetails from "./components/AskEchoReasoning";
import { ApiError, formatApiError } from "./api/client";
import {
  createTicketFeedback,
  postAskEcho,
  postAskEchoFeedback,
  postSnippetFeedback,
} from "./api/endpoints";
import type { AskEchoResponse } from "./api/types";
import { navigateToTicket } from "./appRoutes";

type AskEchoWidgetResponse = AskEchoResponse | { error: string };

type AskEchoErrorInfo = {
  headline: string;
  guidance: string;
  detail: string;
  status?: number;
};

function formatConfidencePercent(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "Unknown";
  const normalized = value <= 1 ? value * 100 : value;
  const clamped = Math.max(0, Math.min(100, normalized));
  return `${Math.round(clamped)}%`;
}

function isAskEchoError(r: AskEchoWidgetResponse): r is { error: string } {
  return typeof r === "object" && r !== null && "error" in r && typeof r.error === "string";
}

function openTicketDetail(ticketId: number) {
  navigateToTicket(ticketId);
}

export default function AskEchoWidget() {
  const [q, setQ] = useState("");
  const [response, setResponse] = useState<AskEchoWidgetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState<AskEchoErrorInfo | null>(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);
  // feedback UI state
  const [fbSubmitting, setFbSubmitting] = useState(false);
  const [fbSaved, setFbSaved] = useState(false);
  const [fbError, setFbError] = useState<string | null>(null);
  const [fbNotesVisible, setFbNotesVisible] = useState(false);
  const [fbNotes, setFbNotes] = useState("");
  const [selectedFeedbackTicketId, setSelectedFeedbackTicketId] = useState<number | null>(null);
  const trimmedQuery = q.trim();
  const canSubmit = !loading && trimmedQuery.length > 0;

  function logDevDebug(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    console.debug("[ask-echo]", { event, ...payload });
  }

  function logDevError(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    console.error("[ask-echo]", { event, ...payload });
  }

  function classifyAskEchoError(err: unknown): AskEchoErrorInfo {
    const detail = formatApiError(err);

    if (err instanceof ApiError) {
      if (err.status >= 500) {
        return {
          headline: "Echo hit an error",
          guidance: "Please try again in a moment.",
          detail,
          status: err.status,
        };
      }
      return {
        headline: "Request failed",
        guidance: "Please check your input and try again.",
        detail,
        status: err.status,
      };
    }

    return {
      headline: "Backend not running",
      guidance: "Start backend on :8001, then try again.",
      detail,
    };
  }

  async function askWithQuery(query: string) {
    if (!query.trim()) return;
    setLoading(true);
    setResponse(null);
    setErrorInfo(null);
    setShowErrorDetails(false);
    setFbSaved(false);
    setLastQuery(query);
    logDevDebug("submit", {
      source: "ask_echo",
      query,
      limit: 5,
    });
    try {
      const data = await postAskEcho({ q: query, limit: 5 });
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
    } catch (err: unknown) {
      // Preserve prior rendering behavior: store an error string on response.
      setResponse({ error: formatApiError(err) });
      const classified = classifyAskEchoError(err);
      setErrorInfo(classified);
      logDevError("request_failed", {
        source: "ask_echo",
        query,
        headline: classified.headline,
        status: classified.status ?? null,
        detail: classified.detail,
      });
    } finally {
      setLoading(false);
    }
  }

  function ask() {
    void askWithQuery(q).catch((err: unknown) => {
      const fallback = classifyAskEchoError(err);
      setResponse({ error: fallback.detail });
      setErrorInfo(fallback);
      setLoading(false);
      logDevError("unexpected_rejection", {
        source: "ask_echo",
        query: q,
        detail: fallback.detail,
      });
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    ask();
  }

  useEffect(() => {
    if (!response || isAskEchoError(response)) {
      setSelectedFeedbackTicketId(null);
      setFbSaved(false);
      return;
    }

    setFbSaved(false);

    // Prefer references (returned as { ticket_id, confidence }), then results (full tickets), then snippet.ticket_id
    let pick: number | null = null;
    if (Array.isArray(response.references) && response.references.length > 0) {
      pick = response.references[0].ticket_id ?? null;
    }
    if (!pick && Array.isArray(response.suggested_tickets) && response.suggested_tickets.length > 0) {
      const r0 = response.suggested_tickets[0];
      pick = r0?.id ?? null;
    }
    if (!pick && Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0) {
      const s0 = response.suggested_snippets[0];
      if (s0 && s0.ticket_id) pick = s0.ticket_id;
    }

    setSelectedFeedbackTicketId(pick);
  }, [response]);

  async function submitFeedback(helped: boolean) {
    setFbError(null);
    setFbSubmitting(true);
    try {
      if (!response || isAskEchoError(response)) {
        throw new Error("No Ask Echo response to attach feedback to.");
      }

      const askEchoLogId: number | null = response.ask_echo_log_id ?? null;
      if (!askEchoLogId) {
        throw new Error("Missing Ask Echo log id; please ask again.");
      }

      // Always record Ask Echo feedback by log id (works even when ungrounded).
      await postAskEchoFeedback({
        ask_echo_log_id: askEchoLogId,
        helped,
        notes: (!helped && fbNotes.trim().length > 0) ? fbNotes.trim() : null,
      });

      // Determine ticket id to attach to feedback.
      // Priority: explicit selectedFeedbackTicketId -> response.references -> response.results -> snippet.ticket_id
      let ticketId: number | undefined;
      if (selectedFeedbackTicketId) ticketId = selectedFeedbackTicketId;

      if ((!ticketId || ticketId === null) && response) {
        if (Array.isArray(response.references) && response.references.length > 0) {
          ticketId = response.references[0].ticket_id;
        }
        if ((!ticketId || ticketId === null) && Array.isArray(response.suggested_tickets) && response.suggested_tickets.length > 0) {
          const r0 = response.suggested_tickets[0];
          ticketId = r0?.id ?? undefined;
        }
        if ((!ticketId || ticketId === null) && Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0) {
          const s0 = response.suggested_snippets[0];
          if (s0 && s0.ticket_id) ticketId = s0.ticket_id;
        }
      }

      // If we found a ticket id, ensure the local state reflects it so subsequent clicks reuse it.
      if (ticketId) setSelectedFeedbackTicketId(ticketId);

      // If there is no ticket id, we've still captured Ask Echo feedback by log id.
      // Skip snippet/ticket feedback persistence in that case.
      if (!ticketId && ticketId !== 0) {
        setFbNotes("");
        setFbNotesVisible(false);
        setFbSaved(true);
        return;
      }

      // Build payload. Backend expects `notes` for resolution notes; include `resolution_notes` and `query_text` as well for context.
      const payload: SnippetFeedbackRequest & {
        source?: string;
        resolution_notes?: string;
        query_text?: string;
      } = { helped, ticket_id: ticketId, source: "ask_echo" };
      if (!helped && fbNotes.trim().length > 0) {
        payload.notes = fbNotes.trim();
        payload.resolution_notes = fbNotes.trim();
      }
      if (q && q.trim().length > 0) payload.query_text = q.trim();

      await postSnippetFeedback(payload);

      // Also record a ticket-feedback row so Ask Echo feedback is visible in Insights.
      // Map helped -> rating (5 for helped, 1 for not helped) to satisfy TicketFeedback.rating requirement.
      try {
        const tfPayload: TicketFeedbackCreate = {
          ticket_id: ticketId,
          rating: helped ? 5 : 1,
          resolution_notes: fbNotes.trim() || undefined,
          query_text: q.trim() || "",
          helped,
        };

        await createTicketFeedback(tfPayload);
      } catch {
        // Ignore ticket feedback persistence failures in this UI flow.
      }

      // on success: clear notes and hide
      setFbNotes("");
      setFbNotesVisible(false);
      setFbSaved(true);
    } catch (err: unknown) {
      setFbError(formatApiError(err));
    } finally {
      setFbSubmitting(false);
    }
  }

  const tryExamples = [
    "password reset doesn't work",
    "vpn auth_failed",
    "mfa codes invalid",
    "outlook keeps asking for password",
  ];
  const responseData = response && !isAskEchoError(response) ? response : null;
  const responseMode = responseData?.mode ?? "unknown";
  const responseConfidence =
    responseData?.kb_confidence ?? responseData?.references?.[0]?.confidence;
  const responseTopTicket =
    responseData?.references?.[0]?.ticket_id ?? responseData?.suggested_tickets?.[0]?.id ?? null;
  const responseSourceCount =
    (responseData?.references?.length ?? 0) + (responseData?.kb_evidence?.length ?? 0);

  return (
    <div className="ask-echo-shell">
      <div className="ask-echo">
        <div className="ask-echo__hero">
          <header className="ask-echo__header">
            <div>
              <h1 className="ask-echo__title">Ask Echo</h1>
              <p className="ask-echo__subtitle">
                Ask a question to search resolved tickets and get a confident, grounded answer.
              </p>
              <p className="ask-echo__lede">
                Echo remembers what worked before and turns support history into next-step guidance.
              </p>
              <div className="ask-echo__hero-chips" aria-label="Ask Echo capabilities">
                <span className="ask-echo__hero-chip">Ticket intelligence</span>
                <span className="ask-echo__hero-chip">KB support</span>
                <span className="ask-echo__hero-chip">Feedback loop</span>
              </div>
            </div>
          </header>

          <div className="ask-echo__command-intro">
            <span className="ask-echo__command-label">Search resolved tickets, reusable snippets, and KB evidence</span>
            <span className="ask-echo__command-hint">Press Enter to submit</span>
          </div>

          <form className="ask-echo__command" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              className="op-input ask-echo__input"
              aria-label="Ask Echo question"
              placeholder="Ask Echo about a ticket pattern, outage, or known fix"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <button
              type="submit"
              className="op-button op-button--primary ask-echo__submit"
              disabled={!canSubmit}
            >
              {loading ? "Thinking..." : "Ask Echo"}
            </button>
          </form>
        </div>

        {!q.trim() && !response && (
          <div className="ask-echo__empty">
            <div className="ask-echo__card ask-echo__empty-card">
              <div className="ask-echo__empty-title">Start with a support question</div>
              <p className="ask-echo__empty-copy">
                Echo will search past tickets and supporting references, then return a grounded answer you can verify.
              </p>
            </div>
            <div className="ask-echo__examples">
              <span className="ask-echo__examples-label">Try an example</span>
              {tryExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="operator-pill"
                  onClick={() => {
                    setQ(example);
                    setResponse(null);
                    setErrorInfo(null);
                    setShowErrorDetails(false);
                    try {
                      inputRef.current?.focus();
                    } catch {
                      // Ignore focus failures when the input is unavailable.
                    }
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="ask-echo__loading-card" role="status" aria-live="polite">
            <div className="ask-echo__spinner" />
            <div>
              <div className="ask-echo__loading-title">Thinking…</div>
              <div className="ask-echo__loading-sub">Searching tickets and snippets.</div>
            </div>
          </div>
        )}

        {response && isAskEchoError(response) && errorInfo && (
          <div className="ask-echo__error">
            <div className="ask-echo__error-title">{errorInfo.headline}</div>
            <div className="ask-echo__error-message">{errorInfo.guidance}</div>
            <div className="ask-echo__error-actions">
              <button
                type="button"
                className="op-button op-button--primary"
                onClick={() => askWithQuery(lastQuery || q)}
                disabled={loading || !(lastQuery || q).trim()}
              >
                Try again
              </button>
              <button
                type="button"
                className="ask-echo__link-button"
                onClick={() => setShowErrorDetails((prev) => !prev)}
              >
                {showErrorDetails ? "Hide details" : "Details"}
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
          </div>
        )}

        {response && !isAskEchoError(response) && (
          <div className="ask-echo__grid">
            <div className="ask-echo__stack">
              <div className="ask-echo__card ask-echo__card--answer">
                <div className="ask-echo__card-title">Answer</div>
                <div className="ask-echo__answer-header">
                  <div className="ask-echo__answer">{response.answer || "No answer returned yet."}</div>
                  <div className="ask-echo__signal-card">
                    <span className="ask-echo__signal-label">Confidence</span>
                    <strong className="ask-echo__signal-value">
                      {formatConfidencePercent(responseConfidence)}
                    </strong>
                    <span className="ask-echo__signal-note">
                      {response.answer_kind === "grounded" || response.mode === "kb_answer"
                        ? "Grounded in prior support context"
                        : "Useful guidance with lighter grounding"}
                    </span>
                  </div>
                </div>
                <div className="ask-echo__signal-grid">
                  <div className="ask-echo__signal-tile">
                    <span className="ask-echo__signal-label">Mode</span>
                    <strong>{responseMode}</strong>
                  </div>
                  <div className="ask-echo__signal-tile">
                    <span className="ask-echo__signal-label">Sources</span>
                    <strong>{responseSourceCount}</strong>
                  </div>
                  <div className="ask-echo__signal-tile">
                    <span className="ask-echo__signal-label">Top ticket</span>
                    <strong>{responseTopTicket != null ? `#${responseTopTicket}` : "None"}</strong>
                  </div>
                </div>
                <div className="ask-echo__meta ask-echo__meta--chips">
                  {response.answer_kind === "grounded" || response.mode === "kb_answer" ? (
                    <span className="ask-echo__badge">Based on your past tickets</span>
                  ) : response.answer_kind === "ungrounded" || response.mode === "general_answer" ? (
                    <span className="ask-echo__badge ask-echo__badge--warning">General guidance</span>
                  ) : (
                    <span className="ask-echo__badge">Mode: {responseMode}</span>
                  )}
                  <span className="ask-echo__badge ask-echo__badge--source">source: ask_echo</span>
                </div>
              </div>

              {response.reasoning && <AskEchoReasoningDetails reasoning={response.reasoning} />}

              <div className="ask-echo__card ask-echo__card--sources">
                <div className="ask-echo__card-header">
                  <div>
                    <div className="ask-echo__card-title">Sources</div>
                    <div className="ask-echo__card-subtitle">Open the supporting tickets behind this answer.</div>
                  </div>
                  {Array.isArray(response.references) && response.references.length > 0 && (
                    <span className="ask-echo__badge ask-echo__badge--soft">
                      {response.references.length} ticket source{response.references.length === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
                {Array.isArray(response.references) && response.references.length > 0 ? (
                  <div className="ask-echo__source-list">
                    {response.references.map((reference, index) => {
                      const matchingTicket = response.suggested_tickets.find((ticket) => ticket.id === reference.ticket_id);
                      const label =
                        matchingTicket?.title ??
                        matchingTicket?.summary ??
                        `Ticket #${reference.ticket_id}`;

                      return (
                        <button
                          key={`${reference.ticket_id}-${index}`}
                          type="button"
                          className="ask-echo__source-item"
                          onClick={() => openTicketDetail(reference.ticket_id)}
                        >
                          <span className="ask-echo__source-copy">
                            <span className="ask-echo__source-title">{label}</span>
                            <span className="ask-echo__source-id">Ticket #{reference.ticket_id}</span>
                          </span>
                          <span className="ask-echo__source-meta">
                            {typeof reference.confidence === "number" && (
                              <span className="ask-echo__badge ask-echo__badge--soft">
                                Confidence {reference.confidence.toFixed(2)}
                              </span>
                            )}
                            <span className="ask-echo__source-arrow" aria-hidden="true">View ticket</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : Array.isArray(response.suggested_tickets) && response.suggested_tickets.length > 0 ? (
                  <div className="ask-echo__source-list">
                    {response.suggested_tickets.slice(0, 5).map((ticket) => (
                      <button
                        key={ticket.id}
                        type="button"
                        className="ask-echo__source-item"
                        onClick={() => openTicketDetail(ticket.id)}
                      >
                        <span className="ask-echo__source-copy">
                          <span className="ask-echo__source-title">{ticket.title ?? ticket.summary ?? `Ticket #${ticket.id}`}</span>
                          <span className="ask-echo__source-id">Ticket #{ticket.id}</span>
                        </span>
                        <span className="ask-echo__source-arrow" aria-hidden="true">View ticket</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="state-panel">No ticket sources were attached to this answer.</div>
                )}
              </div>

              <div className="ask-echo__card">
                <div className="ask-echo__card-header">
                  <div>
                    <div className="ask-echo__card-title">Knowledge Base</div>
                    <div className="ask-echo__card-subtitle">Evidence Echo used to shape this answer.</div>
                  </div>
                  {Array.isArray(response.kb_evidence) && response.kb_evidence.length > 0 && (
                    <span className="ask-echo__badge ask-echo__badge--soft">
                      {response.kb_evidence.length} source{response.kb_evidence.length === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
                {Array.isArray(response.kb_evidence) && response.kb_evidence.length > 0 ? (
                  <div className="snippet-list">
                    {response.kb_evidence.slice(0, 5).map((entry) => (
                      <div key={String(entry.entry_id)} className="snippet-item">
                        <div className="snippet-item__title">
                          <span>{entry.title}</span>
                          {typeof entry.score === "number" && (
                            <span className="ask-echo__badge ask-echo__badge--soft">{entry.score.toFixed(2)}</span>
                          )}
                        </div>
                        <div className="snippet-item__meta">
                          <span className="ask-echo__badge ask-echo__badge--kb">{entry.source_system || "seed_kb"}</span>
                          {entry.source_url ? (
                            <a className="ask-echo__kb-link" href={entry.source_url} target="_blank" rel="noreferrer">
                              Open source
                            </a>
                          ) : (
                            <span className="ask-echo__kb-link ask-echo__kb-link--muted">No link</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="state-panel">No knowledge base matches for this query yet.</div>
                )}
              </div>

              <div className="ask-echo__card">
                <div className="ask-echo__card-header">
                  <div>
                    <div className="ask-echo__card-title">Suggested snippets</div>
                    <div className="ask-echo__card-subtitle">Relevant excerpts from previous support work.</div>
                  </div>
                  {Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0 && (
                    <span className="ask-echo__badge ask-echo__badge--soft">
                      {response.suggested_snippets.length} match{response.suggested_snippets.length === 1 ? "" : "es"}
                    </span>
                  )}
                </div>
                {Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0 ? (
                  <div className="snippet-list">
                    {response.suggested_snippets.slice(0, 5).map((s) => (
                      <div key={String(s.id)} className="snippet-item">
                        <div className="snippet-item__title">
                          <span>{s.title}</span>
                          {typeof s.echo_score === "number" && (
                            <span className="ask-echo__badge ask-echo__badge--soft">{s.echo_score.toFixed(2)}</span>
                          )}
                        </div>
                        {s.summary && <div className="snippet-item__meta">{s.summary}</div>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="state-panel">No snippets returned yet.</div>
                )}
              </div>

              <div className="ask-echo__card ask-echo__card--feedback">
                <div className="ask-echo__card-header">
                  <div>
                    <div className="ask-echo__card-title">Feedback</div>
                    <div className="ask-echo__card-subtitle">Train Echo with a quick thumbs-up or a correction.</div>
                  </div>
                  {fbSaved && <span className="ask-echo__badge ask-echo__badge--success">Saved</span>}
                </div>
                <div className="ask-echo__feedback-row">
                  <span className="ask-echo__feedback-question">Was this helpful?</span>
                  <div className="ask-echo__feedback-actions">
                    <button
                      type="button"
                      onClick={() => submitFeedback(true)}
                      disabled={fbSubmitting || fbSaved}
                      className="op-button op-button--primary ask-echo__feedback-button"
                    >
                      👍 Yes
                    </button>
                    <button
                      type="button"
                      onClick={() => setFbNotesVisible(true)}
                      disabled={fbSubmitting || fbSaved}
                      className="op-button op-button--danger ask-echo__feedback-button"
                    >
                      👎 No
                    </button>
                  </div>
                </div>

                {fbNotesVisible && (
                  <div className="ask-echo__feedback-panel">
                    <textarea
                      rows={3}
                      className="op-input ask-echo__feedback-textarea"
                      placeholder="What went wrong or what did you do to resolve it?"
                      value={fbNotes}
                      onChange={(e) => setFbNotes(e.target.value)}
                    />
                    <div className="ask-echo__feedback-panel-actions">
                      <button
                        type="button"
                        className="op-button op-button--ghost"
                        onClick={() => submitFeedback(false)}
                        disabled={fbSubmitting}
                      >
                        Submit feedback
                      </button>
                      <button
                        type="button"
                        className="op-button op-button--ghost"
                        onClick={() => {
                          setFbNotesVisible(false);
                          setFbNotes("");
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                    {fbError && <div className="ask-echo__feedback-error">{fbError}</div>}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {!loading && !response && !!lastQuery.trim() && (
          <div className="ask-echo__error">
            <div className="ask-echo__error-title">Request failed</div>
            <div className="ask-echo__error-message">
              No response was returned. Please try again.
            </div>
            <div className="ask-echo__error-actions">
              <button
                type="button"
                className="op-button op-button--primary"
                onClick={() => askWithQuery(lastQuery || q)}
                disabled={loading || !(lastQuery || q).trim()}
              >
                Try again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
