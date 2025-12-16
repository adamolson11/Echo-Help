
import React, { useState, useEffect } from "react";
import AskEchoLogsPanel from "./AskEchoLogsPanel";
import AskEchoFeedbackPanel from "./AskEchoFeedbackPanel";
import {
  getFeedbackPatternsSummary,
  getTicketFeedbackClusters,
  getTicketFeedbackInsights,
  getTicketPatternRadar,
} from "./api/endpoints";
import type {
  FeedbackCluster,
  FeedbackPatternsSummary,
  TicketFeedbackInsights,
  TicketPatternRadarResponse,
} from "./api/types";


export default function InsightsPanel() {
  const [insights, setInsights] = useState<TicketFeedbackInsights | null>(null);
  const [clusters, setClusters] = useState<FeedbackCluster[]>([]);
  const [feedbackPatterns, setFeedbackPatterns] = useState<FeedbackPatternsSummary | null>(null);
  const [patternRadar, setPatternRadar] = useState<TicketPatternRadarResponse | null>(null);
  const [patternRadarDays, setPatternRadarDays] = useState<number>(14);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchPatternRadar(days: number) {
    setPatternRadar(null);
    try {
      const radarJson = await getTicketPatternRadar(days);
      setPatternRadar(radarJson);
    } catch (err: any) {
      console.error("Pattern Radar error:", err);
      setError(err?.message ?? "Failed to load pattern radar");
    }
  }

  useEffect(() => {
    const fetchInsights = async () => {
      setLoading(true);
      setError(null);

      try {
        const [insightsJson, clustersResp, feedbackPatternsJson] = await Promise.all([
          getTicketFeedbackInsights(),
          getTicketFeedbackClusters({ n_clusters: 5, max_examples_per_cluster: 3 }),
          getFeedbackPatternsSummary(30),
        ]);

        const clustersJson: FeedbackCluster[] = clustersResp.clusters ?? [];

        setInsights(insightsJson);
        setClusters(clustersJson);
        setFeedbackPatterns(feedbackPatternsJson);
        void fetchPatternRadar(patternRadarDays);
      } catch (err: any) {
        console.error("Error loading insights:", err);
        setError(err?.message ?? "Failed to load insights");
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, []);

  if (loading && !insights && clusters.length === 0) {
    return (
      <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-300">
        Loading insights...
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-6 rounded-xl border border-red-700 bg-red-950/60 p-4 text-sm text-red-200">
        Failed to load insights: {error}
      </div>
    );
  }

  if (!insights) {
    return null;
  }

  return (
    <React.Fragment>
      <div className="mt-6 grid gap-4 md:grid-cols-[1.2fr,2fr]">
      {/* Stats card */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Ticket Feedback Overview
        </h2>
        <p className="text-2xl font-bold text-slate-50">
          {insights.total_feedback}
          <span className="ml-2 text-sm font-normal text-slate-400">
            total feedback
          </span>
        </p>

        <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-slate-300">
          <div className="rounded-lg bg-slate-800/60 p-2">
            <div className="text-slate-400">KB Helped</div>
            <div className="text-lg font-semibold text-emerald-300">
              {insights.helped_true}
            </div>
          </div>
          <div className="rounded-lg bg-slate-800/60 p-2">
            <div className="text-slate-400">KB Didn&apos;t Help</div>
            <div className="text-lg font-semibold text-amber-300">
              {insights.helped_false}
            </div>
          </div>
          <div className="rounded-lg bg-slate-800/60 p-2">
            <div className="text-slate-400">Unknown</div>
            <div className="text-lg font-semibold text-slate-200">
              {insights.helped_null}
            </div>
          </div>
        </div>

        <div className="mt-4">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Recent unhelpful cases
          </h3>
          <div className="space-y-2 text-xs text-slate-300 max-h-40 overflow-y-auto pr-1">
            {insights.unhelpful_examples.length === 0 && (
              <div className="text-slate-500">
                No &quot;KB didn&apos;t help&quot; feedback yet.
              </div>
            )}
            {insights.unhelpful_examples.map((ex) => (
              <div
                key={`${ex.ticket_id}-${ex.created_at}`}
                className="rounded-lg bg-slate-800/60 p-2"
              >
                <div className="mb-1 text-[11px] text-slate-400">
                  Ticket #{ex.ticket_id} • {new Date(ex.created_at).toLocaleString()}
                </div>
                <div className="text-[12px]">
                  {ex.resolution_notes ?? "(no notes provided)"}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pattern radar quick stats (ticket-based) */}
        <div className="mt-4 border-t border-slate-800 pt-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Ticket Pattern Radar
            </h3>
            <select
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200"
              value={patternRadarDays}
              onChange={(e) => {
                const days = Number(e.target.value) || 14;
                setPatternRadarDays(days);
                void fetchPatternRadar(days);
              }}
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </div>

          {!patternRadar && (
            <div className="text-xs text-slate-400">Loading ticket patterns…</div>
          )}

          {patternRadar && (
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex flex-col gap-0.5 text-[11px] text-slate-400">
                <span className="font-semibold text-slate-200">
                  Ticket Pattern Radar {patternRadar.meta?.version ? `(v${patternRadar.meta.version})` : ""}
                </span>
                <span>
                  {patternRadar.stats.total_tickets} tickets in the last {patternRadar.stats.window_days} days
                </span>
                {patternRadar.stats.last_ticket_at && (
                  <span>
                    Last signal: {new Date(patternRadar.stats.last_ticket_at).toLocaleString()}
                  </span>
                )}
              </div>

              <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  Top Keywords
                </div>
                {patternRadar.top_keywords.length === 0 ? (
                  <div className="text-[11px] text-slate-500">
                    No clear keyword patterns detected in this window.
                  </div>
                ) : (
                  <ul className="grid grid-cols-2 gap-1 text-[11px]">
                    {patternRadar.top_keywords.slice(0, 10).map((k) => (
                      <li key={k.keyword} className="flex justify-between">
                        <span className="truncate pr-2">{k.keyword}</span>
                        <span className="text-slate-400">{k.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  Frequent Titles
                </div>
                {patternRadar.frequent_titles.length === 0 ? (
                  <div className="text-[11px] text-slate-500">
                    No repeating titles found in this window.
                  </div>
                ) : (
                  <ul className="space-y-1 text-[11px]">
                    {patternRadar.frequent_titles.slice(0, 8).map((t, idx) => (
                      <li key={`${t.title}-${idx}`} className="flex justify-between">
                        <span className="truncate pr-2">{t.title}</span>
                        <span className="text-slate-400">{t.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {patternRadar.top_keywords.length === 0 &&
                patternRadar.frequent_titles.length === 0 && (
                  <div className="text-[11px] text-slate-500">
                    No clear patterns detected in this window yet.
                  </div>
                )}
            </div>
          )}
        </div>
      </div>

      {/* Feedback Patterns card */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Feedback Patterns {feedbackPatterns?.meta?.version ? `(v${feedbackPatterns.meta.version})` : ""}
        </h2>
        {feedbackPatterns ? (
          <div className="space-y-2 text-xs text-slate-300">
            <div>
              {feedbackPatterns.stats.total_feedback} feedback events in the last {feedbackPatterns.stats.window_days} days
            </div>
            <div className="flex gap-3 text-[11px] text-slate-200">
              <span className="text-emerald-300">Positive: {feedbackPatterns.stats.positive}</span>
              <span className="text-amber-300">Negative: {feedbackPatterns.stats.negative}</span>
            </div>
            {feedbackPatterns.stats.total_feedback === 0 && (
              <div className="text-[11px] text-slate-500">
                No feedback received in this window yet.
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-slate-400">Loading feedback patterns…</div>
        )}
      </div>

      {/* Clusters card */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Repeating Fix Patterns
        </h2>
        {/* Existing snippet-based pattern radar now focuses on clusters only */}
        {clusters.length === 0 ? (
          <div className="text-sm text-slate-400">
            Not enough feedback yet to detect patterns. As more techs add notes,
            you&apos;ll start seeing clusters here.
          </div>
        ) : (
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {clusters.map((cluster) => (
              <div
                key={cluster.cluster_index}
                className="rounded-lg bg-slate-800/60 p-3"
              >
                <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                  <span>Cluster #{cluster.cluster_index}</span>
                  <span>{cluster.size} related fixes</span>
                </div>
                <ul className="space-y-1 text-[12px] text-slate-200">
                  {cluster.example_notes.map((note, idx) => (
                    <li
                      key={`${cluster.cluster_index}-${idx}`}
                      className="rounded bg-slate-900/70 p-2"
                    >
                      <div className="mb-1 text-[11px] text-slate-400">
                        Ticket #{cluster.example_ticket_ids[idx]}
                      </div>
                      <div>{note}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
      <AskEchoLogsPanel />
      <div className="mt-4">
        <AskEchoFeedbackPanel />
      </div>
    </React.Fragment>
  );
}
