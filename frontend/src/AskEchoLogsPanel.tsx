import { useEffect, useState } from "react";

type AskEchoLogSummary = {
  id: number;
  query_text: string;
  ticket_id?: string | null;
  echo_score?: number | null;
  created_at?: string | null;
};

type ReasoningSnippetCandidate = {
  id: number;
  title?: string | null;
  score?: number | null;
};

type AskEchoLogDetail = {
  id: number;
  query_text: string;
  answer_text: string;
  ticket_id?: string | null;
  echo_score?: number | null;
  created_at?: string | null;
  reasoning?: {
    candidate_snippets: ReasoningSnippetCandidate[];
    chosen_snippet_ids: number[];
  };
  reasoning_notes?: string | null;
};

const LIMIT = 100;

export default function AskEchoLogsPanel() {
  const [logs, setLogs] = useState<AskEchoLogSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedLog, setSelectedLog] = useState<AskEchoLogDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadLogs() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/ask-echo/logs?limit=${LIMIT}`);
        if (!res.ok) throw new Error(`Failed to fetch logs: ${res.status}`);
        const data: AskEchoLogSummary[] = await res.json();
        if (!cancelled) setLogs(data);
      } catch (err: any) {
        if (!cancelled) setError(err.message ?? "Error loading Ask Echo logs");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadLogs();
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadLogDetail(id: number) {
    setDetailLoading(true);
    setDetailError(null);
    setSelectedLog(null);
    try {
      const res = await fetch(`/api/ask-echo/logs/${id}`);
      if (!res.ok) throw new Error(`Failed to fetch log detail: ${res.status}`);
      const data: AskEchoLogDetail = await res.json();
      setSelectedLog(data);
    } catch (err: any) {
      setDetailError(err.message ?? "Error loading log detail");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Ask Echo Query History</h2>
          <p className="mt-1 text-xs text-slate-400">
            Review past Ask Echo questions, confidence, and reasoning for each answer.
          </p>
        </div>
      </div>

      {loading && <div className="mt-3 text-xs text-slate-400">Loading Ask Echo logs…</div>}
      {error && <div className="mt-3 text-xs text-rose-400">Could not load Ask Echo logs: {error}</div>}

      {!loading && !error && logs.length === 0 && (
        <div className="mt-3 text-xs text-slate-500">No Ask Echo logs yet.</div>
      )}

      {!loading && !error && logs.length > 0 && (
        <div className="mt-3 max-h-72 overflow-y-auto text-xs">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-slate-900/80 text-slate-400">
              <tr>
                <th className="text-left py-1 pr-2">Time</th>
                <th className="text-left py-1 pr-2">Query</th>
                <th className="text-left py-1 pr-2">Ticket</th>
                <th className="text-left py-1 pr-2">EchoScore</th>
                <th className="text-left py-1 pr-2"></th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                const d = log.created_at ? new Date(log.created_at) : null;
                const time = d && !isNaN(d.getTime()) ? d.toLocaleString() : log.created_at ?? "—";
                return (
                  <tr key={log.id} className="border-t border-slate-800 hover:bg-slate-900/60">
                    <td className="py-1 pr-2 align-top text-slate-300">{time}</td>
                    <td className="py-1 pr-2 align-top text-slate-100 truncate max-w-xs" title={log.query_text}>
                      {log.query_text}
                    </td>
                    <td className="py-1 pr-2 align-top text-slate-300">{log.ticket_id ?? "—"}</td>
                    <td className="py-1 pr-2 align-top text-slate-300">
                      {typeof log.echo_score === "number" ? log.echo_score.toFixed(2) : "N/A"}
                    </td>
                    <td className="py-1 pr-2 align-top text-right">
                      <button
                        type="button"
                        className="rounded bg-slate-800 px-2 py-1 text-[11px] text-slate-100 hover:bg-slate-700"
                        onClick={() => loadLogDetail(log.id)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(detailLoading || selectedLog || detailError) && (
        <div className="mt-4 rounded-md border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
          {detailLoading && <div className="text-slate-400">Loading log details…</div>}
          {detailError && <div className="text-rose-400">{detailError}</div>}
          {selectedLog && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-slate-100">Log #{selectedLog.id}</h4>
                {selectedLog.created_at && (
                  <span className="text-[11px] text-slate-400">
                    {new Date(selectedLog.created_at).toLocaleString()}
                  </span>
                )}
              </div>
              <p>
                <span className="font-semibold">Query:</span> {selectedLog.query_text}
              </p>
              <p>
                <span className="font-semibold">Answer:</span> {selectedLog.answer_text || "(not stored)"}
              </p>
              <p className="text-[11px] text-slate-400">
                Ticket: {selectedLog.ticket_id ?? "—"} · EchoScore: {" "}
                {typeof selectedLog.echo_score === "number"
                  ? selectedLog.echo_score.toFixed(2)
                  : "N/A"}
              </p>

              {selectedLog.reasoning && (
                <div className="mt-2">
                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    Reasoning
                  </p>
                  {selectedLog.reasoning.candidate_snippets.length === 0 && (
                    <p className="text-slate-400">
                      No snippet reasoning recorded for this call.
                    </p>
                  )}
                  <div className="space-y-1">
                    {selectedLog.reasoning.candidate_snippets.map((c) => {
                      const used = selectedLog.reasoning!.chosen_snippet_ids.includes(c.id);
                      return (
                        <div
                          key={c.id}
                          className="flex items-center justify-between rounded bg-slate-900/60 px-2 py-1"
                        >
                          <div>
                            <div className="font-medium">{c.title ?? `Snippet #${c.id}`}</div>
                            <div className="text-[11px] text-slate-400">
                              Score: {typeof c.score === "number" ? c.score.toFixed(3) : "N/A"}
                            </div>
                          </div>
                          {used && (
                            <span className="rounded-full bg-emerald-600/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-50">
                              Used
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <details className="mt-2 rounded bg-slate-900/60 px-2 py-1">
                <summary className="cursor-pointer text-[11px] text-slate-400">
                  Raw log JSON
                </summary>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-[10px] text-slate-300">
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
