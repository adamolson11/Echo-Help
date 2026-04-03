# IRON OPERATING FRAMEWORK

Purpose
- Provide a short, copy-pasteable operating contract and practical rules to constrain "Iron" (an assistant/agent) when making repo changes.
- Include strict modes (Read-only / Yellow / Green), a short git workflow to limit blast radius, and prompt templates the user can paste to the agent.

How to use
- When Iron starts freelancing, paste the relevant section (e.g. "AGENT IRON – OPERATING RULES") into the chat and add: "Re-read and follow these rules".
- Use the modes to select the allowed permission scope before asking for edits.

AGENT IRON – OPERATING RULES (MUST FOLLOW)

1. Scope
- Only work on EXACTLY what I ask for in this message.
- Do NOT continue to iterate or propose next steps unless I explicitly ask.

2. Safety
- NEVER change more than the files I name.
- NEVER touch `backend/app/db.py`, `backend/app/main.py`, or tests unless I explicitly say so.
- Prefer minimal diffs: change only the lines required for the request.

3. Workflow
- BEFORE changing anything: summarize in bullet points what you WILL change.
- WHEN changing code: use a single Apply Patch block per file. Keep logic untouched unless instructed.
- AFTER changes: show the list of affected file paths and a two-line summary of what changed.
- Run ONLY the commands I explicitly request (e.g. `npm --prefix frontend run build` or a single `pytest` file). Do not run extra commands.

4. Don’ts
- Do NOT refactor unrelated code for cleanliness.
- Do NOT create new branches or commits unless I give explicit permission.
- Do NOT run the full test suite unless I explicitly ask.

If ambiguous:
- Stop and ask for clarification instead of guessing.


IRON MODES (Copy the mode name into the request to constrain Iron)

Red Mode — Read-Only (analysis)
- Permitted: read files, run static checks listed explicitly (e.g. `npx tsc --noEmit`), return findings.
- Forbidden: Apply Patch, git checkout, git commit, start servers, run tests.
- Prompt prefix suggestion: "IRON READ-ONLY MODE: analyze `path/to/file` and explain the broken JSX. No edits." 

Yellow Mode — Single-file surgical patch
- Permitted: edit exactly one file (user must name it), run explicit commands (e.g. `npm --prefix frontend run build`).
- Requirements before change: show a 1-2 bullet summary of planned change, wait for user confirmation.
- Patch rules: single Apply Patch per file, minimal line changes, do not change unrelated imports.
- Prompt prefix suggestion: "IRON YELLOW MODE: Fix only `frontend/src/Search.tsx`. Do not edit any other files. After patch run: `npm --prefix frontend run build`."

Green Mode — Broader changes allowed
- Permitted: multiple files, refactors, tests, and build runs, but only when user explicitly requests.
- Still obey Safety: do not change db.py/main.py or tests unless user permits.


GIT WORKFLOW (recommended guard rails the user should run before asking Iron to edit)

1. Create a feature branch (user-run):

```bash
git checkout -b feature/iron-<short-purpose>
```

2. Commit a checkpoint before big changes:

```bash
git add .
git commit -m "Checkpoint: before Iron <task>"
```

3. If Iron misbehaves, two quick recoveries:
- Inspect what Iron changed:

```bash
git --no-pager diff --name-only HEAD
```

- Restore a single file (user decision):

```bash
git restore path/to/file
```

- Or reset to checkpoint (user decision, destructive):

```bash
git reset --hard HEAD
```


PROMPT TEMPLATES (copy-paste)

1) Analysis-only (Red Mode):

```text
IRON READ-ONLY MODE:
- Only read files. No Apply Patch, no git commands, no builds.
- Analyze `frontend/src/Search.tsx` and report the exact JSX parse error and three minimal fixes I could apply.
```

2) Single-file surgical (Yellow Mode):

```text
IRON YELLOW MODE: Fix `frontend/src/Search.tsx`
- BEFORE EDIT: show 3 bullet summary of EXACT lines to change.
- AFTER EDIT: run `npm --prefix frontend run build` and show first 20 lines of output.
- Do NOT change any other files.
```

3) Broader (Green Mode — only when explicitly allowed):

```text
IRON GREEN MODE: You may update multiple frontend files to improve UI consistency.
- BEFORE EDIT: list files and a one-line reason for each.
- AFTER EDIT: run `npm --prefix frontend run build` and `pytest -q tests/test_search.py` (only this test).
```


CHECKLIST FOR SENDING A REQUEST TO IRON

- [ ] Mode selected and stated (Red / Yellow / Green).
- [ ] Exact file path(s) listed.
- [ ] Exact commands allowed after changes (if any).
- [ ] Confirm you have a git checkpoint branch (recommended).


SESSION HANDOFF PACKET

Before closing a session or handing to another agent, capture:

- Current branch and `git status --short` (or run `./scripts/iron-check.sh`).
- The exact files changed and the reason each one moved.
- The exact validation commands already run, plus any commands skipped because dependencies were not installed yet.
- Any unresolved blockers or intentionally deferred refactors so the next agent does not rediscover them.


EXAMPLE — Minimal request you can paste:

```text
IRON YELLOW MODE: Fix only `frontend/src/Search.tsx`
- Change: fix unterminated JSX by restoring the original closing tags around the inspector footer.
- After patch run: `npm --prefix frontend run build`.
- Do not modify any other files. Show me planned changes before patch.
```


ADDITIONAL NOTES

- This file is intentionally short and prescriptive so it's easy to copy/paste into the chat with Iron before each risky request.
- Use the included `scripts/iron-check.sh` helper to print the current branch, short status, and recent commits before risky edits.


---
Created: IRON_OPERATING_FRAMEWORK.md — add, edit, or ask me to tailor the language for your team.
