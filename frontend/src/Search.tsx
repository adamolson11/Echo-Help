
import { useState, useEffect, useRef } from "react";
import AskEchoWidget from "./AskEchoWidget";
import SnippetCard from "./components/SnippetCard";
import TicketResultCard from "./components/TicketResultCard";
import { ApiError, formatApiError } from "./api/client";
import {
  createTicketFeedback,
  getSearchPatternsSummary,
  listTicketFeedback,
  postSnippetFeedback,
  searchSnippets,
  searchTicketsSemantic,
  searchTicketsText,
} from "./api/endpoints";
import type { SearchPatternsSummary, SearchTicketResult, SnippetSearchResult, TicketFeedbackRead } from "./api/types";

 
function formatDate(value?: string) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString();
}

function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightQuery(text: string, query: string) {
  const q = query.trim();
  if (!q) return text;

  const regex = new RegExp(`(${escapeRegExp(q)})`, "ig");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className="bg-yellow-300/30 text-yellow-100">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function StatusPill({ status }: { status?: string }) {
  if (!status) return <span className="text-slate-400">-</span>;
  const normalized = status.toLowerCase();
  let classes =
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border";

  if (normalized.includes("open")) {
    classes += " bg-red-500/10 text-red-200 border-red-500/60";
  } else if (normalized.includes("closed") || normalized.includes("resolved")) {
    classes += " bg-emerald-500/10 text-emerald-200 border-emerald-500/60";
  } else {
    classes += " bg-slate-500/10 text-slate-200 border-slate-500/60";
  }

  return <span className={classes}>{status}</span>;
}

export default function Search() {
  const [query, setQuery] = useState("");
  const [useSemantic, setUseSemantic] = useState(false);
  
  // Persist AI toggle to localStorage
  useEffect(() => {
    const saved = localStorage.getItem("useAiSearch");
    if (saved !== null) {
      setUseSemantic(saved === "true");
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("useAiSearch", String(useSemantic));
    } catch (e) {
      // ignore storage errors
    }
  }, [useSemantic]);
  const [results, setResults] = useState<SearchTicketResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<SearchTicketResult | null>(null);
  // Feedback UI state
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackNotes, setFeedbackNotes] = useState<string>("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [feedbackHelped, setFeedbackHelped] = useState<boolean | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "open" | "closed" | "other">(
    "all"
  );
  const [priorityFilter, setPriorityFilter] = useState<
    "all" | "low" | "medium" | "high" | "critical"
  >("all");
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  // Tabs: search | insights
  const [activeTab, setActiveTab] = useState<"search" | "insights" | "kb">("search");
  // When an Insights item requests a ticket that isn't loaded yet,
  // store its id here so we can auto-select it after a broad search.
  const [pendingInsightsTicketId, setPendingInsightsTicketId] = useState<number | null>(null);
  const [flashTicketId, setFlashTicketId] = useState<string | null>(null);

  const [patterns, setPatterns] = useState<SearchPatternsSummary | null>(null);
  const [patternsLoading, setPatternsLoading] = useState(false);
  const [patternsError, setPatternsError] = useState<string | null>(null);
  const [ticketFeedbackHistory, setTicketFeedbackHistory] = useState<TicketFeedbackRead[]>([]);
  const [ticketFeedbackLoading, setTicketFeedbackLoading] = useState(false);
  const [isPendingInsightsSelection, setIsPendingInsightsSelection] = useState(false);
  // KB library state
  const [kbQuery, setKbQuery] = useState("");
  const [kbSnippets, setKbSnippets] = useState<SnippetSearchResult[]>([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbError, setKbError] = useState<string | null>(null);

  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const filteredResults = results.filter((ticket) => {
    const status = String(ticket.status ?? "").toLowerCase();
    const priority = String(ticket.priority ?? "").toLowerCase();

    // Status filter
    if (statusFilter === "open" && !status.includes("open")) return false;
    if (
      statusFilter === "closed" &&
      !(status.includes("closed") || status.includes("resolved"))
    )
      return false;
    if (
      statusFilter === "other" &&
      (status.includes("open") ||
        status.includes("closed") ||
        status.includes("resolved"))
    )
      return false;

    // Priority filter
    if (priorityFilter === "low" && !priority.includes("low")) return false;
    if (priorityFilter === "medium" && !priority.includes("medium")) return false;
    if (priorityFilter === "high" && !priority.includes("high")) return false;
    if (priorityFilter === "critical" && !priority.includes("critical")) return false;

    return true;
  });

  // Keep activeIndex in bounds when filteredResults change
  useEffect(() => {
    if (!filteredResults.length) {
      setActiveIndex(null);
      return;
    }
    if (activeIndex === null || activeIndex >= filteredResults.length) {
      setActiveIndex(0);
    }
  }, [filteredResults, activeIndex]);

  // Global keyboard navigation
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // Ctrl+K / Cmd+K -> focus search input
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // Ignore arrow/enter/esc when typing in an input/textarea/select
      const target = e.target as HTMLElement | null;
      const tagName = target?.tagName.toLowerCase();
      if (tagName === "input" || tagName === "textarea" || tagName === "select") {
        return;
      }

      if (!filteredResults.length) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => {
          if (prev === null) return 0;
          return prev + 1 >= filteredResults.length ? filteredResults.length - 1 : prev + 1;
        });
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => {
          if (prev === null) return filteredResults.length - 1;
          return prev - 1 < 0 ? 0 : prev - 1;
        });
        return;
      }

      if (e.key === "Enter") {
        if (activeIndex !== null && filteredResults[activeIndex]) {
          e.preventDefault();
          setSelectedTicket(filteredResults[activeIndex]);
        }
        return;
      }

      if (e.key === "Escape") {
        if (selectedTicket) {
          e.preventDefault();
          setSelectedTicket(null);
          return;
        }
        if (activeIndex !== null) {
          e.preventDefault();
          setActiveIndex(null);
        }
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [filteredResults, activeIndex, selectedTicket]);

  // Central search runner used by the UI. Accept an optional `qArg` to
  // perform a broad search (e.g., empty string) when triggered from Insights.
  const runSearch = async (qArg?: string) => {
    const localQuery = qArg !== undefined ? qArg : query;

    setLoading(true);
    setError(null);
    setSelectedTicket(null);

    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, 10000);

    try {
      // Use typed endpoints; text search only accepts {q}, semantic search supports filters.
      let normalized: SearchTicketResult[] = [];

      if (useSemantic) {
        const data = await searchTicketsSemantic({
          q: localQuery,
          status: statusFilter,
          priority: priorityFilter,
          limit: 5,
        }, controller.signal);
        clearTimeout(timeout);

        normalized = data;
      } else {
        const data = await searchTicketsText(localQuery, controller.signal);
        clearTimeout(timeout);
        normalized = data;
      }

      setResults(normalized);

      // If Insights requested a specific ticket, try to select it now.
      if (pendingInsightsTicketId !== null) {
        const pid = pendingInsightsTicketId;
        const idx = normalized.findIndex((t) => String(t.id) === String(pid));
        if (idx !== -1) {
          const ticket = normalized[idx];
          setSelectedTicket(ticket);
          setActiveIndex(idx);
          // scroll into view and flash
          setTimeout(() => {
            const el = document.querySelector<HTMLElement>(`[data-ticket-id=\"${ticket.id}\"]`);
            if (el) {
              el.scrollIntoView({ behavior: "smooth", block: "center" });
            }
            setFlashTicketId(String(ticket.id));
          }, 50);
        }
        setPendingInsightsTicketId(null);
        // clear pending hint when we've attempted selection
        setIsPendingInsightsSelection(false);
      }
    } catch (err: any) {
      clearTimeout(timeout);
      if (err instanceof ApiError && err.status === 422) {
        setError("Invalid search request (422). Please try again.");
        setResults([]);
        return;
      }
      if (err?.name === "AbortError") {
        setError("Search timed out. Please try again.");
      } else {
        setError(formatApiError(err));
      }
      setResults([]);
    } finally {
      // ensure pending hint is cleared if an error/timeout occurred
      setIsPendingInsightsSelection(false);
      setLoading(false);
    }
  };

  // Listen for global ticket-selection events (dispatched by AskEchoWidget)
  // so clicking a reference will open the Search tab and select the ticket.
  useEffect(() => {
    function onSelect(e: any) {
      try {
        const detail = e?.detail ?? {};
        const ticketId = detail?.ticketId ?? detail?.ticket_id ?? null;
        if (ticketId) {
          handleInsightsTicketClick(Number(ticketId));
        }
      } catch (err) {
        // no-op
      }
    }

    window.addEventListener("echo-select-ticket", onSelect as EventListener);
    return () => window.removeEventListener("echo-select-ticket", onSelect as EventListener);
  }, [results, filteredResults]);

  // Listen for global "open search" events (dispatched by AskEchoWidget)
  // so Ask Echo can route users into the Search console with the same query.
  useEffect(() => {
    function onOpenSearch(e: any) {
      try {
        const detail = e?.detail ?? {};
        const q = String(detail?.query ?? "").trim();
        const ticketId = detail?.ticketId ?? detail?.ticket_id ?? null;

        setActiveTab("search");

        if (q) {
          setQuery(q);
          if (ticketId) {
            setPendingInsightsTicketId(Number(ticketId));
            setIsPendingInsightsSelection(true);
          }
          runSearch(q);
          return;
        }

        // If no query was provided, fall back to a broad search.
        if (ticketId) {
          setPendingInsightsTicketId(Number(ticketId));
          setIsPendingInsightsSelection(true);
          runSearch("");
          return;
        }

        runSearch("");
      } catch (err) {
        // no-op
      }
    }

    window.addEventListener("echo-open-search", onOpenSearch as EventListener);
    return () => window.removeEventListener("echo-open-search", onOpenSearch as EventListener);
  }, [runSearch]);

  // Clear temporary flash highlight after a short duration
  useEffect(() => {
    if (!flashTicketId) return;
    const t = window.setTimeout(() => setFlashTicketId(null), 1500);
    return () => window.clearTimeout(t);
  }, [flashTicketId]);

  // Send snippet feedback to backend using ticket_id so snippets can be
  // auto-created/updated via ensure_snippet_for_feedback.
  async function handleSnippetFeedback(ticketId: string | number, helped: boolean, notes?: string) {
    setFeedbackError(null);
    setFeedbackSuccess(null);
    setFeedbackSubmitting(true);
    try {
      const payload: any = { ticket_id: ticketId, helped };
      if (notes && notes.trim().length) payload.notes = notes.trim();

      await postSnippetFeedback(payload);

      setFeedbackSuccess("Thank you — feedback submitted.");

      // If the ticket we just fed back on isn't selected, select it so user
      // can see the updated KB state in the inspector.
      if (!selectedTicket || String(selectedTicket.id) !== String(ticketId)) {
        const found = results.find((t) => String(t.id) === String(ticketId));
        if (found) setSelectedTicket(found as SearchTicketResult);
      }

      // Refresh ticket feedback history for the selected ticket
      try {
        const history = await listTicketFeedback(Number(ticketId));
        setTicketFeedbackHistory(Array.isArray(history) ? history : []);
      } catch (err) {
        // ignore history refresh errors
      }
    } catch (err: any) {
      setFeedbackError(formatApiError(err));
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  const handleSearch = async () => runSearch();

  // Reset feedback state when selected ticket changes
  useEffect(() => {
    setFeedbackError(null);
    setFeedbackSuccess(null);
    setFeedbackNotes("");
    setFeedbackRating(5);
    setFeedbackSubmitting(false);
    setFeedbackHelped(null);
    // Load ticket feedback history for inspector
    if (selectedTicket && selectedTicket.id) {
      const loadHistory = async () => {
        try {
          setTicketFeedbackLoading(true);
          const history = await listTicketFeedback(Number(selectedTicket.id));
          setTicketFeedbackHistory(Array.isArray(history) ? history : []);
        } catch (err) {
          setTicketFeedbackHistory([]);
        } finally {
          setTicketFeedbackLoading(false);
        }
      };

      loadHistory();
    } else {
      setTicketFeedbackHistory([]);
    }
  }, [selectedTicket]);

  // Fetch patterns summary when Insights tab is activated
  useEffect(() => {
    if (activeTab !== "insights") return;
    if (patterns || patternsLoading) return;

    const fetchPatterns = async () => {
      try {
        setPatternsLoading(true);
        setPatternsError(null);

        const data = await getSearchPatternsSummary(30);
        setPatterns(data);
      } catch (err: any) {
        setPatternsError(formatApiError(err));
      } finally {
        setPatternsLoading(false);
      }
    };

    fetchPatterns();
  }, [activeTab, patterns, patternsLoading]);

  async function fetchKbSnippets(query: string) {
    try {
      setKbLoading(true);
      setKbError(null);
      const data = await searchSnippets(query, 10);
      setKbSnippets(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setKbError(err?.message || "Knowledge Base search failed");
      setKbSnippets([]);
    } finally {
      setKbLoading(false);
    }
  }

  async function handleSubmitFeedback() {
    if (!selectedTicket) return;

    setFeedbackError(null);
    setFeedbackSuccess(null);

    // Require notes for low ratings or when user says it did NOT help
    if ((feedbackRating <= 3 || feedbackHelped === false) && !feedbackNotes.trim()) {
      setFeedbackError("Please describe what actually fixed it for low ratings or why this did not help.");
      return;
    }

    setFeedbackSubmitting(true);
    try {
      const payload = {
        ticket_id: Number(selectedTicket.id),
        rating: feedbackRating,
        resolution_notes: feedbackNotes.trim(),
        // ensure non-null value for query_text to match backend NOT NULL constraint
        query_text: query || "",
        // prefer explicit helped flag if user set it; otherwise infer from rating
        helped: feedbackHelped !== null ? feedbackHelped : feedbackRating >= 4,
      } as any;

      await createTicketFeedback(payload);

      setFeedbackSuccess("Feedback saved — thanks!");
      setFeedbackNotes("");
      setFeedbackRating(5);
    } catch (err) {
      if (err instanceof ApiError) {
        setFeedbackError(formatApiError(err));
      } else {
        setFeedbackError("Network error while saving feedback.");
      }
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  // When an Insights list item is clicked, switch to Search and try to select that ticket.
  const handleInsightsTicketClick = (ticketId: number) => {
    // Switch to the search tab
    setActiveTab("search");
    // Try to find the ticket in the currently loaded results (best-effort)
    const foundIdx = results.findIndex((t: any) => String(t.id) === String(ticketId));
    if (foundIdx !== -1) {
      const ticket = results[foundIdx];
      setSelectedTicket(ticket);
      // Also try to set the active index so the row is highlighted if visible
      const idx = filteredResults.findIndex((t) => String(t.id) === String(ticketId));
      if (idx >= 0) setActiveIndex(idx);
      // Scroll into view and flash the row
      setTimeout(() => {
        const el = document.querySelector<HTMLElement>(`[data-ticket-id=\"${ticket.id}\"]`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
        setFlashTicketId(String(ticket.id));
      }, 50);
      return;
    }

    // If not found, remember we want this ticket and trigger a broad search
    setPendingInsightsTicketId(ticketId);
    setIsPendingInsightsSelection(true);
    // run a broad search (empty query) to load recent tickets
    runSearch("");
  };

    return (
      <div className="mx-auto max-w-3xl bg-slate-800/80 border border-slate-700 rounded-xl p-6 md:p-8 shadow-lg text-slate-100">
      <h2 className="text-xl font-semibold mb-1">Ticket Search</h2>
      <p className="text-xs text-slate-400 mb-1">
        Search your raw tickets by keyword or AI semantic relevance.
      </p>
      <p className="text-xs text-slate-400 mb-4">
        Try: <span className="font-mono">password reset</span>, <span className="font-mono">vpn</span>, <span className="font-mono">onboarding</span>.
      </p>

      {/* Tab header */}
      <div className="mb-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("search")}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === "search"
                ? "border-indigo-500 text-indigo-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Ticket Search
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("insights")}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === "insights"
                ? "border-indigo-500 text-indigo-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Insights
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("kb")}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === "kb"
                ? "border-indigo-500 text-indigo-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Knowledge Base
          </button>
        </div>
      </div>

      {activeTab === "search" && (
        <>
      {/* Search bar */}
      <form
        className="flex gap-2 mb-4"
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
      >
        <input
          ref={searchInputRef}
          type="text"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Describe the issue or paste an error message…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 disabled:cursor-not-allowed"
          disabled={loading}
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      <div className="mb-4">
        <div className="text-xs text-slate-400">Try asking a question or describing what happened — e.g. "I can't log in after password reset".</div>
      </div>
      {/* (moved below, before Results) */}

      {/* Error banner */}
      {error && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-500/60 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          <span className="mt-0.5 text-lg leading-none">!</span>
          <div className="flex-1">
            <div className="font-semibold">Search error</div>
            <div>{error}</div>
          </div>
          <button
            type="button"
            onClick={handleSearch}
            className="ml-2 text-xs font-medium underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters + summary */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2 text-xs text-slate-300">
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex items-center gap-1">
            <span className="text-slate-400">Status</span>
            <select
              className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as "all" | "open" | "closed" | "other")
              }
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="closed">Closed / Resolved</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={useSemantic}
              onChange={(e) => setUseSemantic(e.target.checked)}
              className="h-4 w-4"
            />
            <span>Use AI semantic search</span>
          </label>

          <label className="inline-flex items-center gap-1">
            <span className="text-slate-400">Priority</span>
            <select
              className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={priorityFilter}
              onChange={(e) =>
                setPriorityFilter(
                  e.target.value as "all" | "low" | "medium" | "high" | "critical"
                )
              }
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>

        <div className="text-slate-400">
          {results.length === 0 ? (
            <span>No tickets loaded yet</span>
          ) : filteredResults.length === 0 ? (
            <span>No tickets match current filters</span>
          ) : useSemantic ? (
            <span>
              Showing top <span className="font-semibold text-slate-100">{filteredResults.length}</span> AI-ranked tickets
            </span>
          ) : (
            <span>
              Showing <span className="font-semibold text-slate-100">{filteredResults.length}</span> of <span className="font-semibold text-slate-100">{results.length}</span> tickets
            </span>
          )}
        </div>
      </div>

      {/* End Search tab */}
        </>
      )}

      {activeTab === "insights" && (
        <div className="space-y-4">
          <p className="text-xs text-slate-400 mb-1">
            View patterns, system behavior, and AI routing signals from Ask Echo.
          </p>
          {/* Friendly empty state when there is no feedback at all */}
          {patterns && patterns.total_feedback === 0 && !patternsLoading && (
            <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-xs text-slate-300">
              <p className="font-medium text-slate-100 mb-1">No feedback yet</p>
              <p>As agents start submitting “Did this resolve your issue?” feedback, EchoHelp will surface unresolved patterns and high-friction tickets here.</p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
              <div className="text-xs text-slate-400">Total Feedback</div>
              <div className="mt-1 text-2xl font-semibold">
                {patterns ? patterns.total_feedback : patternsLoading ? "…" : "0"}
              </div>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
              <div className="text-xs text-slate-400">Tickets with Unresolved Feedback</div>
              <div className="mt-1 text-2xl font-semibold">
                {patterns
                  ? (patterns.by_ticket ?? []).filter((t) => t.unresolved > 0).length
                  : patternsLoading
                  ? "…"
                  : "0"}
              </div>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
              <div className="text-xs text-slate-400">Most Unresolved Ticket</div>
              <div className="mt-1 text-sm font-semibold line-clamp-2">
                {patterns && (patterns.top_unresolved ?? []).length > 0
                  ? (patterns.top_unresolved ?? [])[0].summary || `Ticket #${(patterns.top_unresolved ?? [])[0].ticket_id}`
                  : patternsLoading
                  ? "Loading…"
                  : "No data"}
              </div>
            </div>
          </div>

          {patternsError && (
            <div className="rounded-md border border-rose-500/50 bg-rose-950/40 px-3 py-2 text-xs text-rose-200">
              {patternsError}
            </div>
          )}

          <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-slate-100">Top Unresolved Tickets</h2>
              {patternsLoading && <span className="text-xs text-slate-400">Loading…</span>}
            </div>

            {patterns && (patterns.top_unresolved ?? []).length === 0 && !patternsLoading && (
              <p className="text-xs text-slate-400">No unresolved feedback yet. Once users start saying “No, this didn’t help”, they will show up here.</p>
            )}

            {patterns && (patterns.top_unresolved ?? []).length > 0 && (
              <ul className="divide-y divide-slate-800">
                {(patterns.top_unresolved ?? []).map((item) => (
                  <li
                    key={item.ticket_id}
                    onClick={() => handleInsightsTicketClick(item.ticket_id)}
                    className="py-2 flex items-center justify-between cursor-pointer hover:bg-slate-800/60 rounded-md px-2 transition"
                  >
                    <div className="mr-2">
                      <div className="text-xs font-medium text-slate-100">{item.summary || `Ticket #${item.ticket_id}`}</div>
                      <div className="text-[11px] text-slate-400">Ticket #{item.ticket_id}</div>
                    </div>
                    <div className="flex gap-3 text-[11px]">
                      <span className="px-2 py-1 rounded-full bg-slate-800 text-slate-200">{item.total_feedback} feedback</span>
                      <span className="px-2 py-1 rounded-full bg-rose-900/70 text-rose-100">{item.unresolved} unresolved</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {activeTab === "kb" && (
        <div className="mt-2">
          <p className="text-xs text-slate-400 mb-2">
            Search reusable solution snippets created from past tickets and resolutions.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              fetchKbSnippets(kbQuery);
            }}
            className="mb-3 flex gap-2"
          >
            <input
              type="text"
              value={kbQuery}
              onChange={(e) => setKbQuery(e.target.value)}
              placeholder="Search knowledge base..."
              className="flex-1 border rounded px-2 py-1 text-sm bg-slate-900/50"
            />
            <button
              type="submit"
              className="border rounded px-3 py-1 text-sm"
              disabled={kbLoading}
            >
              {kbLoading ? "Searching..." : "Search"}
            </button>
          </form>

          {kbError && <div className="mb-2 text-xs text-rose-400">{kbError}</div>}

          {!kbLoading && kbSnippets.length === 0 && !kbError && (
            <div className="text-xs text-slate-400">No snippets yet. Try submitting feedback from tickets or use a broader query.</div>
          )}

          <div className="space-y-2 mt-3">
            {kbSnippets.map((s: any) => (
              <SnippetCard
                key={s.id}
                id={s.id}
                title={s.title ?? null}
                summary={s.summary ?? null}
                echo_score={s.echo_score ?? null}
                success_count={s.success_count ?? 0}
                failure_count={s.failure_count ?? 0}
                ticket_id={s.ticket_id ?? null}
              />
            ))}
          </div>
        </div>
      )}

      {/* Ask Echo helper card */}
      <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Ask Echo (AI assistant)</h2>
            <p className="mt-1 text-xs text-slate-400">
              Ask a natural-language question about your issues. Echo will search past tickets and snippets, then explain why it chose its answer.
            </p>
          </div>
        </div>

        <div className="mt-3">
          <AskEchoWidget />
        </div>
      </div>

      {/* Results + inspector layout */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.4fr)] gap-3 items-start">
        {/* Results table */}
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-100">Results</h2>
            <div className="flex items-center gap-3">
              {useSemantic ? (
                <div className="text-xs text-emerald-200">
                  {query ? (
                    <span>
                      AI semantic search – top <span className="font-semibold">{filteredResults.length}</span> matches for “{query}”
                    </span>
                  ) : (
                    <span>AI semantic search – top <span className="font-semibold">{filteredResults.length}</span> matches for recent issues</span>
                  )}
                </div>
              ) : (
                <span className="inline-flex items-center rounded-full border border-slate-600 bg-slate-900/30 px-2 py-1 text-[11px] font-medium text-slate-200">Keyword search</span>
              )}

              {loading && (
                <div className="text-xs text-slate-400">{useSemantic ? "Running AI search…" : "Searching…"}</div>
              )}
              {isPendingInsightsSelection && (
                <div className="text-xs text-slate-400">Loading and focusing ticket selected from Insights…</div>
              )}
            </div>
          </div>
          {results.length === 0 && !loading && !error && (
            <div className="px-4 py-6 text-sm text-slate-400 text-center">
              {useSemantic ? (
                <span>No strong AI matches yet. Try a different query or switch to keyword search.</span>
              ) : (
                <span>No tickets yet. Try a different keyword or broaden your search.</span>
              )}
            </div>
          )}

          {filteredResults.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-900/80 text-slate-300">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium">ID</th>
                    <th className="text-left px-4 py-2 font-medium">Title</th>
                    <th className="text-left px-4 py-2 font-medium">Status</th>
                    <th className="text-left px-4 py-2 font-medium">Priority</th>
                    <th className="text-left px-4 py-2 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.map((ticket, index) => {
                    const isActive = index === activeIndex;
                    const isFlashing =
                      !!flashTicketId && String(flashTicketId) === String(ticket.id);

                    const highlightedTitle = highlightQuery(
                      String(ticket.title ?? ticket.summary ?? ""),
                      query,
                    );

                    const statusPill = <StatusPill status={ticket.status} />;
                    const priorityCell = <>{ticket.priority ?? "-"}</>;
                    const createdAtCell = <>{ticket.created_at ? formatDate(ticket.created_at) : "-"}</>;

                    const feedbackButtons = (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTicket(ticket);
                            handleSnippetFeedback(ticket.id, true);
                          }}
                          title="This helped"
                          className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-xs"
                        >
                          👍
                        </button>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            setSelectedTicket(ticket);
                            const note = window.prompt(
                              "What actually fixed it or why this didn't help? (optional)",
                            );
                            await handleSnippetFeedback(ticket.id, false, note ?? "");
                          }}
                          title="Didn't help"
                          className="px-2 py-1 rounded bg-rose-600 hover:bg-rose-500 text-xs"
                        >
                          👎
                        </button>
                      </>
                    );

                    return (
                      <TicketResultCard
                        key={ticket.id}
                        ticket={ticket as any}
                        isActive={isActive}
                        isFlashing={isFlashing}
                        onSelect={() => {
                          setSelectedTicket(ticket);
                          setActiveIndex(index);
                        }}
                        highlightedTitle={highlightedTitle}
                        statusPill={statusPill}
                        priorityCell={priorityCell}
                        createdAtCell={createdAtCell}
                        feedbackButtons={feedbackButtons}
                        useSemantic={useSemantic}
                      />
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {results.length > 0 &&
            filteredResults.length === 0 &&
            !loading &&
            !error && (
              <div className="px-4 py-6 text-sm text-slate-400 text-center">
                {useSemantic ? (
                  <span>No strong AI matches for “{query || 'your query'}”. Try different wording or switch to keyword search.</span>
                ) : (
                  <span>No tickets found for “{query}”. Try a broader search or switch to AI semantic search.</span>
                )}
              </div>
            )}
        </div>

        {/* Inspector panel */}
        <div className="p-4 rounded-lg border border-slate-700 bg-slate-900/80 min-h-[160px]">
          {selectedTicket ? (
            <>
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="text-xs text-slate-400 mb-1">
                    Ticket ID:{" "}
                    <span className="font-mono">{selectedTicket.id}</span>
                  </div>
                  <h3 className="text-lg font-semibold">
                    {selectedTicket.title ?? selectedTicket.summary}
                  </h3>
                  {selectedTicket && (selectedTicket as any).ai_score !== undefined && (
                    <div className="text-xs text-emerald-300">AI score: {((selectedTicket as any).ai_score as number).toFixed(2)}</div>
                  )}
                </div>
                <button
                  type="button"
                  className="text-xs text-slate-400 hover:text-slate-200"
                  onClick={() => setSelectedTicket(null)}
                >
                  Close ✕
                </button>
              </div>

              <div className="flex flex-wrap gap-3 mb-3 text-xs text-slate-300">
                <StatusPill status={selectedTicket.status} />
                {selectedTicket.priority && (
                  <span className="px-2 py-0.5 rounded-full border border-slate-600">
                    Priority: {selectedTicket.priority}
                  </span>
                )}
                {selectedTicket.created_at && (
                  <span>Created: {formatDate(selectedTicket.created_at)}</span>
                )}
                {selectedTicket.updated_at && (
                  <span>Updated: {formatDate(selectedTicket.updated_at)}</span>
                )}
              </div>

              {selectedTicket.summary && (
                <p className="text-sm text-slate-200 mb-2">
                  {selectedTicket.summary}
                </p>
              )}

              {selectedTicket.description && (
                <div className="mt-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                    Description
                  </div>
                  <p className="text-sm text-slate-200 whitespace-pre-wrap">
                    {selectedTicket.description}
                  </p>
                </div>
              )}

              {typeof (selectedTicket as any).resolution === "string" && (selectedTicket as any).resolution && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-emerald-300 uppercase tracking-wide mb-1">
                    Resolution
                  </div>
                  <p className="text-sm text-slate-100 whitespace-pre-wrap">
                    {(selectedTicket as any).resolution}
                  </p>
                </div>
              )}

              {/* Previous feedback history (if any) */}
              {ticketFeedbackLoading ? (
                <div className="mb-3 text-xs text-slate-400">Loading previous feedback…</div>
              ) : ticketFeedbackHistory && ticketFeedbackHistory.length > 0 ? (
                <div className="mb-3 border border-slate-800 rounded-md bg-slate-900/70 p-2 max-h-40 overflow-y-auto">
                  <div className="text-[11px] font-semibold text-slate-200 mb-1">Previous feedback</div>
                  <ul className="space-y-1">
                    {ticketFeedbackHistory.map((fb) => (
                      <li key={fb.id} className="text-[11px] text-slate-300">
                        <span className="font-medium">{fb.helped ? "✅ Helped" : "⚠️ Not resolved"}</span>{" "}
                        · rating {fb.rating} · <span className="text-slate-400">{fb.resolution_notes ? (fb.resolution_notes.length > 120 ? fb.resolution_notes.slice(0, 120) + "…" : fb.resolution_notes) : ""}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {/* Feedback form */}
              <div className="mt-6 border border-slate-700 rounded-lg p-4 bg-slate-900/60">
                <h3 className="text-sm font-semibold mb-3">Feedback</h3>

                <label className="block text-xs font-medium mb-1">Did this resolve your issue?</label>
                <div className="flex gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => setFeedbackHelped(true)}
                    className={`px-3 py-1 rounded-md text-xs font-medium border ${feedbackHelped === true ? 'bg-emerald-600/80 border-emerald-400' : 'bg-slate-900 border-slate-700'}`}
                    disabled={feedbackSubmitting}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => setFeedbackHelped(false)}
                    className={`px-3 py-1 rounded-md text-xs font-medium border ${feedbackHelped === false ? 'bg-rose-600/80 border-rose-400' : 'bg-slate-900 border-slate-700'}`}
                    disabled={feedbackSubmitting}
                  >
                    No
                  </button>
                </div>

                <label className="block text-xs font-medium mb-1">How helpful was this ticket?</label>
                <select
                  className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm mb-3"
                  value={feedbackRating}
                  onChange={(e) => setFeedbackRating(Number(e.target.value))}
                  disabled={feedbackSubmitting}
                >
                  <option value={5}>5 – Very helpful</option>
                  <option value={4}>4</option>
                  <option value={3}>3 – Neutral</option>
                  <option value={2}>2</option>
                  <option value={1}>1 – Not helpful</option>
                </select>

                <label className="block text-xs font-medium mb-1">What actually fixed it? (steps, missing info, or notes)</label>
                <textarea
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm mb-3 resize-y min-h-[80px]"
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  disabled={feedbackSubmitting}
                  placeholder="Example: Had to clear cached credentials and re-sync MFA before reset worked..."
                />

                {feedbackError && <p className="text-xs text-red-400 mb-2">{feedbackError}</p>}
                {feedbackSuccess && <p className="text-xs text-emerald-400 mb-2">{feedbackSuccess}</p>}

                <button
                  type="button"
                  onClick={handleSubmitFeedback}
                  disabled={feedbackSubmitting || !selectedTicket}
                  className="inline-flex items-center rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed px-3 py-1.5 text-xs font-medium"
                >
                  {feedbackSubmitting ? "Submitting..." : "Submit feedback"}
                </button>
              </div>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-sm text-slate-400">
              <div className="mb-1 font-semibold text-slate-200">
                No ticket selected
              </div>
              <div className="text-center">
                Choose a ticket from the table to view its full details here.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
