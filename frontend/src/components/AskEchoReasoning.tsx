
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
    <details className="ask-echo-reasoning">
      <summary className="ask-echo-reasoning__summary">
        <span>Why Echo chose this answer</span>
        <span className="ask-echo-reasoning__summary-note">Inspect ranking context</span>
      </summary>
      <div className="ask-echo-reasoning__body">
        {typeof reasoning.echo_score === "number" && (
          <div className="ask-echo-reasoning__score">EchoScore {reasoning.echo_score.toFixed(2)}</div>
        )}

        {candidates.length === 0 && (
          <p className="ask-echo-reasoning__empty">No snippet reasoning available for this answer.</p>
        )}

        {candidates.map((c) => {
          const selected = chosenIds.includes(c.id);
          return (
            <div
              key={c.id}
              className="ask-echo-reasoning__candidate"
            >
              <div className="ask-echo-reasoning__candidate-copy">
                <div className="ask-echo-reasoning__candidate-title">{c.title ?? `Snippet #${c.id}`}</div>
                <div className="ask-echo-reasoning__candidate-score">
                  Score: {typeof c.score === "number" ? c.score.toFixed(3) : "N/A"}
                </div>
              </div>
              {selected && (
                <span className="ask-echo-reasoning__used">
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
