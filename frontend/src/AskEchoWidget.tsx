import { useState, useEffect, useRef } from "react";
import AskEchoReasoningDetails from "./components/AskEchoReasoning";
import { ApiError, formatApiError } from "./api/client";
import {
  createTicketFeedback,
  postAskEcho,
  postAskEchoFeedback,
  postSnippetFeedback,
} from "./api/endpoints";
import type { AskEchoOutcome, AskEchoRecommendation, AskEchoResponse } from "./api/types";
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
  return typeof (r as any)?.error === "string";
}

function openTicketDetail(ticketId: number) {
  navigateToTicket(ticketId);
}

const OUTCOME_LABELS: Record<AskEchoOutcome, string> = {
  resolved: "Resolved",
  partially_resolved: "Partially resolved",
  not_resolved: "Not resolved",
  needs_escalation: "Needs escalation",
};

const RECOMMENDATION_SOURCE_LABELS: Record<AskEchoRecommendation["source"]["kind"], string> = {
  ticket: "Past ticket",
  snippet: "Saved step",
  kb: "KB article",
  general: "Fallback",
};

function mapOutcomeToHelped(outcome: AskEchoOutcome): boolean {
  return outcome === "resolved" || outcome === "partially_resolved";
}

function getRecommendationSourceHint(recommendation: AskEchoRecommendation): string {
  switch (recommendation.source.kind) {
    case "ticket":
      return "Based on the closest past ticket Echo found.";
    case "snippet":
      return "Based on a saved step sequence that matched this issue.";
    case "kb":
      return "Based on a supporting knowledge-base article.";
    default:
      return "Use this when Echo found weaker evidence and you need a safe next move.";
  }
}

function pickFeedbackTicketId(
  response: AskEchoResponse,
  recommendation?: AskEchoRecommendation | null,
): number | null {
  const sourceTicketId = recommendation?.source.ticket_id;
  if (typeof sourceTicketId === "number") return sourceTicketId;

  if (Array.isArray(response.references) && response.references.length > 0) {
    return response.references[0].ticket_id ?? null;
  }

  if (Array.isArray(response.suggested_tickets) && response.suggested_tickets.length > 0) {
    return response.suggested_tickets[0]?.id ?? null;
  }

  if (Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0) {
    return response.suggested_snippets[0]?.ticket_id ?? null;
  }

  return null;
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
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<string | null>(null);
  const [selectedOutcome, setSelectedOutcome] = useState<AskEchoOutcome | null>(null);
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [reusableLearning, setReusableLearning] = useState("");
  const [selectedFeedbackTicketId, setSelectedFeedbackTicketId] = useState<number | null>(null);

  function logDevDebug(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    // eslint-disable-next-line no-console
    console.debug("[ask-echo]", { event, ...payload });
  }

  function logDevError(event: string, payload: Record<string, unknown>) {
    if (!import.meta.env.DEV) return;
    // eslint-disable-next-line no-console
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

  // when a new Ask Echo response arrives, auto-select a sensible ticket id for feedback
  useEffect(() => {
    if (!response || isAskEchoError(response)) {
      setSelectedFeedbackTicketId(null);
      setSelectedRecommendationId(null);
      setSelectedOutcome(null);
      setOutcomeNotes("");
      setReusableLearning("");
      setFbSaved(false);
      return;
    }

    setFbSaved(false);
    setSelectedOutcome(null);
    setOutcomeNotes("");
    setReusableLearning("");

    const defaultRecommendation = response.flywheel?.recommendations?.[0] ?? null;
    setSelectedRecommendationId(defaultRecommendation?.id ?? null);
    setSelectedFeedbackTicketId(pickFeedbackTicketId(response, defaultRecommendation));
  }, [response]);

  const responseData = response && !isAskEchoError(response) ? response : null;
  const flywheel = responseData?.flywheel ?? null;
  const recommendations = flywheel?.recommendations ?? [];
  const selectedRecommendation =
    recommendations.find((recommendation) => recommendation.id === selectedRecommendationId) ??
    recommendations[0] ??
    null;

  useEffect(() => {
    if (!responseData) return;
    setSelectedFeedbackTicketId(pickFeedbackTicketId(responseData, selectedRecommendation));
  }, [responseData, selectedRecommendation]);

  async function submitFeedback() {
    setFbError(null);
    setFbSubmitting(true);
    try {
      if (!responseData) {
        throw new Error("No Ask Echo response to attach feedback to.");
      }

      if (!selectedRecommendation) {
        throw new Error("Select one recommended next action before saving the loop.");
      }

      if (!selectedOutcome) {
        throw new Error("Capture the outcome before saving the loop.");
      }

      if (!reusableLearning.trim()) {
        throw new Error("Add the reusable learning before saving the loop.");
      }

      const askEchoLogId: number | null = responseData.ask_echo_log_id ?? null;
      if (!askEchoLogId) {
        throw new Error("Missing Ask Echo log id; please ask again.");
      }

      const helped = mapOutcomeToHelped(selectedOutcome);

      await postAskEchoFeedback({
        ask_echo_log_id: askEchoLogId,
        helped,
        notes: outcomeNotes.trim() || reusableLearning.trim(),
        selected_recommendation_id: selectedRecommendation.id,
        selected_recommendation_title: selectedRecommendation.title,
        outcome: selectedOutcome,
        outcome_notes: outcomeNotes.trim() || null,
        reusable_learning: reusableLearning.trim(),
      });

      let ticketId: number | undefined = undefined;
      if (selectedFeedbackTicketId) ticketId = selectedFeedbackTicketId as number;
      const snippetId =
        selectedRecommendation.source.kind === "snippet"
          ? selectedRecommendation.source.snippet_id ?? undefined
          : undefined;

      if ((!ticketId || ticketId === null) && responseData) {
        if (Array.isArray(responseData.references) && responseData.references.length > 0) {
          ticketId = responseData.references[0].ticket_id;
        }
        if ((!ticketId || ticketId === null) && Array.isArray(responseData.suggested_tickets) && responseData.suggested_tickets.length > 0) {
          const r0 = responseData.suggested_tickets[0];
          ticketId = r0?.id ?? undefined;
        }
        if ((!ticketId || ticketId === null) && Array.isArray(responseData.suggested_snippets) && responseData.suggested_snippets.length > 0) {
          const s0 = responseData.suggested_snippets[0];
          if (s0 && s0.ticket_id) ticketId = s0.ticket_id;
        }
      }

      if (ticketId) setSelectedFeedbackTicketId(ticketId as number);

      if ((!ticketId && ticketId !== 0) && !snippetId) {
        setOutcomeNotes("");
        setReusableLearning("");
        setFbSaved(true);
        return;
      }

      const payload: any = {
        helped,
        ticket_id: ticketId,
        snippet_id: snippetId,
        source: "ask_echo",
        notes: reusableLearning.trim(),
        resolution_notes: outcomeNotes.trim() || reusableLearning.trim(),
      };
      if (q && q.trim().length > 0) payload.query_text = q.trim();

      if (ticketId || snippetId) {
        await postSnippetFeedback(payload);
      }

      try {
        if (ticketId) {
          const tfPayload: any = {
          ticket_id: ticketId,
          rating: helped ? 5 : 1,
          resolution_notes: outcomeNotes.trim() || reusableLearning.trim() || undefined,
          query_text: q.trim() || "",
          helped: helped,
          ai_summary: reusableLearning.trim() || undefined,
        };

          await createTicketFeedback(tfPayload);
        }
      } catch (e) {
        // ignore ticket-feedback errors in the UI flow
      }

      setFbSaved(true);
    } catch (err: any) {
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
  const responseMode = responseData?.mode ?? "unknown";
  const responseConfidence =
    responseData?.kb_confidence ?? responseData?.references?.[0]?.confidence;
  const responseTopTicket =
    responseData?.references?.[0]?.ticket_id ?? responseData?.suggested_tickets?.[0]?.id ?? null;
  const responseSourceCount =
    (responseData?.references?.length ?? 0) + (responseData?.kb_evidence?.length ?? 0);
  const currentStage = fbSaved
    ? "learning_captured"
    : selectedOutcome
      ? "outcome_recorded"
      : selectedRecommendation
        ? "action_selected"
        : flywheel?.state.current_stage ?? "recommendations_ready";
  const saveDisabled =
    fbSubmitting ||
    fbSaved ||
    !selectedRecommendation ||
    !selectedOutcome ||
    !reusableLearning.trim();
  const saveHelperText = fbSaved
    ? "Saved with this Ask Echo run so the next operator can reuse what you learned."
    : !selectedRecommendation
      ? "Pick one next action to start the loop."
      : !selectedOutcome
        ? "Choose the outcome after trying the selected action."
        : !reusableLearning.trim()
          ? "Add what Echo should remember next time to enable save."
          : "Saving learning stores your notes with this Ask Echo run for future operators.";
  const stages = [
    { id: "recommendations_ready", label: "Review result" },
    { id: "action_selected", label: "Choose action" },
    { id: "outcome_recorded", label: "Capture outcome" },
    { id: "learning_captured", label: "Save learning" },
  ] as const;

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
                <span className="ask-echo__hero-chip">Flywheel wedge</span>
              </div>
            </div>
          </header>

          <div className="ask-echo__command">
            <input
              ref={inputRef}
              className="op-input ask-echo__input"
              placeholder="Ask Echo a question about tickets..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
            />
            <button
              type="button"
              className="op-button op-button--primary ask-echo__submit"
              onClick={ask}
              disabled={loading}
            >
              {loading ? "Thinking..." : "Ask Echo"}
            </button>
          </div>
        </div>

        {!q.trim() && !response && (
          <div className="ask-echo__empty">
            <div className="ask-echo__card ask-echo__empty-card">
              Ask a question to search resolved tickets.
            </div>
            <div className="ask-echo__examples">
              <span>Try an example:</span>
              {tryExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="operator-pill"
                  onClick={() => {
                    setQ(example);
                    setResponse(null);
                    try {
                      inputRef.current?.focus();
                    } catch {
                      // no-op
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
          <div className="ask-echo__loading-card">
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
                <div className="ask-echo__card-title">1. What Echo found</div>
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
                    <span className="ask-echo__badge">Grounded in past support work</span>
                  ) : response.answer_kind === "ungrounded" || response.mode === "general_answer" ? (
                    <span className="ask-echo__badge ask-echo__badge--warning">Fallback guidance</span>
                  ) : (
                    <span className="ask-echo__badge">Mode: {responseMode}</span>
                  )}
                </div>
                <div className="ask-echo__flow-callout">
                  Next: pick one of the three actions below. Echo will load the selected path and let you record what happened.
                </div>
              </div>

              <div className="ask-echo__card ask-echo__card--flywheel">
                <div className="ask-echo__card-header">
                  <div>
                    <div className="ask-echo__card-title">2. Pick your next action</div>
                    <div className="ask-echo__card-subtitle">
                      Choose one card. The selected action becomes the step-by-step path below.
                    </div>
                  </div>
                  <span className="ask-echo__badge ask-echo__badge--soft">
                    {recommendations.length} recommendation{recommendations.length === 1 ? "" : "s"}
                  </span>
                </div>

                <div className="ask-echo__stage-strip" aria-label="Flywheel stages">
                  {stages.map((stage, index) => {
                    const isActive = currentStage === stage.id;
                    const isComplete = stages.findIndex((item) => item.id === currentStage) > index;
                    return (
                      <div
                        key={stage.id}
                        className={`ask-echo__stage ${isActive ? "ask-echo__stage--active" : ""} ${isComplete ? "ask-echo__stage--complete" : ""}`.trim()}
                      >
                        <span className="ask-echo__stage-number">{index + 1}</span>
                        <span className="ask-echo__stage-label">{stage.label}</span>
                      </div>
                    );
                  })}
                </div>

                <div className="ask-echo__recommendation-grid">
                  {recommendations.map((recommendation, index) => {
                    const selected = recommendation.id === selectedRecommendation?.id;
                    return (
                      <button
                        key={recommendation.id}
                        type="button"
                        className={`ask-echo__recommendation-card ${selected ? "ask-echo__recommendation-card--selected" : ""}`.trim()}
                        onClick={() => {
                          setSelectedRecommendationId(recommendation.id);
                          setFbSaved(false);
                        }}
                        aria-pressed={selected}
                      >
                        <div className="ask-echo__recommendation-card-header">
                          <span className="ask-echo__recommendation-rank">Action {index + 1}</span>
                          {selected ? (
                            <span className="ask-echo__badge ask-echo__badge--success">Selected</span>
                          ) : null}
                        </div>
                        <div className="ask-echo__recommendation-meta-row">
                          <span className="ask-echo__badge ask-echo__badge--soft">
                            {RECOMMENDATION_SOURCE_LABELS[recommendation.source.kind]}
                          </span>
                          {typeof recommendation.confidence === "number" && (
                            <span className="ask-echo__badge ask-echo__badge--soft">
                              {formatConfidencePercent(recommendation.confidence)}
                            </span>
                          )}
                        </div>
                        <div className="ask-echo__recommendation-title">{recommendation.title}</div>
                        <div className="ask-echo__recommendation-summary">{recommendation.summary}</div>
                        <div className="ask-echo__recommendation-rationale">{getRecommendationSourceHint(recommendation)}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {selectedRecommendation && (
                <div className="ask-echo__card ask-echo__card--action-plan">
                  <div className="ask-echo__card-header">
                    <div>
                      <div className="ask-echo__card-title">3. Run this action</div>
                      <div className="ask-echo__card-subtitle">
                        Follow these steps in order, then record the result below.
                      </div>
                    </div>
                    <span className="ask-echo__badge ask-echo__badge--source">
                      Selected path
                    </span>
                  </div>

                  <div className="ask-echo__selected-action-caption">
                    {RECOMMENDATION_SOURCE_LABELS[selectedRecommendation.source.kind]}: {selectedRecommendation.source.label}
                  </div>
                  <div className="ask-echo__selected-action-title">{selectedRecommendation.title}</div>
                  <ol className="ask-echo__steps-list">
                    {selectedRecommendation.steps.map((step, index) => (
                      <li key={`${selectedRecommendation.id}-${index}`} className="ask-echo__step">
                        {step}
                      </li>
                    ))}
                  </ol>

                  <div className="ask-echo__action-toolbar">
                    {selectedRecommendation.source.ticket_id ? (
                      <button
                        type="button"
                        className="op-button op-button--ghost"
                        onClick={() => openTicketDetail(selectedRecommendation.source.ticket_id as number)}
                      >
                        Open supporting ticket
                      </button>
                    ) : null}
                    {selectedRecommendation.source.source_url ? (
                      <a
                        className="ask-echo__kb-link"
                        href={selectedRecommendation.source.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open KB source
                      </a>
                    ) : null}
                  </div>
                </div>
              )}

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
                    <div className="ask-echo__card-title">4. Record the result</div>
                    <div className="ask-echo__card-subtitle">Capture what happened, then save what Echo should remember next time.</div>
                  </div>
                  {fbSaved && <span className="ask-echo__badge ask-echo__badge--success">Saved</span>}
                </div>
                <div className="ask-echo__feedback-row">
                  <span className="ask-echo__feedback-question">What happened after you tried this selected action?</span>
                </div>

                <div className="ask-echo__outcome-grid" role="group" aria-label="Outcome options">
                  {(flywheel?.outcome_options ?? []).map((outcome) => {
                    const selected = selectedOutcome === outcome;
                    return (
                      <button
                        key={outcome}
                        type="button"
                        className={`ask-echo__outcome-button ${selected ? "ask-echo__outcome-button--selected" : ""}`.trim()}
                        onClick={() => {
                          setSelectedOutcome(outcome);
                          setFbSaved(false);
                        }}
                        aria-pressed={selected}
                        disabled={fbSubmitting || fbSaved}
                      >
                        {OUTCOME_LABELS[outcome]}
                      </button>
                    );
                  })}
                </div>

                <div className="ask-echo__feedback-panel">
                  <label className="ask-echo__textarea-label" htmlFor="ask-echo-outcome-notes">
                    Outcome notes
                  </label>
                  <textarea
                    id="ask-echo-outcome-notes"
                    rows={3}
                    className="op-input ask-echo__feedback-textarea"
                    placeholder="What happened when you executed the selected action?"
                    value={outcomeNotes}
                    onChange={(e) => setOutcomeNotes(e.target.value)}
                    disabled={fbSubmitting || fbSaved}
                  />

                  <label className="ask-echo__textarea-label" htmlFor="ask-echo-reusable-learning">
                    What should Echo remember next time?
                  </label>
                  <textarea
                    id="ask-echo-reusable-learning"
                    rows={4}
                    className="op-input ask-echo__feedback-textarea"
                    placeholder={flywheel?.reusable_learning_prompt ?? "Capture what Echo should remember next time."}
                    value={reusableLearning}
                    onChange={(e) => setReusableLearning(e.target.value)}
                    disabled={fbSubmitting || fbSaved}
                  />

                  <div className="ask-echo__feedback-panel-actions">
                    <button
                      type="button"
                      className="op-button op-button--primary ask-echo__feedback-save"
                      onClick={() => submitFeedback()}
                      disabled={saveDisabled}
                    >
                      {fbSubmitting ? "Saving..." : "Save learning for next time"}
                    </button>
                    <button
                      type="button"
                      className="op-button op-button--ghost"
                      onClick={() => {
                        setSelectedOutcome(null);
                        setOutcomeNotes("");
                        setReusableLearning("");
                        setFbSaved(false);
                        setFbError(null);
                      }}
                      disabled={fbSubmitting}
                    >
                      Reset
                    </button>
                  </div>
                  <div className="ask-echo__feedback-help">{saveHelperText}</div>
                  {fbError && <div className="ask-echo__feedback-error">{fbError}</div>}
                </div>
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
