
import React, { useState, useEffect, useRef } from "react";
import { getApiBase } from "./apiConfig";

type TicketResult = {
  id: string | number;
  title?: string;
  summary?: string;
  status?: string;
  priority?: string;
  created_at?: string;
  updated_at?: string;
  description?: string;
  resolution?: string;
  [key: string]: unknown;
};

const API_BASE = getApiBase();
const API_URL = `${API_BASE}/api/search`;

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
  console.log("SEARCH API_BASE =", API_BASE);
  const [results, setResults] = useState<TicketResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<TicketResult | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "open" | "closed" | "other">(
    "all"
  );
  const [priorityFilter, setPriorityFilter] = useState<
    "all" | "low" | "medium" | "high" | "critical"
  >("all");
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

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

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSelectedTicket(null);

    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, 10000);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q: query }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (res.status === 422) {
        setError("Invalid search request (422). Please try again.");
        setResults([]);
        return;
      }

      if (!res.ok) {
        throw new Error(`Error: ${res.status}`);
      }

      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
    } catch (err: any) {
      clearTimeout(timeout);
      if (err?.name === "AbortError") {
        setError("Search timed out. Please try again.");
      } else {
        setError(err?.message || "Unknown error");
      }
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

    return (
      <div className="mx-auto max-w-3xl bg-slate-800/80 border border-slate-700 rounded-xl p-6 md:p-8 shadow-lg text-slate-100">
      <h2 className="text-xl font-semibold mb-1">Ticket Search</h2>
      <p className="text-xs text-slate-400 mb-4">
        Search across tickets by keyword. Try:{" "}
        <span className="font-mono">password reset</span>,{" "}
        <span className="font-mono">vpn</span>,{" "}
        <span className="font-mono">onboarding</span>.
      </p>

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
          placeholder="Search tickets..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 disabled:cursor-not-allowed"
          disabled={loading || !query.trim()}
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

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
          ) : (
            <span>
              Showing{" "}
              <span className="font-semibold text-slate-100">
                {filteredResults.length}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-100">
                {results.length}
              </span>{" "}
              tickets
            </span>
          )}
        </div>
      </div>

      {/* Results + inspector layout */}
      <div className="mt-2 grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.4fr)] gap-3 items-start">
        {/* Results table */}
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg">
          {results.length === 0 && !loading && !error && (
            <div className="px-4 py-6 text-sm text-slate-400 text-center">
              No tickets yet. Try a different keyword or broaden your search.
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
                    return (
                      <tr
                        key={ticket.id}
                        className={
                          "border-t border-slate-800 cursor-pointer " +
                          (isActive
                            ? "bg-slate-800/90 ring-1 ring-indigo-500"
                            : "hover:bg-slate-800/80")
                        }
                        onClick={() => {
                          setSelectedTicket(ticket);
                          setActiveIndex(index);
                        }}
                      >
                        <td className="px-4 py-2 font-mono text-xs text-slate-400">
                          {ticket.id}
                        </td>
                        <td className="px-4 py-2">
                          {highlightQuery(
                            String(ticket.title ?? ticket.summary ?? ""),
                            query
                          )}
                        </td>
                        <td className="px-4 py-2">
                          <StatusPill status={ticket.status} />
                        </td>
                        <td className="px-4 py-2">{ticket.priority ?? "-"}</td>
                        <td className="px-4 py-2 text-xs text-slate-400">
                          {ticket.created_at ? formatDate(ticket.created_at) : "-"}
                        </td>
                      </tr>
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
                No tickets match the current filters.
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

              {selectedTicket.resolution && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-emerald-300 uppercase tracking-wide mb-1">
                    Resolution
                  </div>
                  <p className="text-sm text-slate-100 whitespace-pre-wrap">
                    {selectedTicket.resolution}
                  </p>
                </div>
              )}
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
