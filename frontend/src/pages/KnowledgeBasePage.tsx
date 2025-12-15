import { useEffect, useRef, useState } from "react";
import Button from "../ui/Button";
import Card from "../ui/Card";
import Input from "../ui/Input";
import SectionHeader from "../ui/SectionHeader";

function SnippetBadge(props: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[11px] text-slate-200">
      {props.children}
    </span>
  );
}

export default function KnowledgeBasePage() {
  const [query, setQuery] = useState("");
  const [snippets, setSnippets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const queryInputRef = useRef<HTMLInputElement | null>(null);

  async function runSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/snippets/search?q=${encodeURIComponent(query.trim())}&limit=30`);
      if (!res.ok) throw new Error(`KB search error: ${res.status}`);
      const data = await res.json();

      const items = Array.isArray(data)
        ? data
        : (data?.items ?? data?.snippets ?? data?.results ?? []);

      setSnippets(Array.isArray(items) ? items : []);
    } catch (e: any) {
      setError(e?.message ?? "KB search failed");
      setSnippets([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    queryInputRef.current?.focus();
  }, []);

  return (
    <div>
      <SectionHeader
        title="Knowledge Base"
        description="Search curated snippets; this is what Ask Echo should cite."
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          ref={queryInputRef}
          className="flex-1"
          placeholder="Search snippets (e.g. password reset, SSO, VPN)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void runSearch();
          }}
        />
        <Button onClick={() => void runSearch()} disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </div>

      {error && (
        <div className="mt-3 rounded-xl border border-red-700 bg-red-950/60 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="mt-4 space-y-3">
        {!loading && snippets.length === 0 && query.trim().length > 0 && !error && (
          <Card className="text-sm text-slate-300">
            No snippets found.
          </Card>
        )}

        {snippets.map((s: any) => (
          <Card key={s.id ?? `${s.ticket_id ?? "t"}-${s.created_at ?? Math.random()}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold text-slate-100">
                {s.title ?? s.summary ?? "Snippet"}
              </div>
              <div className="flex flex-wrap gap-2">
                {s.ticket_id && <SnippetBadge>Ticket #{s.ticket_id}</SnippetBadge>}
                {s.source && <SnippetBadge>{String(s.source)}</SnippetBadge>}
              </div>
            </div>

            {(s.text ?? s.content ?? s.body ?? s.snippet_text) && (
              <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-950/40 p-3 text-xs text-slate-200">
                {String(s.text ?? s.content ?? s.body ?? s.snippet_text)}
              </pre>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
