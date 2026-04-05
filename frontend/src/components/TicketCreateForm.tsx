import { useState } from "react";
import { formatApiError } from "../api/client";
import { createTicket } from "../api/endpoints";
import { navigateToTicket } from "../appRoutes";

const PRIORITY_OPTIONS = ["low", "medium", "high"] as const;

export default function TicketCreateForm() {
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState("manual");
  const [projectKey, setProjectKey] = useState("IT");
  const [priority, setPriority] = useState<(typeof PRIORITY_OPTIONS)[number]>("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const ticket = await createTicket({
        summary,
        description,
        source,
        project_key: projectKey,
        priority,
      });
      navigateToTicket(ticket.id);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="rounded-xl border border-slate-800 bg-slate-900/40 p-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Create Ticket</h3>
          <p className="mt-1 text-xs text-slate-400">Capture a new issue manually, then jump straight to the saved ticket.</p>
        </div>
        <div className="text-xs text-slate-500">Status: open</div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-200 sm:col-span-2">
          Summary
          <input
            type="text"
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
            placeholder="Example: Customer cannot complete MFA setup"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            required
          />
        </label>

        <label className="block text-sm font-medium text-slate-200 sm:col-span-2">
          Description
          <textarea
            rows={5}
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
            placeholder="Capture the customer issue as reported so the ticket can be reviewed and searched later."
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
          />
        </label>

        <label className="block text-sm font-medium text-slate-200">
          Source
          <input
            type="text"
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
            value={source}
            onChange={(event) => setSource(event.target.value)}
          />
        </label>

        <label className="block text-sm font-medium text-slate-200">
          Project Key
          <input
            type="text"
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm uppercase text-slate-100"
            value={projectKey}
            onChange={(event) => setProjectKey(event.target.value.toUpperCase())}
          />
        </label>

        <label className="block text-sm font-medium text-slate-200 sm:col-span-2">
          Priority
          <select
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
            value={priority}
            onChange={(event) => setPriority(event.target.value as (typeof PRIORITY_OPTIONS)[number])}
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <div className="mt-3 text-sm text-rose-300">{error}</div>}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={loading || !summary.trim() || !description.trim()}
          className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium text-slate-50 hover:bg-indigo-400 disabled:opacity-50"
        >
          {loading ? "Creating…" : "Create Ticket"}
        </button>
        <span className="text-xs text-slate-400">Creates the ticket and opens its detail view.</span>
      </div>
    </form>
  );
}