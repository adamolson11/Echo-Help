# Echo-Help Repo Tree Map

Classification artifact only.

- This file records repository classification/support truth.
- This file is not checkpoint proof.
- Canonical checkpoint truth remains PR #58, commit `fa147dd17afa94f2055063c72e6c17eb9dd2b479`, tag `echohelp-v0.1.0-prototype-findings`.

## CORE

Locked prototype ingest/findings path and required dependencies:

- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/ingest.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/schemas/findings.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/schemas/ingest.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/schemas/tickets.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/findings.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/ingest.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/ai/normalize.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/db.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/main.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/models/embedding.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/models/ticket.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/models/ticket_feedback.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/embeddings.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/tickets.py`
- `/home/runner/work/Echo-Help/Echo-Help/sample_data/sample_thread_slack.json`
- `/home/runner/work/Echo-Help/Echo-Help/scripts/ingest_sample_thread.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/conftest.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_ingest_thread.py`

## HOLD

Mixed, broader, or partial feature surfaces not part of checkpoint proof:

- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/ask_echo.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/insights.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/machine.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/patterns.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/routes/snippets.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/api/tickets.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/ask_echo_engine.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/feedback.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/pattern_radar.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/patterns.py`
- `/home/runner/work/Echo-Help/Echo-Help/backend/app/services/ranking_policy.py`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/AskEchoWidget.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/App.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/InsightsPanel.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/Intake.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/Search.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/components/TicketCreateForm.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/pages/AskEchoPage.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/pages/InsightsPage.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/pages/IntakePage.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/pages/SearchPage.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/src/pages/TicketDetailPage.tsx`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_ask_echo.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_ask_echo_contract_surfaces.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_ask_echo_engine_features.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_feedback_patterns_api.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_insights_ask_echo_feedback.py`
- `/home/runner/work/Echo-Help/Echo-Help/tests/test_ticket_create_api.py`

## INFRA

Reproducibility, requirements, CI, repo hygiene, and support artifacts:

- `/home/runner/work/Echo-Help/Echo-Help/.github/workflows/ci.yml`
- `/home/runner/work/Echo-Help/Echo-Help/.github/workflows/pr-guard.yml`
- `/home/runner/work/Echo-Help/Echo-Help/.gitignore`
- `/home/runner/work/Echo-Help/Echo-Help/.pre-commit-config.yaml`
- `/home/runner/work/Echo-Help/Echo-Help/.ruff.toml`
- `/home/runner/work/Echo-Help/Echo-Help/.vscode/settings.json`
- `/home/runner/work/Echo-Help/Echo-Help/ARCHITECTURE.md`
- `/home/runner/work/Echo-Help/Echo-Help/DEV_NOTES.md`
- `/home/runner/work/Echo-Help/Echo-Help/IRON_OPERATING_FRAMEWORK.md`
- `/home/runner/work/Echo-Help/Echo-Help/README.md`
- `/home/runner/work/Echo-Help/Echo-Help/backend/Dockerfile`
- `/home/runner/work/Echo-Help/Echo-Help/backend/echohelp.db`
- `/home/runner/work/Echo-Help/Echo-Help/backend/requirements.txt`
- `/home/runner/work/Echo-Help/Echo-Help/docker-compose.yml`
- `/home/runner/work/Echo-Help/Echo-Help/docs/ARCHITECTURE.md`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/Dockerfile`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/README.md`
- `/home/runner/work/Echo-Help/Echo-Help/frontend/package.json`
- `/home/runner/work/Echo-Help/Echo-Help/package.json`
- `/home/runner/work/Echo-Help/Echo-Help/pyrightconfig.json`
- `/home/runner/work/Echo-Help/Echo-Help/pytest.ini`
- `/home/runner/work/Echo-Help/Echo-Help/requirements.txt`
- `/home/runner/work/Echo-Help/Echo-Help/scripts/dev_check.sh`
- `/home/runner/work/Echo-Help/Echo-Help/scripts/dev_test.sh`
- `/home/runner/work/Echo-Help/Echo-Help/scripts/dev_up_and_test.sh`
- `/home/runner/work/Echo-Help/Echo-Help/scripts/iron-check.sh`

## ARCHIVE

No files are currently classified as ARCHIVE in this pass.
Only confirmed dead or duplicate experiments should move here.
