import { useEffect, useState } from "react";

export type AskEchoLogEntry = {
  id: number;
  created_at: string;
  query: string;
  mode?: string | null;
  kb_confidence?: number | null;
  references_count?: number | null;
};

const LIMIT = 100;

export default function AskEchoLogsPanel() {
  const [logs, setLogs] = useState<AskEchoLogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState<"all" | "kb" | "general">("all");

  useEffect(() => {
    let cancelled = false;
    const fetchLogs = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/insights/ask-echo-logs?limit=${LIMIT}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: AskEchoLogEntry[] = await res.json();
        if (!cancelled) setLogs(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.message ?? "Failed to load Ask Echo logs");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchLogs();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = logs.filter((l) => {
    if (modeFilter === "all") return true;
    if (modeFilter === "kb") return !!l.mode && l.mode.toLowerCase().includes("kb");
    if (modeFilter === "general") return !!l.mode && l.mode.toLowerCase().includes("general");
    return true;
  });

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-100">Ask Echo Logs</h3>
        <div className="flex items-center gap-2 text-xs">
          <label className="text-slate-400">Mode</label>
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value as any)}
            className="rounded bg-slate-800/60 px-2 py-1 text-sm text-slate-200"
          >
            <option value="all">All</option>
            <option value="kb">KB</option>
            <option value="general">General</option>
          </select>
        </div>
      </div>

      {loading && <div className="mt-3 text-xs text-slate-400">Loading Ask Echo logs…</div>}
      {error && <div className="mt-3 text-xs text-rose-400">Could not load Ask Echo logs: {error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="mt-3 text-xs text-slate-500">No Ask Echo logs yet.</div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="mt-3 max-h-72 overflow-y-auto text-xs">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-slate-900/80 text-slate-400">
              <tr>
                <th className="text-left py-1 pr-2">Time</th>
                <th className="text-left py-1 pr-2">Query</th>
                <th className="text-left py-1 pr-2">Mode</th>
                <th className="text-left py-1 pr-2">KB Conf</th>
                <th className="text-left py-1 pr-2">Refs</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l) => {
                const d = new Date(l.created_at);
                const time = isNaN(d.getTime()) ? l.created_at : d.toLocaleString();
                const kb = l.kb_confidence ?? null;
                const kbPct = kb === null ? null : Math.round(kb * 100);
                return (
                  <tr key={l.id} className="border-t border-slate-800/80">
                    <td className="py-1 pr-2 align-top text-slate-300">{time}</td>
                    <td className="py-1 pr-2 align-top text-slate-100 truncate max-w-xs" title={l.query || ""}>{l.query}</td>
                    <td className="py-1 pr-2 align-top text-slate-200">{l.mode ?? "—"}</td>
                    <td className="py-1 pr-2 align-top">{kbPct === null ? <span className="text-slate-400">—</span> : <span className="text-slate-300">{kbPct}%</span>}</td>
                    <td className="py-1 pr-2 align-top text-slate-300">{l.references_count ?? "—"}</td>
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
