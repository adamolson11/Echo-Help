import { useEffect, useState, useCallback } from "react";

export interface AskEchoFeedbackRow {
  id: number;
  ticket_id: number;
  rating: number;
  helped: boolean | null;
  resolution_notes?: string | null;
  query_text?: string | null;
  created_at: string;
}

const LIMIT = 100;

export default function AskEchoFeedbackPanel() {
  const [rows, setRows] = useState<AskEchoFeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [helpedFilter, setHelpedFilter] = useState<"all" | "yes" | "no">("all");

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/insights/ask-echo-feedback?limit=${LIMIT}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRows(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to load feedback rows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    // initial load
    fetchRows();

    // poll every 10s
    const id = window.setInterval(() => {
      if (!cancelled) fetchRows();
    }, 10_000);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [fetchRows]);

  const filtered = rows.filter((r) => {
    if (helpedFilter === "all") return true;
    if (helpedFilter === "yes") return r.helped === true;
    return r.helped === false;
  });

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-100">Ask Echo Feedback</h2>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 text-xs">
            <button onClick={() => setHelpedFilter("all")} className={`px-2 py-1 rounded ${helpedFilter === "all" ? "bg-indigo-600" : "bg-slate-800"}`}>All</button>
            <button onClick={() => setHelpedFilter("yes")} className={`px-2 py-1 rounded ${helpedFilter === "yes" ? "bg-emerald-600" : "bg-slate-800"}`}>Helpful</button>
            <button onClick={() => setHelpedFilter("no")} className={`px-2 py-1 rounded ${helpedFilter === "no" ? "bg-rose-600" : "bg-slate-800"}`}>Not helpful</button>
          </div>
          <div>
            <button
              type="button"
              onClick={() => fetchRows()}
              disabled={loading}
              className="text-xs border border-slate-600 px-2 py-1 rounded hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
      </div>

      {loading && <div className="text-xs text-slate-400">Loading feedback…</div>}
      {error && <div className="text-xs text-rose-400">Failed to load feedback: {error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-xs text-slate-500">No Ask Echo feedback yet.</div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="max-h-72 overflow-y-auto text-xs">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-slate-900/80 text-slate-400">
              <tr>
                <th className="text-left py-1 pr-2">Time</th>
                <th className="text-left py-1 pr-2">Query</th>
                <th className="text-left py-1 pr-2">Helped</th>
                <th className="text-left py-1 pr-2">What worked</th>
                <th className="text-left py-1 pr-2">Ticket</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const d = new Date(r.created_at);
                const time = isNaN(d.getTime()) ? r.created_at : d.toLocaleString();
                return (
                  <tr key={r.id} className="border-t border-slate-800/80">
                    <td className="py-1 pr-2 align-top text-slate-300">{time}</td>
                    <td className="py-1 pr-2 align-top text-slate-100 truncate max-w-xs" title={r.query_text || ""}>{r.query_text}</td>
                    <td className="py-1 pr-2 align-top">
                      {r.helped ? <span className="text-emerald-300">Yes</span> : <span className="text-rose-300">No</span>}
                    </td>
                    <td className="py-1 pr-2 align-top text-slate-200">{r.resolution_notes ?? "—"}</td>
                      <td className="py-1 pr-2 align-top text-slate-300">
                        {r.ticket_id ? (
                          <button
                            type="button"
                            onClick={() => {
                              try {
                                const ev = new CustomEvent("echo-select-ticket", { detail: { ticketId: r.ticket_id, ticket_id: r.ticket_id } });
                                window.dispatchEvent(ev);
                              } catch (err) {
                                // ignore
                              }
                            }}
                            className="underline text-indigo-300 hover:text-indigo-200 text-xs"
                          >
                            {r.ticket_id}
                          </button>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
