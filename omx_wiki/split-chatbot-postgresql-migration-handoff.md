---
title: "Split chatbot PostgreSQL migration handoff"
tags: ["split-chatbot", "postgres", "migration", "handoff", "blocked", "ci-cd", "ops"]
created: 2026-05-08T17:06:44.518Z
updated: 2026-05-08T17:06:44.518Z
sources: ["specs/001-split-chatbot-postgres/codex-prompts.md", "specs/001-split-chatbot-postgres/completion-audit.md", "specs/001-split-chatbot-postgres/cutover-runbook.md", "specs/001-split-chatbot-postgres/cutover-dryrun.md", ".cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md", "https://github.com/GC-MapleWind/MSGS_13_B/pull/54", "https://github.com/GC-MapleWind/MSGS_13_B/actions/runs/25567914804", "https://github.com/GC-MapleWind/maplewind-chatbot/issues/1", "https://github.com/GC-MapleWind/MSGS_13_B/issues/55"]
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
- Verify the current `dev` hash with `git ls-remote origin refs/heads/dev`; evidence-only commits may advance the branch without changing implementation state.
- Main `.env.example` includes both `DATABASE_URL` and integration-level `CHATBOT_DATABASE_URL`; the chatbot repo `.env.example` carries the chatbot service-specific environment contract.
- Dev GitHub Actions run `25567914804` for `Backend CI/CD (Docker)` completed with conclusion `success` on `2026-05-08T16:52:37Z`.
- Chatbot repo `GC-MapleWind/maplewind-chatbot` remote `main` is `6c76fbad89bfadaca4fe2eef5edaeca061e9640b`, a docs-only descendant of history-adopting merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e`.
- Chatbot history/archive refs exist:
  - `archive/chinbabang-submission` -> `b357aeaa6bc201fa693c871b31c6ad823b66e4c7`
  - `history-preserved-extract` -> `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`
  - `archive/chinbabang-submission-filtered` -> `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`
- Local dry-run evidence, row counts, tests, and runbooks are recorded under `specs/001-split-chatbot-postgres/`.
- Chatbot README documents required env vars, Kakao webhook endpoint, operations notes, and `scripts/simulate_maesaeng_flow.py` usage.
- Production `docker-compose.yml` is the integrated compose design for T034: it pulls both GHCR images, shares PostgreSQL, and uses separate backend/chatbot DB URLs.

## Remaining blockers

1. Chatbot CI/CD workflows are not present on the remote repo.
   - API check for `repos/GC-MapleWind/maplewind-chatbot/contents/.github/workflows` returned HTTP 404.
   - Current GitHub OAuth scopes are `gist, read:org, repo`; missing required `workflow` scope.
   - Workflow patch is preserved in `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`.
   - Patch recoverability was verified against current chatbot `origin/main` `6c76fbad89bfadaca4fe2eef5edaeca061e9640b`: `git apply --check` passed. Patch SHA-256 is `43baf797f0057ef4b8631370f400929482a9615c60e87be75d8502b42fc8e12e`; it adds `.github/workflows/ci.yml` and `.github/workflows/deploy.yml`.
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
