import React, { useState } from "react";

interface Ticket {
  id: number;
  external_key: string;
  source: string;
  project_key: string;
  summary: string;
  description: string;
  status: string;
  priority?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

const API_URL = "http://localhost:8000/api/search";

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}?q=${encodeURIComponent(query)}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", padding: 24 }}>
      <h2>Ticket Search</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Type a keyword..."
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {results.map(ticket => (
          <li key={ticket.id} style={{ border: "1px solid #ccc", borderRadius: 6, margin: "12px 0", padding: 12 }}>
            <strong>{ticket.summary}</strong> <span style={{ color: "#888" }}>({ticket.status})</span>
            <div style={{ fontSize: 13, color: "#555" }}>{ticket.description}</div>
            <div style={{ fontSize: 12, color: "#999" }}>
              <span>Key: {ticket.external_key}</span> | <span>Project: {ticket.project_key}</span> | <span>Priority: {ticket.priority || "-"}</span>
            </div>
          </li>
        ))}
      </ul>
      {results.length === 0 && !loading && !error && <div>No results.</div>}
    </div>
  );
}
