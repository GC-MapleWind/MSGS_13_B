---
title: "Split chatbot PostgreSQL migration handoff"
tags: ["split-chatbot", "postgres", "migration", "handoff", "blocked", "ci-cd", "ops"]
created: 2026-05-08T17:06:44.518Z
updated: 2026-05-08T17:54:10Z
sources: ["specs/001-split-chatbot-postgres/codex-prompts.md", "specs/001-split-chatbot-postgres/completion-audit.md", "specs/001-split-chatbot-postgres/cutover-runbook.md", "specs/001-split-chatbot-postgres/cutover-dryrun.md", ".cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md", "https://github.com/GC-MapleWind/MSGS_13_B/pull/54", "https://github.com/GC-MapleWind/MSGS_13_B/actions/runs/25567914804", "https://github.com/GC-MapleWind/MSGS_13_B/actions/runs/25570800233", "https://github.com/GC-MapleWind/MSGS_13_B/actions/runs/25571572967", "https://github.com/GC-MapleWind/maplewind-chatbot/issues/1", "https://github.com/GC-MapleWind/MSGS_13_B/issues/55"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# Split chatbot PostgreSQL migration handoff

## Current status

The repo-local implementation and verified development-lane evidence are complete, but the overall migration objective is not complete. Remaining gates are blocked by external authority/ops actions.
`specs/001-split-chatbot-postgres/tasks.md` has an execution status overlay; the original
checkboxes are retained as historical plan text.

## Verified completed evidence

- Main repo PR #54 was merged into `dev` as merge commit `eafce94c3c0930c5dbd420bb95cf455af319215f`.
- This handoff page is published from `dev` and linked from both open blocker issues.
- Latest dependency-cleanup evidence commit is `7d70ea9ae35fc6ddc884b0af88dcf051bff20ff0`; verify the current moving `dev` branch pointer with `git ls-remote origin refs/heads/dev` because evidence-only commits may advance the branch without changing implementation state.
- Main `.env.example` includes both `DATABASE_URL` and integration-level `CHATBOT_DATABASE_URL`; the chatbot repo `.env.example` carries the chatbot service-specific environment contract.
- Chatbot at `dff9dfd2b23be4c5e562e0ca65219df530081b57` now documents the main-repo integrated compose deployment handoff and FR-009 seven-day reverse-proxy compatibility route, and its `src/main.py` lifespan runs Alembic `upgrade head` before serving requests; chatbot ruff, unittest, and a PostgreSQL-backed startup smoke passed after the update.
- Dev GitHub Actions run `25567914804` for `Backend CI/CD (Docker)` completed with conclusion `success` on `2026-05-08T16:52:37Z`.
- Dev GitHub Actions run `25570800233` for `Backend CI/CD (Docker)` completed with conclusion `success` after the FR-007/SC-006 dependency cleanup.
- Dev GitHub Actions run `25571572967` for `Backend CI/CD (Docker)` completed with conclusion `success` after the compose environment isolation fix.
- Main dependency graph now removes `aiosqlite` completely: `pyproject.toml` and `uv.lock` are clean, and runtime-seeding tests run against temporary `postgres:17-alpine`.
- Chatbot repo `GC-MapleWind/maplewind-chatbot` remote `main` is `dff9dfd2b23be4c5e562e0ca65219df530081b57`, a documentation descendant of history-adopting merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e`.
- Archive/history refs now satisfy FR-014:
  - Main `GC-MapleWind/MSGS_13_B` `archive/chinbabang-submission` -> `387cb221da0e18c9bcefe595d3fb119f18f0ea05`
  - Chatbot `GC-MapleWind/maplewind-chatbot` `archive/chinbabang-submission` -> `b357aeaa6bc201fa693c871b31c6ad823b66e4c7`
  - Chatbot `history-preserved-extract` -> `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`
  - Chatbot `archive/chinbabang-submission-filtered` -> `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`
- Local dry-run evidence, row counts, tests, and runbooks are recorded under `specs/001-split-chatbot-postgres/`.
- Chatbot README documents required env vars, Kakao webhook endpoint, operations notes, and `scripts/simulate_maesaeng_flow.py` usage.
- Production `docker-compose.yml` is the integrated compose design for T034: it pulls both GHCR images, shares PostgreSQL, runs Alembic before app startup, and uses isolated backend/chatbot environment blocks. Backend no longer receives `CHATBOT_*`/`GOOGLE_*`; chatbot no longer receives `DATABASE_URL`.
- `specs/001-split-chatbot-postgres/completion-audit.md` now includes explicit FR-001~FR-016 and SC-001~SC-007 coverage, including exact admin isolation evidence for FR-015, with only workflow-credential and production/staging ops gaps remaining.

## Remaining blockers

1. Chatbot CI/CD workflows are not present on the remote repo.
   - API check for `repos/GC-MapleWind/maplewind-chatbot/contents/.github/workflows` returned HTTP 404.
   - Current GitHub OAuth scopes are `gist, read:org, repo`; missing required `workflow` scope.
   - Updated workflow patch is preserved in `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`.
   - Patch recoverability was verified against current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57`: `git apply --check` passed. Patch SHA-256 is `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`; it adds `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` with GHCR `:latest`, `:<full sha>`, `:main`, and `:main-*` tags.
   - Local workflow simulation was re-run against current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57` after the README/T024 lifespan updates: patch application in a temporary worktree, frozen dev sync, ruff, CI-env SQLite unit tests, Alembic offline SQL, Alembic online migration against temporary `postgres:17-alpine`, T030 tag-shape check for `type=sha,format=long,prefix=`, and `docker build -t chatbot-ci-local:workflow-patch-t030 .` all succeeded. Evidence: https://github.com/GC-MapleWind/maplewind-chatbot/issues/1#issuecomment-4408932960. Remaining gap is remote application/execution with a workflow-scoped credential.
   - Tracking issue: `https://github.com/GC-MapleWind/maplewind-chatbot/issues/1`.

2. Production/staging cutover has not been executed.
   - Required work includes production backup, Postgres bring-up, pgloader migration, deployment, Kakao webhook change, SLA/load validation, and 24h/7d monitoring.
   - T042 removal of `migrate_user_student_id_to_username` is also gated by post-cutover/post-run verification; do not remove it before that evidence exists.
   - Tracking issue: `https://github.com/GC-MapleWind/MSGS_13_B/issues/55`.

## Do not mark goal complete until

- Chatbot workflow files are applied to the remote with a workflow-scoped credential/app and CI passes.
- Production/staging cutover and post-cutover verification gates are actually run and evidenced.
- The completion audit maps every `codex-prompts.md`/plan requirement to concrete current evidence with no remaining gaps.

## Safe next actions if authority changes

- With a GitHub credential that includes `workflow`, apply `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch` to `GC-MapleWind/maplewind-chatbot`, push workflows, and verify CI/deploy status.
- With production/staging ops authority, execute `specs/001-split-chatbot-postgres/cutover-runbook.md`, record outputs, update issue #55, and refresh `completion-audit.md`.
