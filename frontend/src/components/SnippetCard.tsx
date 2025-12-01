import React from "react";

export type SnippetCardProps = {
  id: number;
  title: string | null;
  summary: string | null;
  echo_score: number | null;
  success_count: number;
  failure_count: number;
  ticket_id: string | null;
};

const SnippetCard: React.FC<SnippetCardProps> = ({
  id,
  title,
  summary,
  echo_score,
  success_count,
  failure_count,
  ticket_id,
}) => {
  const echoPercent =
    typeof echo_score === "number" ? `${Math.round((echo_score || 0) * 100)}%` : "—";

  return (
    <div className="border rounded p-2 text-sm bg-slate-900/60">
      <div className="font-medium text-slate-100">
        {title ?? summary ?? `(Snippet #${id})`}
      </div>
      <div className="mt-1 text-xs text-slate-400">
        Echo score: {echoPercent} · Successes: {success_count ?? 0} · Failures: {failure_count ?? 0} · Ticket: {ticket_id ?? "—"}
      </div>
      {summary && (
        <div className="mt-2 text-xs text-slate-200 whitespace-pre-wrap">{summary}</div>
      )}
    </div>
  );
};

export default SnippetCard;
