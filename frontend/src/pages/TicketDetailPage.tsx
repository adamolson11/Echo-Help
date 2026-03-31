import { useEffect, useState } from "react";
import { formatApiError } from "../api/client";
import { getTicketById, listTicketFeedback } from "../api/endpoints";
import type { Ticket, TicketFeedbackRead } from "../api/types";
import { navigateToConsole } from "../appRoutes";

function formatDate(value?: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function pickResolution(feedback: TicketFeedbackRead[]): string | null {
  const resolution = feedback.find(
    (item) => typeof item.resolution_notes === "string" && item.resolution_notes.trim().length > 0,
  )?.resolution_notes;
  return resolution?.trim() || null;
}

export default function TicketDetailPage(props: { ticketId: number }) {
  const { ticketId } = props;
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [feedback, setFeedback] = useState<TicketFeedbackRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    async function loadTicket() {
      setLoading(true);
      setError(null);

      try {
        const [ticketData, feedbackData] = await Promise.all([
          getTicketById(ticketId, controller.signal),
          listTicketFeedback(ticketId, controller.signal),
        ]);

        if (cancelled) return;
        setTicket(ticketData);
        setFeedback(Array.isArray(feedbackData) ? feedbackData : []);
      } catch (err) {
        if (cancelled) return;
        setError(formatApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadTicket();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [ticketId]);

  const description = ticket?.description?.trim() || ticket?.body_md?.trim() || "No description provided.";
  const resolution = pickResolution(feedback);

  return (
    <div className="ticket-detail-page">
      <div className="ticket-detail-page__toolbar">
        <button
          type="button"
          className="ticket-detail-page__back"
          onClick={() => navigateToConsole("ask")}
        >
          Back to Ask Echo
        </button>
      </div>

      {loading && <div className="ticket-detail-page__state">Loading ticket #{ticketId}…</div>}

      {!loading && error && (
        <div className="ticket-detail-page__error">
          <div className="ticket-detail-page__error-title">Could not load ticket</div>
          <div>{error}</div>
        </div>
      )}

      {!loading && !error && ticket && (
        <div className="ticket-detail-page__stack">
          <section className="ticket-detail-page__section ticket-detail-page__section--hero">
            <div className="ticket-detail-page__eyebrow">Ticket #{ticket.id}</div>
            <h1 className="ticket-detail-page__title">{ticket.summary || ticket.external_key}</h1>
            <div className="ticket-detail-page__meta">
              <span className="ticket-detail-page__pill">{ticket.external_key}</span>
              <span className="ticket-detail-page__pill">{ticket.source} · {ticket.project_key}</span>
              <span className="ticket-detail-page__pill">Status: {ticket.status}</span>
              {ticket.priority && <span className="ticket-detail-page__pill">Priority: {ticket.priority}</span>}
              {ticket.updated_at && <span className="ticket-detail-page__pill">Updated: {formatDate(ticket.updated_at)}</span>}
            </div>
          </section>

          <section className="ticket-detail-page__section">
            <div className="ticket-detail-page__section-title">Description</div>
            <div className="ticket-detail-page__copy">{description}</div>
          </section>

          {resolution && (
            <section className="ticket-detail-page__section">
              <div className="ticket-detail-page__section-title">Resolution notes</div>
              <div className="ticket-detail-page__copy">{resolution}</div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}