
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
    <details className="ask-echo__reasoning">
      <summary className="ask-echo__reasoning-summary">
        <span>Why Echo chose this answer</span>
        {typeof reasoning.echo_score === "number" && (
          <span className="ask-echo__badge ask-echo__badge--soft">
            EchoScore {reasoning.echo_score.toFixed(2)}
          </span>
        )}
      </summary>
      <div className="ask-echo__reasoning-body">
        {typeof reasoning.echo_score === "number" && (
          <p className="ask-echo__reasoning-note">
            Candidate snippets are ranked below. The selected ones were used to ground the response.
          </p>
        )}

        {candidates.length === 0 && (
          <p className="ask-echo__reasoning-empty">No snippet reasoning available for this answer.</p>
        )}

        {candidates.map((c) => {
          const selected = chosenIds.includes(c.id);
          return (
            <div key={c.id} className="ask-echo__reasoning-item">
              <div>
                <div className="ask-echo__reasoning-item-title">{c.title ?? `Snippet #${c.id}`}</div>
                <div className="ask-echo__reasoning-item-score">
                  Score: {typeof c.score === "number" ? c.score.toFixed(3) : "N/A"}
                </div>
              </div>
              {selected && (
                <span className="ask-echo__badge ask-echo__badge--success">
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
