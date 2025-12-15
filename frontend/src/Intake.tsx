import { useState } from "react";

interface SuggestedTicket {
  id: number;
  external_key: string;
  summary: string;
  description: string;
  status: string;
  priority?: string;
  created_at?: string;
  similarity: number;
}

interface IntakeResponse {
  query: string;
  suggested_tickets: SuggestedTicket[];
  predicted_category?: string | null;
  predicted_subcategory?: string | null;
}

export default function Intake() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<IntakeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ [ticketId: number]: number }>({});
  const [thanks, setThanks] = useState<{ [ticketId: number]: boolean }>({});

  const handleAnalyze = async () => {
    setLoading(true);
    setResults(null);
    setThanks({});
    try {
      const res = await fetch("/api/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      setResults(await res.json());
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (ticketId: number, rating: number) => {
    setFeedback((f) => ({ ...f, [ticketId]: rating }));
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket_id: ticketId, query_text: text, rating }),
    });
    setThanks((t) => ({ ...t, [ticketId]: true }));
  };

  return (
    <div>
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <label className="block text-sm font-medium text-slate-200">Describe the customer issue</label>
        <p className="mt-1 text-xs text-slate-400">
          Paste the request as-is; this tool finds similar past tickets.
        </p>
        <textarea
          rows={4}
          className="mt-3 w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
          placeholder="Example: User cannot reset password; SSO loop; MFA prompt fails…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading || !text.trim()}
            className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium text-slate-50 hover:bg-indigo-400 disabled:opacity-50"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
          <span className="text-xs text-slate-400">Returns top similar tickets + similarity</span>
        </div>
      </div>

      {results && (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Suggested Tickets</h3>
            <div className="text-xs text-slate-400">
              Query length: <span className="text-slate-200">{results.query?.length ?? 0}</span>
            </div>
          </div>

          {results.suggested_tickets.length === 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
              No matches found.
            </div>
          )}

          <div className="space-y-3">
            {results.suggested_tickets.map((t) => (
              <div key={t.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="text-sm font-semibold text-slate-100">{t.summary}</div>
                    <div className="text-xs text-slate-400">{t.external_key}</div>
                  </div>
                  <div className="text-xs text-slate-300">
                    Similarity: <span className="font-semibold text-slate-50">{Math.round(t.similarity * 100)}%</span>
                  </div>
                </div>

                <div className="mt-2 text-sm text-slate-200 whitespace-pre-wrap">{t.description}</div>

                <div className="mt-2 text-xs text-slate-400">
                  Status: <span className="text-slate-200">{t.status}</span> • Priority:{" "}
                  <span className="text-slate-200">{t.priority || "-"}</span>
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <span className="text-xs text-slate-300">Match quality:</span>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      disabled={!!thanks[t.id]}
                      onClick={() => handleFeedback(t.id, star)}
                      className={
                        "rounded-md border px-2 py-1 text-xs transition " +
                        (feedback[t.id] === star
                          ? "border-indigo-400 bg-indigo-500/20 text-slate-50"
                          : "border-slate-700 bg-slate-950/30 text-slate-300 hover:border-slate-600")
                      }
                    >
                      {star}
                    </button>
                  ))}
                  {thanks[t.id] && <span className="text-xs text-emerald-300">Thanks!</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
