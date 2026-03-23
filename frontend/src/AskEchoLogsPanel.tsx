import { useEffect, useState } from "react";
import { getInsightsAskEchoLogDetail, getInsightsAskEchoLogs } from "./api/endpoints";

type AskEchoLogSummary = {
  id: number;
  query_text: string;
  ticket_id?: number | null;
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
  ticket_id?: number | null;
  echo_score?: number | null;
  created_at?: string | null;
  reasoning?: {
    candidate_snippets: ReasoningSnippetCandidate[];
    chosen_snippet_ids: number[];
  } | null;
  reasoning_notes?: string | null;
};

const LIMIT = 100;

function formatTimestamp(value?: string | null) {
  const parsed = value ? new Date(value) : null;
  return parsed && !isNaN(parsed.getTime()) ? parsed.toLocaleString() : value ?? "—";
}

function getErrorMessage(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

export default function AskEchoLogsPanel() {
  const [logs, setLogs] = useState<AskEchoLogSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedLog, setSelectedLog] = useState<AskEchoLogDetail | null>(null);
  const [activeLogId, setActiveLogId] = useState<number | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadLogs() {
      setLoading(true);
      setError(null);
      try {
        const raw = await getInsightsAskEchoLogs(LIMIT);
        const items: AskEchoLogSummary[] = raw.items ?? [];
        if (!cancelled) setLogs(items);
      } catch (err: unknown) {
        if (!cancelled) setError(getErrorMessage(err, "Error loading Ask Echo logs"));
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
    setActiveLogId(id);
    setDetailLoading(true);
    setDetailError(null);
    setSelectedLog(null);
    try {
      const raw = await getInsightsAskEchoLogDetail(id);
      const item: AskEchoLogDetail = raw.item;
      setSelectedLog(item);
    } catch (err: unknown) {
      setDetailError(getErrorMessage(err, "Error loading log detail"));
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <section className="insights-panel insights-panel--ask-echo">
      <div className="insights-panel__header">
        <div>
          <h2 className="insights-panel__title">Ask Echo Query History</h2>
          <p className="insights-panel__description">
            Review past Ask Echo questions, confidence, and reasoning for each answer.
          </p>
        </div>
        <span className="insights-panel__tag">Last {LIMIT}</span>
      </div>

      {loading && <div className="insights-panel__state">Loading Ask Echo logs…</div>}
      {error && <div className="insights-panel__state insights-panel__state--error">Could not load Ask Echo logs: {error}</div>}

      {!loading && !error && logs.length === 0 && (
        <div className="insights-panel__state">No Ask Echo logs yet.</div>
      )}

      {!loading && !error && logs.length > 0 && (
        <div className="insights-panel__table-wrap">
          <table className="insights-panel__table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Query</th>
                <th>Ticket</th>
                <th>EchoScore</th>
                <th aria-label="Actions"></th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                const isActive = activeLogId === log.id;
                return (
                  <tr key={log.id} className={isActive ? "is-active" : undefined}>
                    <td>{formatTimestamp(log.created_at)}</td>
                    <td className="insights-panel__cell-query" title={log.query_text}>
                      {log.query_text}
                    </td>
                    <td>{log.ticket_id ?? "—"}</td>
                    <td>
                      {typeof log.echo_score === "number" ? log.echo_score.toFixed(2) : "N/A"}
                    </td>
                    <td className="insights-panel__cell-action">
                      <button
                        type="button"
                        className="insights-panel__button"
                        onClick={() => loadLogDetail(log.id)}
                      >
                        {isActive ? "Open" : "View"}
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
        <div className="insights-panel__detail" role="status" aria-live="polite">
          {detailLoading && <div className="insights-panel__state">Loading log details…</div>}
          {detailError && <div className="insights-panel__state insights-panel__state--error">{detailError}</div>}
          {selectedLog && (
            <div className="insights-panel__detail-stack">
              <div className="insights-panel__detail-header">
                <h4 className="insights-panel__detail-title">Log #{selectedLog.id}</h4>
                {selectedLog.created_at && (
                  <span className="insights-panel__detail-meta">
                    {formatTimestamp(selectedLog.created_at)}
                  </span>
                )}
              </div>
              <div className="insights-panel__detail-block">
                <span className="insights-panel__detail-label">Query</span>
                <p>{selectedLog.query_text}</p>
              </div>
              <div className="insights-panel__detail-block">
                <span className="insights-panel__detail-label">Answer</span>
                <p>{selectedLog.answer_text || "(not stored)"}</p>
              </div>
              <p className="insights-panel__detail-meta">
                Ticket: {selectedLog.ticket_id ?? "—"} · EchoScore: {" "}
                {typeof selectedLog.echo_score === "number"
                  ? selectedLog.echo_score.toFixed(2)
                  : "N/A"}
              </p>

              {selectedLog.reasoning && (
                <div className="insights-panel__detail-section">
                  <p className="insights-panel__detail-label insights-panel__detail-label--section">
                    Reasoning
                  </p>
                  {selectedLog.reasoning.candidate_snippets.length === 0 && (
                    <p className="insights-panel__detail-meta">
                      No snippet reasoning recorded for this call.
                    </p>
                  )}
                  <div className="insights-panel__reasoning-list">
                    {selectedLog.reasoning.candidate_snippets.map((c) => {
                      const used = selectedLog.reasoning!.chosen_snippet_ids.includes(c.id);
                      return (
                        <div
                          key={c.id}
                          className="insights-panel__reasoning-item"
                        >
                          <div>
                            <div className="insights-panel__reasoning-title">{c.title ?? `Snippet #${c.id}`}</div>
                            <div className="insights-panel__detail-meta">
                              Score: {typeof c.score === "number" ? c.score.toFixed(3) : "N/A"}
                            </div>
                          </div>
                          {used && (
                            <span className="insights-panel__pill insights-panel__pill--success">
                              Used
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <details className="insights-panel__json">
                <summary className="insights-panel__json-summary">
                  Raw log JSON
                </summary>
                <pre className="insights-panel__json-pre">
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
