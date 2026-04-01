import { useState } from "react";
import { formatApiError } from "../api/client";
import { createTicket } from "../api/endpoints";
import { navigateToTicket } from "../appRoutes";

export default function TicketCreateForm() {
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = summary.trim().length >= 3 && description.trim().length >= 3 && !submitting;

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);

    try {
      const created = await createTicket({
        summary: summary.trim(),
        description: description.trim(),
        priority,
      });

      navigateToTicket(created.id);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <label className="block text-sm font-medium text-slate-200">Create ticket</label>
      <p className="mt-1 text-xs text-slate-400">Create a new ticket and open it immediately.</p>

      <div className="mt-3 space-y-3">
        <input
          className="w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
          placeholder="Summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />

        <textarea
          rows={4}
          className="w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <select
          className="rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium text-slate-50 hover:bg-indigo-400 disabled:opacity-50"
        >
          {submitting ? "Creating…" : "Create ticket"}
        </button>

        {error && <div className="text-sm text-red-300">{error}</div>}
      </div>
    </form>
  );
}
