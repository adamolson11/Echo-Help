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
    <div style={{ maxWidth: 600, margin: "2rem auto" }}>
      <h2>Intake Assistant</h2>
      <textarea
        rows={3}
        style={{ width: "100%" }}
        placeholder="Describe the customer's issue..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <br />
      <button onClick={handleAnalyze} disabled={loading || !text.trim()}>
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {results && (
        <div style={{ marginTop: 32 }}>
          <h3>Suggested Tickets</h3>
          {results.suggested_tickets.length === 0 && <div>No matches found.</div>}
          {results.suggested_tickets.map((t) => (
            <div key={t.id} style={{ border: "1px solid #ccc", borderRadius: 8, padding: 12, marginBottom: 16 }}>
              <div>
                <b>{t.summary}</b> <span style={{ color: "#888" }}>({t.external_key})</span>
              </div>
              <div style={{ fontSize: 13, color: "#555" }}>{t.description}</div>
              <div style={{ fontSize: 12, color: "#888" }}>
                Status: {t.status} | Priority: {t.priority || "-"} | Similarity: {Math.round(t.similarity * 100)}%
              </div>
              <div style={{ marginTop: 8 }}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    style={{
                      color: feedback[t.id] === star ? "#1976d2" : "#888",
                      fontWeight: feedback[t.id] === star ? "bold" : undefined,
                      marginRight: 2,
                    }}
                    disabled={!!thanks[t.id]}
                    onClick={() => handleFeedback(t.id, star)}
                  >
                    ★
                  </button>
                ))}
                {thanks[t.id] && <span style={{ color: "green", marginLeft: 8 }}>Thanks!</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
