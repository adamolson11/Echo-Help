import { useMemo, useState } from "react";
import { formatApiError } from "./api/client";
import { postFlywheelOutcome, postFlywheelRecommend } from "./api/endpoints";
import type {
  FlywheelOutcomeStatus,
  FlywheelRecommendResponse,
  FlywheelRecommendation,
} from "./api/types";

type StepSelection = Record<string, boolean>;

const outcomeOptions: Array<{ value: FlywheelOutcomeStatus; label: string; hint: string }> = [
  { value: "resolved", label: "Resolved", hint: "The selected action fixed the issue." },
  { value: "needs_follow_up", label: "Needs follow-up", hint: "Progress was made, but more work is needed." },
  { value: "blocked", label: "Blocked", hint: "The action did not move the issue forward." },
];

function summarizeOutcome(value: FlywheelOutcomeStatus) {
  if (value === "resolved") return "Store the winning move so it becomes reusable.";
  if (value === "needs_follow_up") return "Capture what changed so the next loop starts smarter.";
  return "Record the blocker so the dead end does not repeat.";
}

export default function FlywheelWidget() {
  const [problem, setProblem] = useState("");
  const [plan, setPlan] = useState<FlywheelRecommendResponse | null>(null);
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<StepSelection>({});
  const [outcomeStatus, setOutcomeStatus] = useState<FlywheelOutcomeStatus>("resolved");
  const [executionNotes, setExecutionNotes] = useState("");
  const [reusableLearning, setReusableLearning] = useState("");
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [savingOutcome, setSavingOutcome] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const selectedRecommendation = useMemo<FlywheelRecommendation | null>(() => {
    if (!plan) return null;
    return plan.recommendations.find((item) => item.id === selectedRecommendationId) ?? plan.recommendations[0] ?? null;
  }, [plan, selectedRecommendationId]);

  async function buildPlan() {
    if (!problem.trim()) return;
    setLoadingPlan(true);
    setError(null);
    setSavedMessage(null);
    try {
      const data = await postFlywheelRecommend({ problem: problem.trim() });
      setPlan(data);
      const firstRecommendation = data.recommendations[0] ?? null;
      setSelectedRecommendationId(firstRecommendation?.id ?? null);
      setCompletedSteps({});
      setOutcomeStatus("resolved");
      setExecutionNotes("");
      setReusableLearning("");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoadingPlan(false);
    }
  }

  async function saveOutcome() {
    if (!plan || !selectedRecommendation) return;
    setSavingOutcome(true);
    setError(null);
    setSavedMessage(null);
    try {
      const saved = await postFlywheelOutcome({
        ask_echo_log_id: plan.issue.ask_echo_log_id,
        problem: plan.issue.problem,
        recommendation_id: selectedRecommendation.id,
        recommendation_title: selectedRecommendation.title,
        ticket_id: selectedRecommendation.ticket_id ?? plan.issue.top_ticket_id ?? null,
        outcome_status: outcomeStatus,
        completed_step_ids: selectedRecommendation.steps
          .filter((step) => completedSteps[step.id])
          .map((step) => step.id),
        execution_notes: executionNotes.trim() || null,
        reusable_learning: reusableLearning.trim() || null,
      });
      setSavedMessage(saved.saved.learning_summary);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSavingOutcome(false);
    }
  }

  return (
    <div className="flywheel">
      <section className="flywheel__hero">
        <div>
          <p className="flywheel__eyebrow">Flywheel wedge</p>
          <h2 className="flywheel__title">Problem → 3 options → execute → capture → store</h2>
          <p className="flywheel__subtitle">
            Enter one operator problem, choose the best next action, run it step-by-step, then save the outcome as reusable learning.
          </p>
        </div>

        <div className="flywheel__input-row">
          <textarea
            className="flywheel__textarea"
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
            placeholder="Describe the support problem you want EchoHelp to work through..."
            rows={4}
          />
          <button
            type="button"
            className="flywheel__primary"
            disabled={loadingPlan || !problem.trim()}
            onClick={() => void buildPlan()}
          >
            {loadingPlan ? "Building loop..." : "Recommend 3 next actions"}
          </button>
        </div>
      </section>

      {error && <div className="flywheel__error">{error}</div>}

      {plan && (
        <>
          <section className="flywheel__panel">
            <div className="flywheel__section-heading">
              <h3>Locked contract</h3>
              <span>Ask Echo log #{plan.issue.ask_echo_log_id}</span>
            </div>
            <div className="flywheel__state-row" aria-label="Flywheel states">
              {plan.states.map((state) => (
                <div key={state.id} className={`flywheel__state flywheel__state--${state.status}`}>
                  <span>{state.label}</span>
                  <strong>{state.status}</strong>
                </div>
              ))}
            </div>
            <div className="flywheel__contract-grid">
              <div>
                <h4>In scope</h4>
                <ul>
                  {plan.contract.in_scope.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Deferred</h4>
                <ul>
                  {plan.contract.deferred.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Acceptance</h4>
                <ul>
                  {plan.contract.acceptance_criteria.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          <section className="flywheel__panel">
            <div className="flywheel__section-heading">
              <h3>Issue framing</h3>
              <span>
                {Math.round(plan.issue.confidence * 100)}% confidence · {plan.issue.source_count} source
                {plan.issue.source_count === 1 ? "" : "s"}
              </span>
            </div>
            <p className="flywheel__issue">{plan.issue.problem}</p>
            <p className="flywheel__answer">{plan.issue.answer}</p>
          </section>

          <section className="flywheel__panel">
            <div className="flywheel__section-heading">
              <h3>Choose one of the 3 recommended actions</h3>
              <span>Single-path wedge</span>
            </div>
            <div className="flywheel__card-grid">
              {plan.recommendations.map((recommendation) => {
                const selected = recommendation.id === selectedRecommendation?.id;
                return (
                  <button
                    key={recommendation.id}
                    type="button"
                    className={`flywheel__recommendation ${selected ? "flywheel__recommendation--selected" : ""}`}
                    onClick={() => {
                      setSelectedRecommendationId(recommendation.id);
                      setSavedMessage(null);
                    }}
                  >
                    <div className="flywheel__recommendation-top">
                      <h4>{recommendation.title}</h4>
                      <span>{recommendation.source_label}</span>
                    </div>
                    <p>{recommendation.summary}</p>
                    <small>{recommendation.rationale}</small>
                  </button>
                );
              })}
            </div>
          </section>

          {selectedRecommendation && (
            <>
              <section className="flywheel__panel">
                <div className="flywheel__section-heading">
                  <h3>Execute the selected action</h3>
                  <span>{selectedRecommendation.title}</span>
                </div>
                <ol className="flywheel__steps">
                  {selectedRecommendation.steps.map((step, index) => (
                    <li key={step.id} className="flywheel__step">
                      <label>
                        <input
                          type="checkbox"
                          checked={Boolean(completedSteps[step.id])}
                          onChange={(event) =>
                            setCompletedSteps((current) => ({
                              ...current,
                              [step.id]: event.target.checked,
                            }))
                          }
                        />
                        <div>
                          <strong>
                            {index + 1}. {step.title}
                          </strong>
                          <p>{step.instruction}</p>
                          <small>Expected signal: {step.expected_signal}</small>
                        </div>
                      </label>
                    </li>
                  ))}
                </ol>
              </section>

              <section className="flywheel__panel">
                <div className="flywheel__section-heading">
                  <h3>Capture the outcome and save learning</h3>
                  <span>{summarizeOutcome(outcomeStatus)}</span>
                </div>

                <div className="flywheel__outcome-options">
                  {outcomeOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`flywheel__outcome ${outcomeStatus === option.value ? "flywheel__outcome--selected" : ""}`}
                      onClick={() => setOutcomeStatus(option.value)}
                    >
                      <strong>{option.label}</strong>
                      <span>{option.hint}</span>
                    </button>
                  ))}
                </div>

                <div className="flywheel__capture-grid">
                  <label>
                    <span>What happened when you ran the steps?</span>
                    <textarea
                      className="flywheel__textarea"
                      rows={4}
                      value={executionNotes}
                      onChange={(event) => setExecutionNotes(event.target.value)}
                      placeholder="Capture commands run, observations, blockers, and what changed."
                    />
                  </label>

                  <label>
                    <span>Reusable learning to keep</span>
                    <textarea
                      className="flywheel__textarea"
                      rows={4}
                      value={reusableLearning}
                      onChange={(event) => setReusableLearning(event.target.value)}
                      placeholder="Write the one learning the next operator should inherit."
                    />
                  </label>
                </div>

                <button
                  type="button"
                  className="flywheel__primary"
                  disabled={savingOutcome}
                  onClick={() => void saveOutcome()}
                >
                  {savingOutcome ? "Saving..." : "Save outcome and learning"}
                </button>

                {savedMessage && <div className="flywheel__saved">Saved learning: {savedMessage}</div>}
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
