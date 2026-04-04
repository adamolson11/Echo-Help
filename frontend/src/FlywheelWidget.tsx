import { useMemo, useState } from "react";
import { formatApiError } from "./api/client";
import { postFlywheelOutcome, postFlywheelRecommend } from "./api/endpoints";
import type {
  FlywheelOutcomeStatus,
  FlywheelRecommendResponse,
  FlywheelRecommendation,
  FlywheelState,
} from "./api/types";

type StepSelection = Record<string, boolean>;

const outcomeOptions: Array<{
  value: FlywheelOutcomeStatus;
  label: string;
  hint: string;
}> = [
  { value: "resolved", label: "Resolved", hint: "This path fixed the issue." },
  { value: "needs_follow_up", label: "Needs follow-up", hint: "This helped, but more work is needed." },
  { value: "blocked", label: "Blocked", hint: "This path did not move the issue forward." },
];

const stageCopy: Record<FlywheelState["id"], string> = {
  input: "Type the issue",
  recommend: "Review the 3 actions",
  execute: "Run one path",
  capture: "Record what happened",
  store: "Save learning",
};

function learningPlaceholder(outcomeStatus: FlywheelOutcomeStatus) {
  if (outcomeStatus === "resolved") {
    return "What should the next operator repeat because it worked?";
  }
  if (outcomeStatus === "needs_follow_up") {
    return "What should the next operator know before taking the next step?";
  }
  return "What blocker or dead end should Echo remember next time?";
}

function summarizeDeferred(items: string[]) {
  if (items.length === 0) return "No extra paths are included in this UX pass.";
  if (items.length === 1) return `${items[0]}.`;
  return `${items[0]} and ${items[1]}.`;
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

  const completedStepCount = useMemo(() => {
    if (!selectedRecommendation) return 0;
    return selectedRecommendation.steps.filter((step) => completedSteps[step.id]).length;
  }, [completedSteps, selectedRecommendation]);

  const currentStageId: FlywheelState["id"] = selectedRecommendation ? "execute" : plan ? "recommend" : "input";

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
          <p className="flywheel__eyebrow">Ask Echo wedge</p>
          <h2 className="flywheel__title">Search the issue, choose one action, then save what happened.</h2>
          <p className="flywheel__subtitle">
            Ask Echo gives you 3 next actions. Pick one, run the steps, record the result, and save the learning for the next operator.
          </p>
        </div>

        <div className="flywheel__mini-flow" aria-label="Ask Echo loop">
          <span>1. Search</span>
          <span>2. Choose</span>
          <span>3. Run</span>
          <span>4. Save</span>
        </div>

        <label className="flywheel__field">
          <span className="flywheel__field-label">Describe the issue</span>
          <textarea
            className="flywheel__textarea"
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
            placeholder="Example: VPN login fails after a password reset and MFA re-prompt."
            rows={4}
          />
        </label>

        <div className="flywheel__hero-actions">
          <button
            type="button"
            className="flywheel__primary"
            disabled={loadingPlan || !problem.trim()}
            onClick={() => void buildPlan()}
          >
            {loadingPlan ? "Searching..." : "Find 3 next actions"}
          </button>
          <p className="flywheel__helper">Echo keeps this on one path: search, choose, run, capture, and save.</p>
        </div>
      </section>

      {error && <div className="flywheel__error">{error}</div>}

      {plan && (
        <>
          <section className="flywheel__panel flywheel__panel--compact">
            <div className="flywheel__section-heading">
              <h3>How this run works</h3>
              <span>Ask Echo log #{plan.issue.ask_echo_log_id}</span>
            </div>

            <div className="flywheel__state-row" aria-label="Flywheel states">
              {plan.states.map((state) => {
                const isActive = state.id === currentStageId;
                return (
                  <div
                    key={state.id}
                    className={`flywheel__state flywheel__state--${isActive ? "current" : state.status}`}
                  >
                    <div>
                      <strong>{stageCopy[state.id]}</strong>
                      <span>{state.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flywheel__summary-grid">
              <div className="flywheel__summary-card">
                <strong>In this pass</strong>
                <p>One issue in, 3 actions out, one selected path, one saved learning.</p>
              </div>
              <div className="flywheel__summary-card">
                <strong>Not in this pass</strong>
                <p>{summarizeDeferred(plan.contract.deferred)}</p>
              </div>
              <div className="flywheel__summary-card">
                <strong>Done when</strong>
                <p>The operator can explain what Echo found, what they tried, and what should happen next.</p>
              </div>
            </div>
          </section>

          <section className="flywheel__panel">
            <div className="flywheel__section-heading">
              <h3>1. What Echo found</h3>
              <span>
                {Math.round(plan.issue.confidence * 100)}% confidence · {plan.issue.source_count} source
                {plan.issue.source_count === 1 ? "" : "s"}
              </span>
            </div>
            <p className="flywheel__issue">{plan.issue.problem}</p>
            <div className="flywheel__answer-card">
              <strong className="flywheel__answer-label">Best answer so far</strong>
              <p className="flywheel__answer">{plan.issue.answer}</p>
            </div>
            <p className="flywheel__helper">If this looks weak, choose the action that gathers better evidence before changing anything else.</p>
          </section>

          <section className="flywheel__panel">
            <div className="flywheel__section-heading">
              <h3>2. Choose your next action</h3>
              <span>Click one card to continue</span>
            </div>
            <div className="flywheel__card-grid">
              {plan.recommendations.map((recommendation, index) => {
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
                      <span className="flywheel__recommendation-number">Option {index + 1}</span>
                      {selected && <span className="flywheel__selected-pill">Selected</span>}
                    </div>
                    <h4>{recommendation.title}</h4>
                    <p>{recommendation.summary}</p>
                    <div className="flywheel__recommendation-meta">
                      <span>Why this: {recommendation.rationale}</span>
                      <span>Based on: {recommendation.source_label}</span>
                    </div>
                    <span className="flywheel__recommendation-cta">
                      {selected ? "Selected path — run the steps below" : "Click to choose this path"}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {selectedRecommendation && (
            <>
              <section className="flywheel__panel">
                <div className="flywheel__section-heading">
                  <h3>3. Run the selected path</h3>
                  <span>
                    {completedStepCount}/{selectedRecommendation.steps.length} steps complete
                  </span>
                </div>

                <div className="flywheel__selected-path">
                  <strong>{selectedRecommendation.title}</strong>
                  <span>Next click: check each step as you complete it.</span>
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
                          <div className="flywheel__step-title-row">
                            <strong>
                              Step {index + 1}: {step.title}
                            </strong>
                            {completedSteps[step.id] && <span className="flywheel__step-done">Done</span>}
                          </div>
                          <p>{step.instruction}</p>
                          <small>Look for: {step.expected_signal}</small>
                        </div>
                      </label>
                    </li>
                  ))}
                </ol>
              </section>

              <section className="flywheel__panel">
                <div className="flywheel__section-heading">
                  <h3>4. Capture the result</h3>
                  <span>Choose what happened, then save the learning</span>
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
                  <label className="flywheel__field">
                    <span className="flywheel__field-label">What happened?</span>
                    <textarea
                      className="flywheel__textarea"
                      rows={4}
                      value={executionNotes}
                      onChange={(event) => setExecutionNotes(event.target.value)}
                      placeholder="Write the short story: what you ran, what changed, and what is still true."
                    />
                  </label>

                  <label className="flywheel__field">
                    <span className="flywheel__field-label">Save learning for next time</span>
                    <textarea
                      className="flywheel__textarea"
                      rows={4}
                      value={reusableLearning}
                      onChange={(event) => setReusableLearning(event.target.value)}
                      placeholder={learningPlaceholder(outcomeStatus)}
                    />
                    <span className="flywheel__field-help">
                      This note is stored with this Ask Echo run so future operators can reuse what worked or avoid what failed.
                    </span>
                  </label>
                </div>

                <button
                  type="button"
                  className="flywheel__primary"
                  disabled={savingOutcome}
                  onClick={() => void saveOutcome()}
                >
                  {savingOutcome ? "Saving..." : "Save learning"}
                </button>

                {savedMessage && (
                  <div className="flywheel__saved">
                    Saved. Echo can reuse this note next time: <strong>{savedMessage}</strong>
                  </div>
                )}
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
