import React, { useState } from "react";
import { formatApiError } from "./api/client";
import { createTicketFeedback } from "./api/endpoints";


interface FeedbackFormProps {
  ticketId: number | string;
  onSubmitted?: () => void;
}

export default function FeedbackForm({ ticketId, onSubmitted }: FeedbackFormProps) {
  const [helped, setHelped] = useState<boolean | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      if (helped === null) throw new Error("Please choose Yes or No.");
      await createTicketFeedback({
        ticket_id: Number(ticketId),
        query_text: "",
        rating: helped ? 5 : 1,
        helped,
        resolution_notes: notes,
      });
      setSuccess(true);
      setNotes("");
      setHelped(null);
      if (onSubmitted) onSubmitted();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="mt-2 text-emerald-400 text-xs">Thank you for your feedback!</div>
    );
  }

  return (
    <form className="mt-2 space-y-2" onSubmit={handleSubmit}>
      <div className="flex gap-2 items-center text-xs">
        <span>Did this help?</span>
        <button
          type="button"
          className={`px-2 py-1 rounded ${helped === true ? "bg-emerald-600 text-white" : "bg-slate-800 text-slate-200"}`}
          onClick={() => setHelped(true)}
          disabled={loading}
        >
          Yes
        </button>
        <button
          type="button"
          className={`px-2 py-1 rounded ${helped === false ? "bg-rose-600 text-white" : "bg-slate-800 text-slate-200"}`}
          onClick={() => setHelped(false)}
          disabled={loading}
        >
          No
        </button>
      </div>
      <textarea
        className="w-full rounded bg-slate-900 border border-slate-700 px-2 py-1 text-xs text-slate-100"
        placeholder="What did you actually do? (optional)"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        rows={2}
        disabled={loading}
      />
      <div className="flex gap-2 items-center">
        <button
          type="submit"
          className="px-3 py-1 rounded bg-indigo-600 text-white text-xs disabled:opacity-60"
          disabled={loading || helped === null}
        >
          {loading ? "Submitting..." : "Submit Feedback"}
        </button>
        {error && <span className="text-xs text-rose-400">{error}</span>}
      </div>
    </form>
  );
}
