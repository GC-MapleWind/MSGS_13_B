# Completion Audit — split-chatbot-postgres

Date: 2026-05-09

## Objective restated

Use the SDD artifacts in `specs/001-split-chatbot-postgres/`, `codex-prompts.md`, and `.cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md` to split the Kakao chatbot into `GC-MapleWind/maplewind-chatbot` and migrate both the main backend and chatbot from SQLite to one PostgreSQL 17 instance with two databases (`maplewind`, `chatbot`) while preserving data.

## Prompt-to-artifact checklist

| Requirement / task | Evidence inspected | Status |
| --- | --- | --- |
| T005 dependencies: main repo has asyncpg, psycopg, alembic and no runtime Google chatbot deps | `pyproject.toml`; `grep` for `gspread`, `google-api-python-client`, `googleapiclient` in main `src`/`pyproject.toml` | PASS for runtime; `aiosqlite` remains in dev dependencies for SQLite tests |
| T006/T007 PostgreSQL service and two DB init SQL | `docker-compose.yml`, `docker-compose.dev.yml`, `scripts/postgres-init.sql`; dry-run DB creation via `cat scripts/postgres-init.sql | docker exec ... psql` | PASS |
| T008 `.env.example` Postgres variables | `.env.example` | PASS |
| T009 main DB fail-fast and SQLite PRAGMA guard | `src/database.py` | PASS |
| T010/T011 chatbot DB/model Postgres compatibility | moved to `../maplewind-chatbot/src/database.py`, `src/models/chatbot.py`, `src/alembic/versions/0001_initial.py` | PASS locally |
| T012 legacy SQLite migration guard | `src/main.py` checks dialect before PRAGMA | PASS |
| T013 main Alembic metadata only | `src/alembic/env.py`, `src/alembic/versions/0001_initial.py`; online dry-run against PostgreSQL | PASS |
| T014/T015 pgloader wrapper and local row-count verification | `scripts/migrate_sqlite_to_postgres.sh`; dry-run with `dimitri/pgloader:latest`; row-count output in `cutover-dryrun.md` | PASS |
| T016/T017 chatbot model DDL and event date tests | chatbot Alembic online dry-run; `uv run python -m unittest discover -s tests -v` in chatbot repo | PASS |
| T018 메생결산 simulation | `../maplewind-chatbot/scripts/simulate_maesaeng_flow.py`; SQLite fallback and PostgreSQL-backed run against temporary `postgres:17-alpine` container both called `register_final_data` once, sent callback once, and cleaned the temporary session | PASS |
| T019 dry-run report with row counts and sample comparisons | `specs/001-split-chatbot-postgres/cutover-dryrun.md` | PASS for local SQLite copies |
| T020 cutover runbook with rollback | `specs/001-split-chatbot-postgres/cutover-runbook.md` | PASS |
| T021 git history-preserving extraction | Local filtered repo `../chatbot-history-extract` has 42 commits; remote evidence branches `history-preserved-extract` and `archive/chinbabang-submission-filtered` point to filtered commit `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f` | PASS for evidence branch; remote `main` is still not history-preserved |
| T022-T028 chatbot repo structure/env/Dockerfile/dev compose | `../maplewind-chatbot` file tree; runtime commit `b3d80a935f82427d13432ad56107dd51189931e0` pushed to remote `main` | PASS |
| T029/T030 chatbot CI/CD workflows | local branch `workflows-pending-scope` commit `6ab860c` contains `.github/workflows/ci.yml` and `deploy.yml`; direct push rejected by GitHub token missing `workflow` scope; patch preserved in `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch` | GAP for remote workflow availability |
| T031 push new repo + archive branch | chatbot remote `main` now points to runtime commit `b3d80a935f82427d13432ad56107dd51189931e0`; `archive/chinbabang-submission` pushed at `b357aea`; filtered-history evidence branches pushed at `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`; workflow branch push rejected by remote workflow-scope policy | PARTIAL |
| T032/T033 main repo cleanup | main `src/` has no chatbot/google refs; tracked chatbot files absent; main tests pass | PASS |
| T034-T037 SLA isolation | requires deployed/staging environment and load test | GAP |
| T038-T043 production cutover/polish | requires production backup, deployment, Kakao webhook update, monitoring, and backup retention | GAP/manual ops |

## Verification commands run

### Main repo

- `bash -n scripts/migrate_sqlite_to_postgres.sh` — PASS.
- `uv run ruff check .` — PASS.
- `uv run python -m unittest discover -s tests -v` — PASS, 4 tests.
- Main Alembic online migration against temporary PostgreSQL 17 dry-run container — PASS.
- `scripts/migrate_sqlite_to_postgres.sh main maplewind.db ...` — PASS, row counts matched.
- `scripts/migrate_sqlite_to_postgres.sh chatbot chatbot.db ...` — PASS, row counts matched.

### Chatbot repo

- `uv run ruff check .` — PASS.
- `uv run python -m unittest discover -s tests -v` — PASS, 6 tests.
- `uv run python scripts/simulate_maesaeng_flow.py` — PASS.
- Chatbot Alembic online migration against temporary PostgreSQL 17 dry-run container — PASS.
- After splitting blocked workflow files out of the runtime commit, reran on remote-main commit `b3d80a9`: `uv run ruff check .`, `uv run python -m unittest discover -s tests -v`, and `uv run python scripts/simulate_maesaeng_flow.py` — PASS.
- PostgreSQL-backed simulation on remote-main commit `b3d80a9`: temporary `postgres:17-alpine` container `dpbr-chatbot-sim-pg` on localhost port `55414`; `CHATBOT_DATABASE_URL=postgresql+asyncpg://maplewind:maplewind@localhost:55414/chatbot uv run python scripts/simulate_maesaeng_flow.py` — PASS; container removed after the run.

## Blocking gaps before goal completion

1. `GC-MapleWind/maplewind-chatbot` remote main now has runtime commit `b3d80a9`, but CI/CD workflow files remain on local branch `workflows-pending-scope` commit `6ab860c` and as patch artifact `chatbot-workflows-pending.patch`; pushing that branch failed because the OAuth credential lacks GitHub `workflow` scope for `.github/workflows/ci.yml`.
2. History-preserving extraction is evidenced on non-destructive remote branches (`history-preserved-extract`, `archive/chinbabang-submission-filtered`) and local repo `../chatbot-history-extract`, but the chatbot remote `main` branch itself is still not the filtered-history branch.
3. Main repo PR [#54](https://github.com/GC-MapleWind/MSGS_13_B/pull/54) is open at `735ddaa`; build/test jobs passed, but GitHub still reports the PR as `UNSTABLE` while the `Deploy to Dev Server` job is pending/in progress.
4. Production cutover, webhook update, SLA tests, and 24h/7d monitoring are manual/production operations and have not run in this local session.

## Current conclusion

The local implementation, chatbot remote runtime push, and migration dry-run are substantially complete and verified. History preservation is now evidenced on separate branches, but the overall objective is not complete until the remote workflow-scope push/branch-adoption gap and production/staging operational gates are resolved.
