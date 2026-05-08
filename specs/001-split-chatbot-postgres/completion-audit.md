# Completion Audit — split-chatbot-postgres

Date: 2026-05-09

## Objective restated

Use the SDD artifacts in `specs/001-split-chatbot-postgres/`, `codex-prompts.md`, and `.cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md` to split the Kakao chatbot into `GC-MapleWind/maplewind-chatbot` and migrate both the main backend and chatbot from SQLite to one PostgreSQL 17 instance with two databases (`maplewind`, `chatbot`) while preserving data.

## Prompt-to-artifact checklist

| Requirement / task | Evidence inspected | Status |
| --- | --- | --- |
| T005 dependencies: main repo has asyncpg, psycopg, alembic and no runtime Google chatbot deps | `pyproject.toml`; `grep` for `gspread`, `google-api-python-client`, `googleapiclient` in main `src`/`pyproject.toml` | PASS for runtime; `aiosqlite` remains in dev dependencies for SQLite tests |
| T006/T007 PostgreSQL service and two DB init SQL | `docker-compose.yml`, `docker-compose.dev.yml`, `scripts/postgres-init.sql`; dry-run DB creation via `cat scripts/postgres-init.sql | docker exec ... psql` | PASS |
| T008 `.env.example` Postgres variables | `.env.example` includes `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, and integration-level `CHATBOT_DATABASE_URL`; chatbot repo `.env.example` also requires `CHATBOT_DATABASE_URL` | PASS |
| T009 main DB fail-fast and SQLite PRAGMA guard | `src/database.py` | PASS |
| T010/T011 chatbot DB/model Postgres compatibility | moved to `../maplewind-chatbot/src/database.py`, `src/models/chatbot.py`, `src/alembic/versions/0001_initial.py` | PASS locally |
| T012 legacy SQLite migration guard | `src/main.py` checks dialect before PRAGMA | PASS |
| T013 main Alembic metadata only | `src/alembic/env.py`, `src/alembic/versions/0001_initial.py`; online dry-run against PostgreSQL | PASS |
| T014/T015 pgloader wrapper and local row-count verification | `scripts/migrate_sqlite_to_postgres.sh`; dry-run with `dimitri/pgloader:latest`; row-count output in `cutover-dryrun.md` | PASS |
| T016/T017 chatbot model DDL and event date tests | chatbot Alembic online dry-run; `uv run python -m unittest discover -s tests -v` in chatbot repo | PASS |
| T018 메생결산 simulation | `../maplewind-chatbot/scripts/simulate_maesaeng_flow.py`; SQLite fallback and PostgreSQL-backed run against temporary `postgres:17-alpine` container both called `register_final_data` once, sent callback once, and cleaned the temporary session | PASS |
| T019 dry-run report with row counts and sample comparisons | `specs/001-split-chatbot-postgres/cutover-dryrun.md` | PASS for local SQLite copies |
| T020 cutover runbook with rollback | `specs/001-split-chatbot-postgres/cutover-runbook.md` | PASS |
| T021 git history-preserving extraction | Local filtered repo `../chatbot-history-extract` has 42 commits; chatbot remote `main` now points to merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e` with parents `b3d80a9` and filtered-history commit `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`; `git diff HEAD^1 HEAD` is empty, preserving the runtime tree | PASS |
| T022-T028 chatbot repo structure/env/Dockerfile/dev compose | `../maplewind-chatbot` file tree; runtime commit `b3d80a935f82427d13432ad56107dd51189931e0` pushed to remote `main` | PASS |
| T029/T030 chatbot CI/CD workflows | local branch `workflows-pending-scope` commit `6ab860c` contains `.github/workflows/ci.yml` and `deploy.yml`; direct push rejected by GitHub token missing `workflow` scope; patch preserved in `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`; patch applies cleanly to chatbot `origin/main` `5e6c20df8b0c047f716ad02be249a99ce367838e` via `git apply --check` | GAP for remote workflow availability |
| T031 push new repo + archive branch | chatbot remote `main` now points to history-adopting merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e`; `archive/chinbabang-submission` pushed at `b357aea`; filtered-history evidence branches remain at `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`; workflow branch push rejected by remote workflow-scope policy | PARTIAL only for workflow branch |
| T032/T033 main repo cleanup | main `src/` has no chatbot/google refs; tracked chatbot files absent; main tests pass | PASS |
| T034-T037 SLA isolation | requires deployed/staging environment and load test | GAP |
| T038-T043 production cutover/polish | requires production backup, deployment, Kakao webhook update, monitoring, backup retention, and the post-run T042 removal decision for `migrate_user_student_id_to_username` | GAP/manual ops |

## Verification commands run

### Main repo

- `bash -n scripts/migrate_sqlite_to_postgres.sh` — PASS.
- `uv run ruff check .` — PASS.
- `uv run python -m unittest discover -s tests -v` — PASS, 4 tests.
- Main Alembic online migration against temporary PostgreSQL 17 dry-run container — PASS.
- PR #54 merged into `dev` as merge commit `eafce94c3c0930c5dbd420bb95cf455af319215f`; post-merge dev workflow run `25567914804` passed `Build and Push Dev Image` and `Deploy to Dev Server`.
- Durable handoff evidence is published from `dev` at `omx_wiki/split-chatbot-postgresql-migration-handoff.md`; verify the current `dev` hash with `git ls-remote origin refs/heads/dev` instead of treating this audit text as the moving branch pointer.
- `scripts/migrate_sqlite_to_postgres.sh main maplewind.db ...` — PASS, row counts matched.
- `scripts/migrate_sqlite_to_postgres.sh chatbot chatbot.db ...` — PASS, row counts matched.

### Chatbot repo

- `uv run ruff check .` — PASS.
- `uv run python -m unittest discover -s tests -v` — PASS, 6 tests.
- `uv run python scripts/simulate_maesaeng_flow.py` — PASS.
- Chatbot Alembic online migration against temporary PostgreSQL 17 dry-run container — PASS.
- After splitting blocked workflow files out of the runtime commit, reran on remote-main runtime commit `b3d80a9`: `uv run ruff check .`, `uv run python -m unittest discover -s tests -v`, and `uv run python scripts/simulate_maesaeng_flow.py` — PASS.
- PostgreSQL-backed simulation on remote-main commit `b3d80a9`: temporary `postgres:17-alpine` container `dpbr-chatbot-sim-pg` on localhost port `55414`; `CHATBOT_DATABASE_URL=postgresql+asyncpg://maplewind:maplewind@localhost:55414/chatbot uv run python scripts/simulate_maesaeng_flow.py` — PASS; container removed after the run.
- Workflow patch recoverability check: pulled `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch` from `origin/dev` and ran `git apply --check` against a temporary worktree of chatbot `origin/main` `5e6c20df8b0c047f716ad02be249a99ce367838e` — PASS. Patch SHA-256: `43baf797f0057ef4b8631370f400929482a9615c60e87be75d8502b42fc8e12e`; adds `.github/workflows/ci.yml` (88 lines) and `.github/workflows/deploy.yml` (115 lines).

## Blocking gaps before goal completion

1. `GC-MapleWind/maplewind-chatbot` remote main now has history-adopting merge commit `5e6c20d`, but CI/CD workflow files remain as patch artifact `chatbot-workflows-pending.patch`; the patch applies cleanly to current chatbot `origin/main`, but pushing/applying it to the remote failed because the OAuth credential lacks GitHub `workflow` scope for `.github/workflows/ci.yml`; credential headers confirm `X-Oauth-Scopes: gist, read:org, repo` with no `workflow`; remote API check for `.github/workflows` still returns HTTP 404. Handoff issue: https://github.com/GC-MapleWind/maplewind-chatbot/issues/1
2. Production cutover, webhook update, SLA tests, and 24h/7d monitoring are manual/production operations and have not run in this local session. Handoff issue: https://github.com/GC-MapleWind/MSGS_13_B/issues/55
3. T042 removal of `migrate_user_student_id_to_username` is intentionally not a free local cleanup until the cutover/post-run verification prerequisite in `tasks.md` is satisfied.
4. Durable handoff evidence is published at https://github.com/GC-MapleWind/MSGS_13_B/blob/dev/omx_wiki/split-chatbot-postgresql-migration-handoff.md and cross-linked from both blocker issues.

## Current conclusion

The implementation is merged to `dev`, the chatbot remote runtime/history adoption is pushed, and the migration dry-run is verified. The overall objective is not complete until the chatbot workflow-scope push and production/staging operational gates are resolved.
