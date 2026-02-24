import { useState, useEffect, useRef } from "react";
import AskEchoReasoningDetails from "./components/AskEchoReasoning";
import { formatApiError } from "./api/client";
import {
  createTicketFeedback,
  postAskEcho,
  postAskEchoFeedback,
  postSnippetFeedback,
} from "./api/endpoints";
import type { AskEchoResponse } from "./api/types";

type AskEchoWidgetResponse = AskEchoResponse | { error: string };

function isAskEchoError(r: AskEchoWidgetResponse): r is { error: string } {
  return typeof (r as any)?.error === "string";
}

export default function AskEchoWidget() {
  const [q, setQ] = useState("");
  const [response, setResponse] = useState<AskEchoWidgetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  // feedback UI state
  const [fbSubmitting, setFbSubmitting] = useState(false);
  const [fbSaved, setFbSaved] = useState(false);
  const [fbError, setFbError] = useState<string | null>(null);
  const [fbNotesVisible, setFbNotesVisible] = useState(false);
  const [fbNotes, setFbNotes] = useState("");
  const [selectedFeedbackTicketId, setSelectedFeedbackTicketId] = useState<number | null>(null);

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    setResponse(null);
    setFbSaved(false);
    try {
      const data = await postAskEcho({ q, limit: 5 });
      setResponse(data);
    } catch (err: any) {
      // Preserve prior rendering behavior: store an error string on response.
      setResponse({ error: formatApiError(err) });
    } finally {
      setLoading(false);
    }
  }

  // when a new Ask Echo response arrives, auto-select a sensible ticket id for feedback
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

      const askEchoLogId: number | null = response?.ask_echo_log_id ?? null;
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
      let ticketId: number | undefined = undefined;
      if (selectedFeedbackTicketId) ticketId = selectedFeedbackTicketId as number;

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
      if (ticketId) setSelectedFeedbackTicketId(ticketId as number);

      // If there is no ticket id, we've still captured Ask Echo feedback by log id.
      // Skip snippet/ticket feedback persistence in that case.
      if (!ticketId && ticketId !== 0) {
        setFbNotes("");
        setFbNotesVisible(false);
        setFbSaved(true);
        return;
      }

      // Build payload. Backend expects `notes` for resolution notes; include `resolution_notes` and `query_text` as well for context.
      const payload: any = { helped, ticket_id: ticketId, source: "ask_echo" };
      if (!helped && fbNotes.trim().length > 0) {
        payload.notes = fbNotes.trim();
        payload.resolution_notes = fbNotes.trim();
      }
      if (q && q.trim().length > 0) payload.query_text = q.trim();

      await postSnippetFeedback(payload);

      // Also record a ticket-feedback row so Ask Echo feedback is visible in Insights.
      // Map helped -> rating (5 for helped, 1 for not helped) to satisfy TicketFeedback.rating requirement.
      try {
        const tfPayload: any = {
          ticket_id: ticketId,
          rating: helped ? 5 : 1,
          resolution_notes: fbNotes.trim() || undefined,
          query_text: q.trim() || "",
          helped: helped,
        };

        // Fire-and-forget; we don't block the UI on this.
        await createTicketFeedback(tfPayload);
      } catch (e) {
        // ignore ticket-feedback errors in the UI flow
      }

      // on success: clear notes and hide
      setFbNotes("");
      setFbNotesVisible(false);
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

        {response && isAskEchoError(response) && (
          <div className="ask-echo__error">
            <strong>Something went wrong.</strong> {response.error}
          </div>
        )}

        {response && !isAskEchoError(response) && (
          <div className="ask-echo__grid">
            <div className="ask-echo__stack">
            <div className="ask-echo__card">
              <div className="ask-echo__card-title">Answer</div>
              <div className="ask-echo__answer">{response.answer}</div>
              <div className="ask-echo__meta">
                {response.answer_kind === "grounded" || response.mode === "kb_answer" ? (
                  <span className="ask-echo__badge">Based on your past tickets</span>
                ) : response.answer_kind === "ungrounded" || response.mode === "general_answer" ? (
                  <span className="ask-echo__badge badge--warning">General guidance</span>
                ) : (
                  <span className="ask-echo__badge">Mode: {response.mode ?? "unknown"}</span>
                )}
              </div>
            </div>

            {response.reasoning && <AskEchoReasoningDetails reasoning={response.reasoning} />}

            <div className="ask-echo__card">
              <div className="ask-echo__card-title">Suggested snippets</div>
              {Array.isArray(response.suggested_snippets) && response.suggested_snippets.length > 0 ? (
                <div className="snippet-list">
                  {response.suggested_snippets.slice(0, 5).map((s) => (
                    <div key={String(s.id)} className="snippet-item">
                      <div className="snippet-item__title">
                        <span>{s.title}</span>
                        {typeof s.echo_score === "number" && (
                          <span className="ask-echo__badge">{s.echo_score.toFixed(2)}</span>
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

            <div className="ask-echo__card">
              <div className="ask-echo__card-title">Feedback</div>
              <div className="ask-echo__feedback-row">
                <span>Was this helpful?</span>
                {fbSaved && <span className="ask-echo__badge ask-echo__badge--success">Saved</span>}
                <button
                  type="button"
                  onClick={() => submitFeedback(true)}
                  disabled={fbSubmitting || fbSaved}
                  className="op-button op-button--primary"
                >
                  👍 Yes
                </button>
                <button
                  type="button"
                  onClick={() => setFbNotesVisible(true)}
                  disabled={fbSubmitting || fbSaved}
                  className="op-button op-button--danger"
                >
                  👎 No
                </button>
              </div>

              {fbNotesVisible && (
                <div className="ask-echo__meta">
                  <textarea
                    rows={3}
                    className="op-input"
                    placeholder="What went wrong or what did you do to resolve it?"
                    value={fbNotes}
                    onChange={(e) => setFbNotes(e.target.value)}
                  />
                  <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                    <button
                      type="button"
                      className="op-button op-button--ghost"
                      onClick={() => submitFeedback(false)}
                      disabled={fbSubmitting}
                    >
                      Submit
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
                  {fbError && <div className="ask-echo__meta">{fbError}</div>}
                </div>
              )}
            </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
