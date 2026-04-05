# EchoHelp Flywheel Wedge Contract

## Purpose

The wedge is the smallest complete loop that turns a support issue into reusable resolution memory.

Canonical surface today:
- `/#/flywheel` = visible wedge
- `/#/ask` = secondary inspection / answer-trail surface

Design bias:
- Treat ticketing, analytics, monitoring, and pattern-detection systems as input sources.
- The flywheel owns interpretation, prioritization, recommendation, action guidance, outcome capture, and reusable learning.
- Build custom only where it creates leverage or clear product distinction.
- Prefer integrating commodity upstream capabilities over rebuilding them inside the flywheel.

Loop:
1. Operator enters an issue.
2. Echo returns exactly 3 recommended next actions.
3. Operator selects one action and executes explicit steps.
4. Operator records the outcome.
5. Operator saves reusable learning for the next similar issue.

## Canonical Objects

- `AskEchoResponse.flywheel`
- `AskEchoFlywheel.state`
- `AskEchoFlywheel.recommendations[3]`
- `AskEchoFeedbackCreate.selected_recommendation_id`
- `AskEchoFeedbackCreate.selected_recommendation_title`
- `AskEchoFeedbackCreate.outcome`
- `AskEchoFeedbackCreate.outcome_notes`
- `AskEchoFeedbackCreate.reusable_learning`

## Required States

- `recommendations_ready`: Echo has returned 3 next actions.
- `action_selected`: Operator picked the action to run.
- `outcome_recorded`: Operator captured what happened.
- `learning_captured`: Operator saved reusable learning.

## In Scope

- Ask Echo response includes explicit flywheel contract objects.
- The flywheel consumes upstream search, ticket, KB, and signal inputs to support decisioning.
- Backend stores structured wedge feedback fields.
- Frontend shows issue input, 3 recommendation cards, selected action steps, outcome capture, and reusable learning.
- Tests cover contract shape, persistence, and visible flow.

## Deferred

- Rebuilding commodity analytics, monitoring, or queue-pattern systems inside the flywheel.
- Full mobile-specific UX.
- Multi-user workflow orchestration.
- Rich recommendation generation from LLM planning.
- Separate reusable-learning entity/model beyond Ask Echo feedback persistence.
- Cross-ticket follow-up automation.

## Acceptance Criteria

- A user can enter a problem and receive exactly 3 recommendation cards.
- Selecting a card reveals actionable steps and supporting source context.
- The UI captures one explicit outcome and reusable learning text.
- Saving the loop persists the selected recommendation, outcome, and reusable learning in backend feedback storage.
- Backend tests verify the flywheel contract and structured feedback persistence.
- Frontend end-to-end tests verify the visible wedge flow.