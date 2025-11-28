import { useState } from "react";
import { API_BASE } from "./apiConfig";

export default function AskEchoWidget() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await fetch(`${API_BASE}/api/ask-echo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, limit: 5 }),
      });
      if (!res.ok) {
        const txt = await res.text();
        setAnswer(`Error: ${res.status} ${txt}`);
      } else {
        const data = await res.json();
        setAnswer(data.answer || "(no answer)");
      }
    } catch (err: any) {
      setAnswer(`Request failed: ${err.message}`);
    } finally {
      setLoading(false);
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

      {answer && (
        <div className="mt-3 whitespace-pre-wrap text-sm text-slate-200">
          {answer}
        </div>
      )}
    </div>
  );
}
