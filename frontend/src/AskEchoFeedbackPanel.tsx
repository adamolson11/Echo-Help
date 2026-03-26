import { useEffect, useState, useCallback } from "react";
import { getInsightsAskEchoFeedback } from "./api/endpoints";
import type { AskEchoFeedbackRow } from "./api/types";

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
      const data = await getInsightsAskEchoFeedback(LIMIT);
      setRows(Array.isArray(data) ? data : data.items ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load feedback rows");
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
    <section className="insights-panel insights-panel--feedback">
      <div className="insights-panel__header insights-panel__header--wrap">
        <div>
          <h2 className="insights-panel__title">Ask Echo Feedback</h2>
          <p className="insights-panel__description">Review saved Ask Echo feedback and filter for helpful or missed answers.</p>
        </div>
        <div className="insights-panel__toolbar">
          <div className="insights-panel__segmented" role="tablist" aria-label="Feedback filters">
            <button type="button" onClick={() => setHelpedFilter("all")} className={helpedFilter === "all" ? "is-active" : undefined}>All</button>
            <button type="button" onClick={() => setHelpedFilter("yes")} className={helpedFilter === "yes" ? "is-active is-success" : undefined}>Helpful</button>
            <button type="button" onClick={() => setHelpedFilter("no")} className={helpedFilter === "no" ? "is-active is-danger" : undefined}>Needs work</button>
          </div>
          <button
            type="button"
            onClick={() => fetchRows()}
            disabled={loading}
            className="insights-panel__button"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {loading && <div className="insights-panel__state">Loading feedback…</div>}
      {error && <div className="insights-panel__state insights-panel__state--error">Failed to load feedback: {error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="insights-panel__state">No Ask Echo feedback yet.</div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="insights-panel__table-wrap">
          <table className="insights-panel__table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Query</th>
                <th>Helped</th>
                <th>What worked</th>
                <th>Log</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const d = new Date(r.created_at);
                const time = isNaN(d.getTime()) ? r.created_at : d.toLocaleString();
                return (
                  <tr key={r.id}>
                    <td>{time}</td>
                    <td className="insights-panel__cell-query" title={r.query_text || ""}>{r.query_text || "—"}</td>
                    <td>
                      {r.helped ? <span className="insights-panel__pill insights-panel__pill--success">Helpful</span> : <span className="insights-panel__pill insights-panel__pill--danger">Needs work</span>}
                    </td>
                    <td>{r.notes ?? "—"}</td>
                    <td>{r.ask_echo_log_id}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
