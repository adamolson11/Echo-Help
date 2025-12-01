
type ReasoningSnippetCandidate = {
  id: number;
  title?: string | null;
  score?: number | null;
};

export type AskEchoReasoning = {
  candidate_snippets?: ReasoningSnippetCandidate[];
  chosen_snippet_ids?: number[];
  echo_score?: number | null;
};

type Props = {
  reasoning: AskEchoReasoning | undefined | null;
};

export default function AskEchoReasoningDetails({ reasoning }: Props) {
  if (!reasoning) return null;

  const candidates = reasoning.candidate_snippets || [];
  const chosenIds = reasoning.chosen_snippet_ids || [];

  return (
    <details className="mt-3 rounded-md border border-slate-700 bg-slate-900/40 p-3">
      <summary className="cursor-pointer text-xs font-semibold text-slate-200">
        Why Echo chose this answer
      </summary>
      <div className="mt-2 space-y-2 text-xs text-slate-200">
        {typeof reasoning.echo_score === "number" && (
          <p className="text-[11px] text-slate-400">
            EchoScore: {reasoning.echo_score.toFixed(2)}
          </p>
        )}

        {candidates.length === 0 && (
          <p className="text-slate-400">No snippet reasoning available for this answer.</p>
        )}

        {candidates.map((c) => {
          const selected = chosenIds.includes(c.id);
          return (
            <div
              key={c.id}
              className="flex items-center justify-between rounded bg-slate-900/60 px-2 py-1"
            >
              <div>
                <div className="font-medium">{c.title ?? `Snippet #${c.id}`}</div>
                <div className="text-[11px] text-slate-400">
                  Score: {typeof c.score === "number" ? c.score.toFixed(3) : "N/A"}
                </div>
              </div>
              {selected && (
                <span className="rounded-full bg-emerald-600/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-50">
                  Used
                </span>
              )}
            </div>
          );
        })}
      </div>
    </details>
  );
}
