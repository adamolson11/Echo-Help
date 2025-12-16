import { useState, useEffect } from "react";
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

  // feedback UI state
  const [fbSubmitting, setFbSubmitting] = useState(false);
  const [fbError, setFbError] = useState<string | null>(null);
  const [fbNotesVisible, setFbNotesVisible] = useState(false);
  const [fbNotes, setFbNotes] = useState("");
  const [selectedFeedbackTicketId, setSelectedFeedbackTicketId] = useState<number | null>(null);

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    setResponse(null);
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
      return;
    }

    // Prefer references (returned as { ticket_id, confidence }), then results (full tickets), then snippet.ticket_id
    let pick: number | null = null;
    if (Array.isArray(response.references) && response.references.length > 0) {
      pick = response.references[0].ticket_id ?? null;
    }
    if (!pick && Array.isArray(response.results) && response.results.length > 0) {
      const r0 = response.results[0];
      pick = r0?.id ?? null;
    }
    if (!pick && Array.isArray(response.snippets) && response.snippets.length > 0) {
      const s0 = response.snippets[0];
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
        if ((!ticketId || ticketId === null) && Array.isArray(response.results) && response.results.length > 0) {
          const r0 = response.results[0];
          ticketId = r0?.id ?? undefined;
        }
        if ((!ticketId || ticketId === null) && Array.isArray(response.snippets) && response.snippets.length > 0) {
          const s0 = response.snippets[0];
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
        if (q.trim()) await ask();
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
      // Optionally refresh Ask Echo answer to reflect updated KB confidence
      if (q.trim()) await ask();
    } catch (err: any) {
      setFbError(formatApiError(err));
    } finally {
      setFbSubmitting(false);
    }
  }

  return (
    <div className="mb-4 rounded-md bg-slate-800 p-4">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-md bg-slate-700 px-3 py-2 text-slate-100"
          placeholder="Ask Echo a question about tickets..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button
          type="button"
          className="rounded-md bg-emerald-500 px-3 py-2 font-medium text-slate-900"
          onClick={ask}
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask Echo"}
        </button>
      </div>

      <p className="text-xs text-slate-400 mt-1">
        Ask a natural-language question and get an AI-generated answer based on your tickets and knowledge base.
      </p>

      {response && (
        <div className="mt-3">
          {isAskEchoError(response) ? (
            <div className="text-sm text-rose-400">{response.error}</div>
          ) : (
            <>
              <div className="whitespace-pre-wrap text-sm text-slate-200">{response.answer}</div>

              <div className="mt-2 text-xs text-slate-400">
                {response.answer_kind === "grounded" || response.mode === "kb_answer" ? (
                  <span className="text-emerald-300">Based on your past tickets</span>
                ) : response.answer_kind === "ungrounded" || response.mode === "general_answer" ? (
                  <span className="text-amber-300">General guidance (not found in your history)</span>
                ) : (
                  <span>Mode: {response.mode ?? "unknown"}</span>
                )}
              </div>

              {response.reasoning && (
                <AskEchoReasoningDetails reasoning={response.reasoning} />
              )}

              {Array.isArray(response.references) && response.references.length > 0 && (
                <div className="mt-2 text-xs text-slate-300">
                  <div className="font-semibold text-xs">Related tickets</div>
                  <ul className="mt-1 space-y-1">
                    {response.references.map((ref, idx: number) => {
                      // try to find a matching ticket title in results
                      const ticket = response.results.find((r) => String(r.id) === String(ref.ticket_id));
                      const title = ticket ? (ticket.summary || ticket.title || `Ticket ${ref.ticket_id}`) : `Ticket ${ref.ticket_id}`;
                      return (
                        <li key={idx} className="text-[11px]">
                          <button
                            onClick={() => {
                              try {
                                // dispatch a global event that Search will listen to
                                const ev = new CustomEvent("echo-select-ticket", { detail: { ticketId: ref.ticket_id } });
                                window.dispatchEvent(ev);
                                // also scroll to the Search area for visibility
                                const el = document.querySelector("#root");
                                if (el) el.scrollIntoView({ behavior: "smooth" });
                              } catch (e) {
                                // fallback: no-op
                              }
                            }}
                            className="underline hover:text-slate-200"
                          >
                            • #{ref.ticket_id} – {title}
                            {typeof ref.confidence === "number" && (
                              <span className="text-slate-500 ml-2">({Math.round(ref.confidence * 100)}%)</span>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-slate-300">Was this helpful?</span>
                <button
                  type="button"
                  onClick={() => submitFeedback(true)}
                  disabled={fbSubmitting}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 rounded text-xs"
                >
                  👍 Yes
                </button>
                <button
                  type="button"
                  onClick={() => setFbNotesVisible(true)}
                  disabled={fbSubmitting}
                  className="px-2 py-1 bg-rose-600 hover:bg-rose-500 rounded text-xs"
                >
                  👎 No
                </button>
              </div>

              {fbNotesVisible && (
                <div className="mt-2">
                  <textarea
                    value={fbNotes}
                    onChange={(e) => setFbNotes(e.target.value)}
                    className="w-full rounded bg-slate-700 px-2 py-1 text-sm text-slate-100"
                    rows={3}
                    placeholder="What actually fixed it or why this didn't help?"
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => submitFeedback(false)}
                      disabled={fbSubmitting}
                      className="px-3 py-1 bg-rose-600 hover:bg-rose-500 rounded text-xs"
                    >
                      Submit
                    </button>
                    <button
                      onClick={() => {
                        setFbNotesVisible(false);
                        setFbNotes("");
                      }}
                      disabled={fbSubmitting}
                      className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs"
                    >
                      Cancel
                    </button>
                  </div>
                  {fbError && <div className="mt-2 text-xs text-rose-400">{fbError}</div>}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
