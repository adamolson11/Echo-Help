
import React, { useState, useEffect } from "react";
import AskEchoLogsPanel from "./AskEchoLogsPanel";
import AskEchoFeedbackPanel from "./AskEchoFeedbackPanel";

type UnhelpfulExample = {
  ticket_id: number;
  resolution_notes: string | null;
  created_at: string;
};

type FeedbackInsights = {
  total_feedback: number;
  helped_true: number;
  helped_false: number;
  helped_null: number;
  unhelpful_examples: UnhelpfulExample[];
};

type FeedbackCluster = {
  cluster_index: number;
  size: number;
  example_ticket_ids: number[];
  example_notes: string[];
};

type SnippetPatternSummary = {
  id: number;
  problem_summary: string;
  echo_score: number;
  success_count: number;
  failure_count: number;
  failure_rate: number;
  source_ticket_id?: number | null;
};

type PatternRadarResponse = {
  stats: {
    total_snippets: number;
    total_successes: number;
    total_failures: number;
  };
  top_frequent_snippets: SnippetPatternSummary[];
  top_risky_snippets: SnippetPatternSummary[];
};


export default function InsightsPanel() {
  const [insights, setInsights] = useState<FeedbackInsights | null>(null);
  const [clusters, setClusters] = useState<FeedbackCluster[]>([]);
  const [patternRadar, setPatternRadar] = useState<PatternRadarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInsights = async () => {
      setLoading(true);
      setError(null);

      try {
        const [insightsRes, clustersRes, radarRes] = await Promise.all([
          fetch(`/api/insights/feedback`),
          fetch(`/api/insights/feedback/clusters?n_clusters=5&max_examples_per_cluster=3`),
          fetch(`/api/insights/pattern-radar`),
        ]);

        if (!insightsRes.ok) {
          throw new Error(`Insights error: ${insightsRes.status}`);
        }
        if (!clustersRes.ok) {
          throw new Error(`Clusters error: ${clustersRes.status}`);
        }
        if (!radarRes.ok) {
          throw new Error(`Pattern radar error: ${radarRes.status}`);
        }

        const insightsJson: FeedbackInsights = await insightsRes.json();
        const clustersJson: FeedbackCluster[] = await clustersRes.json();
        const radarJson: PatternRadarResponse = await radarRes.json();

        setInsights(insightsJson);
        setClusters(clustersJson);
        setPatternRadar(radarJson);
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

        {/* Pattern radar quick stats */}
        {patternRadar && (
          <div className="mt-4 border-t border-slate-800 pt-3">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Knowledge Base Stats</h3>
            <div className="text-xs text-slate-300">
              Snippets: {patternRadar.stats.total_snippets} · Successes: {patternRadar.stats.total_successes} · Failures: {patternRadar.stats.total_failures}
            </div>
          </div>
        )}
      </div>

      {/* Clusters card */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Repeating Fix Patterns
        </h2>
        {patternRadar && (
          <div className="mb-3">
            <div className="text-xs font-semibold text-slate-300 mb-1">Most Frequent Issues</div>
            <div className="space-y-2">
              {patternRadar.top_frequent_snippets.map((s) => (
                <div key={s.id} className="rounded-lg bg-slate-800/60 p-2 text-xs">
                  <div className="font-medium text-slate-100">{s.problem_summary || `Snippet ${s.id}`}</div>
                  <div className="text-slate-400">Attempts: {s.success_count + s.failure_count} · Echo: {Math.round((s.echo_score||0)*100)}%</div>
                </div>
              ))}
            </div>

            <div className="mt-3 text-xs font-semibold text-slate-300 mb-1">Riskiest Fixes</div>
            <div className="space-y-2">
              {patternRadar.top_risky_snippets.map((s) => (
                <div key={`r-${s.id}`} className="rounded-lg bg-slate-800/60 p-2 text-xs">
                  <div className="font-medium text-slate-100">{s.problem_summary || `Snippet ${s.id}`}</div>
                  <div className="text-slate-400">Failure rate: {Math.round((s.failure_rate||0)*100)}% · Echo: {Math.round((s.echo_score||0)*100)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
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
