# Completion Audit — split-chatbot-postgres

Date: 2026-05-09

## Objective restated

Use the SDD artifacts in `specs/001-split-chatbot-postgres/`, `codex-prompts.md`, and `.cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md` to split the Kakao chatbot into `GC-MapleWind/maplewind-chatbot` and migrate both the main backend and chatbot from SQLite to one PostgreSQL 17 instance with two databases (`maplewind`, `chatbot`) while preserving data.

## Prompt-to-artifact checklist

`tasks.md` now includes an execution status overlay. Its original checkboxes remain as the
historical plan text; use the overlay and this audit as the current task ledger.

| Requirement / task | Evidence inspected | Status |
| --- | --- | --- |
| T001 production SQLite backups | Production backup/cutover authority is unavailable in this local session; tracked by issue #55 | GAP/ops |
| T002 chatbot repo creation | `GC-MapleWind/maplewind-chatbot` remote exists; current `main` is `dff9dfd2b23be4c5e562e0ca65219df530081b57` | PASS |
| T003 pgloader local verification | `scripts/migrate_sqlite_to_postgres.sh` dry-runs used `dimitri/pgloader:latest`; row-count evidence in `cutover-dryrun.md` | PASS |
| T004 PostgreSQL 17 image selection | `docker-compose.yml`, `docker-compose.dev.yml`, and dry-run containers use PostgreSQL 17 / `postgres:17-alpine` | PASS |
| T005 dependencies: main repo has asyncpg, psycopg, alembic and no Google/chatbot/SQLite driver deps | `pyproject.toml`; `uv.lock`; `grep` for `gspread`, `google-api-python-client`, `googleapiclient`, `aiosqlite` in main `src`/`pyproject.toml` | PASS; `aiosqlite` removed from the main dependency graph and runtime-seeding tests now use PostgreSQL 17 |
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
| T021 git history-preserving extraction | Local filtered repo `../chatbot-history-extract` has 42 commits; chatbot remote `main` is `dff9dfd2b23be4c5e562e0ca65219df530081b57`, a documentation descendant of history-adopting merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e`; the merge has parents `b3d80a9` and filtered-history commit `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`, and `git diff 5e6c20d^1 5e6c20d` was empty, preserving the runtime tree | PASS |
| T022-T028 chatbot repo structure/env/Dockerfile/dev compose | `../maplewind-chatbot` file tree; runtime/history adoption is on remote `main`, now at `dff9dfd2b23be4c5e562e0ca65219df530081b57`; `src/main.py` lifespan now runs Alembic `upgrade head` by default and keeps `AUTO_CREATE_TABLES=true` as a local fallback | PASS |
| T029/T030 chatbot CI/CD workflows | local branch `workflows-pending-scope` commit `6ab860c` provided the original `.github/workflows/ci.yml` and `deploy.yml`; direct push rejected by GitHub token missing `workflow` scope; updated patch preserved in `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`; patch applies cleanly to current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57`; local workflow simulation passed `uv sync --dev --frozen`, ruff, unittest, Alembic offline SQL, Alembic online PostgreSQL 17, Docker build, and T030 tag-shape check for `:latest` plus `:<full sha>` | GAP only for remote workflow availability/execution |
| T031 push new repo + archive branch | chatbot remote `main` now points to docs commit `dff9dfd2b23be4c5e562e0ca65219df530081b57` on top of history-adopting merge commit `5e6c20df8b0c047f716ad02be249a99ce367838e`; chatbot `archive/chinbabang-submission` is `b357aeaa6bc201fa693c871b31c6ad823b66e4c7`; main `GC-MapleWind/MSGS_13_B` `archive/chinbabang-submission` is `387cb221da0e18c9bcefe595d3fb119f18f0ea05`; filtered-history evidence branches remain at `d725f8fa1fafe2ef78adcb4e89b3b8fa930af71f`; workflow-file availability is tracked separately under T029/T030 | PASS |
| T032/T033 main repo cleanup | main `src/` has no chatbot/google refs; tracked chatbot files absent; `src/admin.py` registers only User/Character/Settlement/Comment/Team views; main tests and dev CI pass | PASS |
| T034 production integrated compose design | `docker-compose.yml` pulls `ghcr.io/gc-maplewind/msgs_13_b-backend:latest` and `ghcr.io/gc-maplewind/maplewind-chatbot:latest`, shares PostgreSQL, runs Alembic before service startup, and sets isolated backend/chatbot env blocks; compose config with placeholder env shows backend has only `DATABASE_URL` and no `CHATBOT_*`/`GOOGLE_*` variables, while chatbot has only `CHATBOT_DATABASE_URL` and no `DATABASE_URL` | PASS |
| T035-T037 reverse proxy and SLA isolation validation | requires deployed/staging environment, Kakao webhook/reverse-proxy routing, load test, and crash-isolation scenario | GAP/ops |
| T038-T039 production cutover and monitoring | requires production backup, deployment, Kakao webhook update, SLA evidence, and 24h/7d monitoring | GAP/ops |
| T040-T041 documentation | Main README references `GC-MapleWind/maplewind-chatbot` and integrated compose; chatbot README on `main` `dff9dfd2b23be4c5e562e0ca65219df530081b57` documents env vars, Kakao webhook endpoint, integrated compose deploy ownership, 7-day compatibility routing, operations notes, and simulation script usage | PASS |
| T042-T043 post-cutover cleanup and backup retention | requires post-run T042 removal decision for `migrate_user_student_id_to_username` and SQLite backup retention/cold-storage action after cutover | GAP/ops |

## Functional requirement / success-criteria coverage

This table maps `spec.md` FR/SC items directly to evidence. It intentionally does not treat local dry-runs as production cutover proof.

| Spec item | Evidence inspected | Status |
| --- | --- | --- |
| FR-001 separate repos/images | Main PR #54 merged; chatbot remote `GC-MapleWind/maplewind-chatbot` `main` at `dff9dfd2b23be4c5e562e0ca65219df530081b57`; `docker-compose.yml` pulls separate backend/chatbot GHCR images | PASS |
| FR-002 PostgreSQL 17 instance with `maplewind`/`chatbot` DBs | `docker-compose.yml`, `docker-compose.dev.yml`, `scripts/postgres-init.sql`, and dry-run PostgreSQL 17 containers | PASS for design/local dry-run; production bring-up remains T038 |
| FR-003 no-loss production SQLite migration | `cutover-dryrun.md` row-count/sample comparisons against non-production SQLite copies | GAP/ops until production backup/cutover row counts are captured |
| FR-004 main backend only uses `maplewind` DB | Main `src/database.py` requires `DATABASE_URL`; chatbot DB code/files removed from main `src`; integrated compose no longer injects broad `.env` into backend and compose config shows backend has `DATABASE_URL` only, with no `CHATBOT_*`/`GOOGLE_*` variables | PASS |
| FR-005 chatbot only uses `chatbot` DB | Chatbot repo `src/database.py` requires `CHATBOT_DATABASE_URL`; integrated compose no longer injects broad `.env` into chatbot and compose config shows chatbot has `CHATBOT_DATABASE_URL` without `DATABASE_URL` | PASS |
| FR-006 independent Alembic in both repos | Main `src/alembic`; chatbot repo `src/alembic`; both online migrations passed against temporary PostgreSQL 17 | PASS |
| FR-007 main has no `gspread`, `google-api-python-client`, `aiosqlite` deps | `pyproject.toml`, `uv.lock`, and main `src` grep; `aiosqlite` removed from dev dependencies in this audit pass | PASS |
| FR-008 chatbot declares own runtime deps | Chatbot `pyproject.toml` declares FastAPI, SQLAlchemy, asyncpg, Alembic, httpx, gspread, google API client, sqladmin | PASS |
| FR-009 Kakao webhook/reverse-proxy cutover + 7-day compatibility | `cutover-runbook.md` documents route and compatibility; chatbot README now also documents the integrated compose deploy handoff and 7-day compatibility routing; actual Kakao/reverse-proxy change requires ops authority | GAP/ops |
| FR-010 each container runs `alembic upgrade head` before runtime | Main compose backend command is `uv run alembic upgrade head && uv run uvicorn ...`; chatbot Dockerfile CMD is `uv run alembic upgrade head && uv run uvicorn ...`; online dry-runs passed | PASS locally; production deployment evidence remains T038 |
| FR-011 chatbot callback SLA pattern retained | Chatbot 메생결산 simulation passed; background/callback behavior retained in chatbot runtime | PASS locally; production p95/p99 remains SC-003 |
| FR-012 rollbackable cutover | `cutover-runbook.md` includes rollback commands and backup prerequisites | PASS for runbook; actual rollback readiness depends on T001/T038 |
| FR-013 git filter-repo history preservation | Filtered repo has 42 commits; chatbot history-adopting merge `5e6c20d` preserves runtime tree | PASS |
| FR-014 archive branch preserved in both repos | `git ls-remote` confirms main `GC-MapleWind/MSGS_13_B` `archive/chinbabang-submission` at `387cb221da0e18c9bcefe595d3fb119f18f0ea05` and chatbot `GC-MapleWind/maplewind-chatbot` `archive/chinbabang-submission` at `b357aeaa6bc201fa693c871b31c6ad823b66e4c7` | PASS |
| FR-015 sqladmin chatbot views removed from main and present in chatbot | Main `src/admin.py` has no `EventInfoAdmin`/`InfoListAdmin`/`TemporaryImageAdmin`; chatbot `src/admin.py` imports `EventInfo`, `InfoList`, `TemporaryImage` and registers `EventInfoAdmin`, `InfoListAdmin`, `TemporaryImageAdmin` | PASS |
| FR-016 main compose no longer mounts Google credentials; chatbot-only secret mount | `docker-compose.yml` mounts `../google-credentials.json` only on the chatbot service; backend has no Google credential mount and compose config shows no `GOOGLE_*` variables in backend | PASS |
| SC-001 row counts match SQLite backup | Local dry-run row counts match in `cutover-dryrun.md` | GAP/ops for production backup-time counts |
| SC-002 cutover downtime <= 30 minutes | Requires production cutover timing | GAP/ops |
| SC-003 24h chatbot p95 <= 3s / p99 <= 4s | Requires production/staging monitoring after cutover | GAP/ops |
| SC-004 7d main 5xx <= 0.1% | Requires production monitoring after cutover | GAP/ops |
| SC-005 chatbot CI lint/test and deploy pushes GHCR independently | Workflow patch exists, applies cleanly, and local workflow simulation passes lint/test/Alembic/Docker build; remote workflow files and GHCR push remain blocked by missing `workflow` token scope | GAP/external credential |
| SC-006 main dependency graph removes `gspread`, `google-api-python-client`, `aiosqlite` | `pyproject.toml`/`uv.lock` no longer include those packages after this audit fix | PASS |
| SC-007 chatbot redeploy without backend restart and <= 60s | Integrated compose supports independent service replacement; actual redeploy timing requires staging/production exercise | GAP/ops |

## Verification commands run

### Main repo

- `bash -n scripts/migrate_sqlite_to_postgres.sh` — PASS.
- `uv run ruff check .` — PASS.
- `uv run python -m unittest discover -s tests -v` — PASS, 4 tests; runtime-seeding tests now run against temporary `postgres:17-alpine` and no longer require `aiosqlite`.
- Main Alembic online migration against temporary PostgreSQL 17 dry-run container — PASS.
- PR #54 merged into `dev` as merge commit `eafce94c3c0930c5dbd420bb95cf455af319215f`; post-merge dev workflow run `25567914804` passed `Build and Push Dev Image` and `Deploy to Dev Server`.
- Dependency graph check: `grep -RIn "aiosqlite\|gspread\|google-api-python-client\|googleapiclient" pyproject.toml src tests` and `grep -n "aiosqlite" uv.lock` returned no matches after the dependency cleanup.
- Compose isolation check: `docker compose --env-file <placeholder> -f docker-compose.yml config --format json` showed backend environment contains `DATABASE_URL` only for database access and no `CHATBOT_*`/`GOOGLE_*`; chatbot contains `CHATBOT_DATABASE_URL` and no `DATABASE_URL`.
- Admin isolation check: main `src/admin.py` contains no chatbot ModelViews and `grep -RIn "EventInfo\|InfoList\|TemporaryImage\|chatbot\|gspread\|googleapiclient" src pyproject.toml` returned no main backend refs; chatbot `src/admin.py` registers the three chatbot ModelViews.
- Dev GitHub Actions run `25571572967` for `Backend CI/CD (Docker)` completed with conclusion `success` after the compose environment isolation fix.
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
- Workflow patch recoverability check: pulled `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch` from `origin/dev` and ran `git apply --check` against a temporary worktree of current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57` — PASS. Patch SHA-256: `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`; adds `.github/workflows/ci.yml` (88 lines) and `.github/workflows/deploy.yml` with GHCR `:latest`, `:<full sha>`, `:main`, and `:main-*` tags.
- Chatbot README/T024 audit fixes: chatbot commit `dff9dfd2b23be4c5e562e0ca65219df530081b57` documents integrated main-repo compose deployment ownership and the FR-009 seven-day reverse-proxy compatibility route, and `src/main.py` lifespan runs Alembic `upgrade head` before serving requests while preserving the `AUTO_CREATE_TABLES=true` local fallback; `uv run ruff check .`, `uv run python -m unittest discover -s tests -v`, and a FastAPI `/health` startup smoke against temporary `postgres:17-alpine` passed after these changes.
- Workflow patch local CI simulation was re-run against current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57` after the README/T024 lifespan updates — PASS: applied `chatbot-workflows-pending.patch` in a temporary worktree, `uv sync --dev --frozen`, `uv run ruff check .`, CI-env SQLite unit tests (`uv run python -m unittest discover -s tests -v`, 6 tests), Alembic offline SQL with `CHATBOT_DATABASE_URL=postgresql+asyncpg://ci:ci@localhost:5432/chatbot`, Alembic online migration against temporary `postgres:17-alpine`, and `docker build -t chatbot-ci-local:workflow-patch-t030 .`; it also verified the deploy workflow contains `type=sha,format=long,prefix=` for the required `:<full sha>` GHCR tag; evidence was also posted to https://github.com/GC-MapleWind/maplewind-chatbot/issues/1#issuecomment-4408932960.


### Objective done-criteria grep audit — 2026-05-09

- Main cleanup search passed on `origin/dev`: no `chatbot` refs remain under `src/`, no `gspread` / `googleapiclient` / `google-api-python-client` / `aiosqlite` refs remain in `src/` or `pyproject.toml`, and all extracted chatbot files plus `tests/test_event_date_gating.py` are absent from the main repo.
- Env examples passed: main `.env.example` contains `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, and `CHATBOT_DATABASE_URL`; chatbot `.env.example` contains `CHATBOT_DATABASE_URL`, `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_SHEET_ID`, and the required `KAKAO_*` variables.
- Chatbot startup/admin checks passed on `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57`: lifespan runs Alembic `upgrade head`, Dockerfile also runs Alembic before uvicorn, and `EventInfoAdmin`, `InfoListAdmin`, `TemporaryImageAdmin` are registered.
- Workflow artifact checks passed: `chatbot-workflows-pending.patch` contains `type=raw,value=latest`, `type=sha,format=long,prefix=`, and `type=sha,prefix=main-`, and `git apply --check` passes against chatbot `origin/main`.

## Blocking gaps before goal completion

1. `GC-MapleWind/maplewind-chatbot` remote main is `dff9dfd`, a documentation descendant of history-adopting merge commit `5e6c20d`, but CI/CD workflow files remain as patch artifact `chatbot-workflows-pending.patch`; the patch applies cleanly to current chatbot `origin/main` `dff9dfd2b23be4c5e562e0ca65219df530081b57`, but pushing/applying it to the remote failed because the OAuth credential lacks GitHub `workflow` scope for `.github/workflows/ci.yml`; credential headers confirm `X-Oauth-Scopes: gist, read:org, repo` with no `workflow`; remote API check for `.github/workflows` still returns HTTP 404. Handoff issue: https://github.com/GC-MapleWind/maplewind-chatbot/issues/1
2. T001 and T035-T039/T042-T043 remain production/staging operations: production SQLite backups, reverse proxy/Kakao routing, SLA/load and crash-isolation validation, cutover and monitoring, post-run T042 cleanup, and backup retention/cold-storage have not run in this local session. Handoff issue: https://github.com/GC-MapleWind/MSGS_13_B/issues/55
3. T042 removal of `migrate_user_student_id_to_username` is intentionally not a free local cleanup until the cutover/post-run verification prerequisite in `tasks.md` is satisfied.
4. Durable handoff evidence is published at https://github.com/GC-MapleWind/MSGS_13_B/blob/dev/omx_wiki/split-chatbot-postgresql-migration-handoff.md and cross-linked from both blocker issues.

## Current conclusion

The implementation is merged to `dev`, the chatbot remote runtime/history adoption is pushed, the migration dry-run is verified, T034/T040/T041 are documented complete, and T031 is no longer blocked. The overall objective is not complete until the chatbot workflow-scope push and production/staging operational gates are resolved.
