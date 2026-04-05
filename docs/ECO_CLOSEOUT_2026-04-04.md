# E.C.O Closeout 2026-04-04

STATE:
- Product direction is currently E.C.O. (Executive Command Operations).
- Canonical visible wedge surface is `/#/flywheel`.
- Secondary inspection surface is `/#/ask`.
- The active loop in repo truth is: input/search -> choose action -> run steps -> capture outcome -> save learning.
- Working design bias is: signals in -> decisioning layer -> action guidance -> outcome memory.
- Existing analytics, ticket, and monitoring systems are treated as inputs, not as flywheel features to rebuild.
- Acceptance sentence for the current closeout is: "We will preserve one visible E.C.O loop, verify it is undamaged, and add one server-side OpenAI provider seam without redesign."
- OpenAI provider seam is the active server-side implementation target.
- Jira seam remains deferred until the OpenAI seam is validated.

CAUSE:
- The branch contains valid Ask Echo wedge work plus unrelated ticket/intake/environment residue.
- README and branch state could otherwise be read as broader than the verified wedge surface.

PRESERVED:
- The visible wedge shell is now `/#/flywheel`.
- `/#/ask` remains available as a secondary inspection surface.
- The flywheel contract in `docs/FLYWHEEL_WEDGE.md` remains the canonical loop definition.
- Current wedge implementation surface remains limited to the flywheel route wrapper, Ask Echo contract/persistence, the provider seam in backend services, and focused wedge tests.
- Pattern, analytics, and monitoring surfaces remain adjacent inputs or separate endpoints rather than flywheel scope.

DEFERRED:
- Intake-only wedge paths.
- Mobile expansion.
- Ticket creation lane.
- Environment reconciliation work.
- Jira seam implementation until after OpenAI validation.

LESSONS:
- Branch truth must be stated in exact files, not implied from intent.
- Shared frontend API/type files can carry both wedge and non-wedge residue, so they must be reviewed field-by-field.
- Documentation should point to the verified canonical surface, not aspirational product breadth.
- Commodity upstream capabilities should be integrated where possible; the flywheel should stay focused on decisioning and learning.

CANONICAL SURFACE:
- Flywheel page: `frontend/src/pages/FlywheelPage.tsx`
- Flywheel widget wrapper: `frontend/src/FlywheelWidget.tsx`
- Ask Echo wedge UI implementation: `frontend/src/AskEchoWidget.tsx`
- Ask Echo wedge styling: `frontend/src/index.css`
- Ask Echo wedge e2e test: `frontend/e2e/mvp-flows.spec.ts`
- Ask Echo wedge contract: `backend/app/schemas/ask_echo.py`
- Ask Echo feedback persistence: `backend/app/api/routes/ask_echo.py`, `backend/app/models/ask_echo_feedback.py`, `backend/app/schemas/ask_echo_feedback.py`

OPEN RISKS:
- Current working tree is dirty and includes unrelated files outside the wedge path.
- `frontend/src/api/types.ts` and `frontend/src/api/endpoints.ts` contain both wedge fields and unrelated ticket-create additions; those need careful PR scoping.
- The current flywheel page is still a thin wrapper around Ask Echo UI, so canonical routing is frozen before full surface separation.
- README still contains older duplicated platform framing below the verified direction note.
- Optional environment dependencies for semantic clustering remain a separate stability concern outside the wedge path.

TOMORROW SEED:
- After the provider seam is validated, keep the flywheel surface frozen and only then evaluate the Jira seam.
- Keep memory-first behavior and defer Jira integration to a read-only seam after provider stabilization.