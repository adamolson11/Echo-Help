import { useState } from "react";
import { API_BASE } from "./apiConfig";

export default function AskEchoWidget() {
  const [q, setQ] = useState("");
  const [response, setResponse] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  // feedback UI state
  const [fbSubmitting, setFbSubmitting] = useState(false);
  const [fbError, setFbError] = useState<string | null>(null);
  const [fbNotesVisible, setFbNotesVisible] = useState(false);
  const [fbNotes, setFbNotes] = useState("");

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${API_BASE}/api/ask-echo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, limit: 5 }),
      });
      if (!res.ok) {
        const txt = await res.text();
        setResponse({ error: `Error: ${res.status} ${txt}` });
      } else {
        const data = await res.json();
        setResponse(data);
      }
    } catch (err: any) {
      setResponse({ error: `Request failed: ${err.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function submitFeedback(helped: boolean) {
    setFbError(null);
    setFbSubmitting(true);
    try {
      // prefer ticket_id from top result if available
      const ticketId = response?.results && response.results.length > 0 ? response.results[0].id : undefined;
      const payload: any = { helped };
      if (ticketId !== undefined) payload.ticket_id = ticketId;
      if (!helped && fbNotes.trim().length > 0) payload.notes = fbNotes.trim();

      const res = await fetch(`${API_BASE}/api/snippets/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail = body?.detail ?? `HTTP ${res.status}`;
        throw new Error(detail);
      }

      // on success: clear notes and hide
      setFbNotes("");
      setFbNotesVisible(false);
      // Optionally refresh Ask Echo answer to reflect updated KB confidence
      if (q.trim()) await ask();
    } catch (err: any) {
      setFbError(err?.message || "Feedback failed");
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
          className="rounded-md bg-emerald-500 px-3 py-2 font-medium text-slate-900"
          onClick={ask}
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask Echo"}
        </button>
      </div>

      {response && (
        <div className="mt-3">
          {response.error ? (
            <div className="text-sm text-rose-400">{response.error}</div>
          ) : (
            <>
              <div className="whitespace-pre-wrap text-sm text-slate-200">{response.answer}</div>

              <div className="mt-2 text-xs text-slate-400">
                KB-backed: {response.kb_backed ? "Yes" : "No"} · Confidence: {Math.round((response.kb_confidence ?? 0) * 100)}% · Mode: {response.mode ?? "unknown"}
              </div>

              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-slate-300">Was this helpful?</span>
                <button
                  onClick={() => submitFeedback(true)}
                  disabled={fbSubmitting}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 rounded text-xs"
                >
                  👍 Yes
                </button>
                <button
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
