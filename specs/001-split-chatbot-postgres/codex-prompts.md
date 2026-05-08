# Codex Work Orders — split-chatbot-postgres

> Codex (또는 다른 헤드리스 coding agent) 에게 위임할 작업 프롬프트 모음. 각 섹션은
> 독립적으로 복붙 가능한 하나의 프롬프트다. 모든 프롬프트는 본 repo 의 SDD 산출물
> ([constitution](../../.specify/memory/constitution.md), [spec](./spec.md),
> [plan](./plan.md), [tasks](./tasks.md)) 을 기반으로 한다.
>
> **사용법**:
>
> 1. Codex 세션 시작 시 [§1 Bootstrap](#1-bootstrap-prompt-세션-시작) 을 첫 메시지로 보낸다.
> 2. 작업 단위별로 §2~§5 중 하나를 추가 메시지로 보낸다.
> 3. 운영 영향이 있는 작업 (Phase 0 백업, Phase 6 컷오버) 은 사람이 직접 실행한다.

---

## 1. Bootstrap Prompt (세션 시작)

세션의 첫 메시지로 사용. Codex 가 컨텍스트를 잡고 헌법 / spec / plan / tasks 를 읽도록 한다.

````markdown
You are a senior Python backend engineer working on **MapleWind (단풍바람)**, a
FastAPI + SQLAlchemy 2.0 async backend at `D:/01_Works/msgs13/dpbr_13_B`.

## Mission

We are executing a Spec-Driven feature: **split-chatbot-postgres** —
splitting the chatbot service into its own repo while migrating both
services from SQLite to PostgreSQL 17. You will receive incremental work
orders from me; each maps to a phase in `tasks.md`.

## Mandatory reading (do this BEFORE any code change)

Read these files in order, fully, no skipping:

1. `.specify/memory/constitution.md` — project governing principles. **All
   five core principles are non-negotiable.**
2. `.cursorrules` — supplementary naming and code patterns.
3. `specs/001-split-chatbot-postgres/spec.md` — user stories, FR, success
   criteria.
4. `specs/001-split-chatbot-postgres/plan.md` — technical context,
   constitution check, project structure.
5. `specs/001-split-chatbot-postgres/tasks.md` — task breakdown by phase.

After reading, summarize back to me in 5 bullets:

- the 3-layer rule
- async-first rule
- type-style rule (`str | None`, `Mapped[]`)
- the user story you understand to be P1 / MVP
- the phase you expect to work on next

Do not start coding yet. Wait for my next message.

## Hard rules during this session

- **Architecture**: Controller → Service → Repository, one direction. No
  controller imports from `repositories/` or `models/`. No service writes
  raw SQL or `select()`. Repositories never raise `HTTPException`.
- **Async-only**: every `def` that touches I/O is `async def`. Use
  `AsyncSession`, `httpx.AsyncClient`. Wrap sync SDKs with
  `asyncio.to_thread`.
- **Types**: `str | None`, `list[T]`, `dict[K, V]`, `Mapped[T]`,
  `mapped_column()`. Never `Optional`, `List`, `Dict` from `typing`.
- **Comments**: explain non-obvious intent only. Do not narrate code.
- **Dependencies**: `uv add <pkg>` / `uv add --dev <pkg>` / `uv remove
  <pkg>`. Never edit `uv.lock` by hand.
- **Tests**: run `uv run python -m unittest discover -s tests -v` before
  declaring a task complete. Tests must pass.
- **Secrets**: never read or print `.env`, `google-credentials.json`, or
  any `*.key`/`*.pem`. Update `.env.example` only.
- **Git**: do not commit, do not push, do not create branches unless I
  explicitly ask. Show me a diff summary at the end of each task and let
  me decide.
- **Operational data**: never run `pgloader` against production data.
  Never delete the existing SQLite files. All Postgres work runs against a
  local docker container only.

## Output expectations

For each work order I send, your final reply must include:

1. Files changed (path + one-line summary).
2. Tests run + result.
3. Constitution check: confirm you did not violate any of the five
   principles. If you had to, point to plan.md → "Complexity Tracking" and
   propose an entry.
4. Suggested commit message (English, imperative, ≤72 chars subject +
   body if needed).
5. Anything I should know before merging (risks, follow-ups).

Reply now with the 5-bullet summary requested above. Then stop.
````

---

## 2. Work Order — Phase 2: Foundational (T005–T015)

가장 안전한 첫 코드 변경. 운영 영향 없음. 로컬 docker 안에서만 동작.

````markdown
## Work order: Phase 2 — Foundational PostgreSQL infrastructure

Reference: `specs/001-split-chatbot-postgres/tasks.md` tasks **T005 to
T015**. Implement in this exact order. Stop after T015 and report back.

### Scope

Add PostgreSQL 17 to the main repo, replace aiosqlite with asyncpg,
introduce Alembic, and prepare a pgloader-based migration script. The
chatbot module **stays in this repo for now** — do not delete or move it.

### Specific tasks

1. **T005** — Update `pyproject.toml` via uv:
   - `uv add asyncpg "psycopg[binary]" alembic`
   - `uv remove aiosqlite`
2. **T006** — Add `postgres` service to `docker-compose.yml`:
   - image `postgres:17-alpine`
   - bind-mount `./data/pg` for data, mount `./scripts/postgres-init.sql`
     read-only at `/docker-entrypoint-initdb.d/01-create-databases.sql`
   - healthcheck `pg_isready -U $POSTGRES_USER`
   - inject env vars from `.env`
   - make `backend` depend on `postgres` with `service_healthy`
3. **T007** — Create `scripts/postgres-init.sql` containing:
   ```sql
   CREATE DATABASE maplewind;
   CREATE DATABASE chatbot;
   ```
4. **T008** — Update `.env.example` only (NEVER `.env`):
   - add `POSTGRES_USER`, `POSTGRES_PASSWORD`,
     `DATABASE_URL=postgresql+asyncpg://...`,
     `CHATBOT_DATABASE_URL=postgresql+asyncpg://...`
   - remove SQLite-specific keys
5. **T009** — `src/database.py`:
   - drop the SQLite default URL; raise on missing env var
   - keep dialect-guarded PRAGMA listeners only if dialect == "sqlite"
6. **T010** — `src/database_chatbot.py`:
   - require `CHATBOT_DATABASE_URL` env var
   - guard PRAGMA listener with dialect check
7. **T011** — `src/models/chatbot.py`:
   - apply `from sqlalchemy.dialects.postgresql import JSONB` and
     `JSON().with_variant(JSONB, "postgresql")` on JSON columns
   - update `server_default=text("'{}'::jsonb")` for Postgres
8. **T012** — `src/main.py`:
   - verify `migrate_user_student_id_to_username` is dialect-guarded for
     SQLite. Do NOT remove the function yet (T042 handles that).
9. **T013** — Initialize Alembic for the main repo only:
   - `uv run alembic init src/alembic`
   - configure `src/alembic/env.py` with `target_metadata = Base.metadata`
     (main metadata only — chatbot metadata moves to a separate repo
     later)
   - generate first revision: `uv run alembic revision --autogenerate -m
     "initial schema"`
   - manually inspect the generated DDL and ensure it matches current
     SQLite tables; commit the resulting `versions/0001_*.py` file
10. **T014** — Create `scripts/migrate_sqlite_to_postgres.sh`:
    - bash wrapper that runs `dimitri/pgloader:latest` via Docker
    - parameterized via env vars: `SQLITE_PATH`, `POSTGRES_URL`
    - after pgloader, run a row-count comparison between SQLite and
      Postgres and print a diff table
11. **T015** — Local verification:
    - `docker compose up -d postgres`
    - `uv run alembic upgrade head`
    - take a copy of `data/maplewind.db` (do NOT use prod) and run
      `scripts/migrate_sqlite_to_postgres.sh`
    - confirm row counts match
    - run `uv run python -m unittest discover -s tests -v`

### Out of scope for this work order

- Removing chatbot files (Phase 4 / US2)
- `git filter-repo` (Phase 4 / US2)
- Production cutover (Phase 6)
- Editing `.env` (only `.env.example`)

### Done criteria

- All 11 tasks above implemented.
- `docker compose up -d postgres backend` boots cleanly.
- `alembic upgrade head` is idempotent.
- Existing test suite passes.
- Diff summary + suggested commit message ready for me to review.

Begin. Report back per the §"Output expectations" rule from the bootstrap.
````

---

## 3. Work Order — Phase 3: User Story 1 verification (T016–T020)

Phase 2 가 끝나고 메인 repo 가 Postgres 위에서 도는지 확인하는 단계. 챗봇 모듈을 아직
이 repo 에 둔 채로 검증.

````markdown
## Work order: Phase 3 — User Story 1 (P1 MVP) verification

Reference: `tasks.md` tasks **T016 to T020**. Goal: confirm zero data loss
and that the maesaeng (메생결산) submission flow works end-to-end on
PostgreSQL.

### Specific tasks

1. **T016** — Verify chatbot SQLAlchemy models (`src/models/chatbot.py`)
   produce correct DDL on PostgreSQL via alembic-autogenerate. Pay close
   attention to `func.now()` defaults and `DateTime` columns. If a column
   silently produces wrong DDL on PG, fix the model annotation, not the
   migration.
2. **T017** — Run `uv run python -m unittest tests.test_event_date_gating
   -v` against the new Postgres environment. The `case()` expression in
   `src/repositories/chatbot_repo.py` must work identically. If a test
   fails, **do not** edit the test — investigate the repository or model.
3. **T018** — Update `scripts/simulate_maesaeng_flow.py`:
   - read `DATABASE_URL` and `CHATBOT_DATABASE_URL` from env
   - assert exactly one final submission is handed to the Google Sheets mock
   - assert temporary chatbot DB rows return to their initial count after cleanup
   - keep all existing mocks (Google Sheets, Kakao callback)
4. **T019** — pgloader operational dry-run:
   - take a non-production copy of `maplewind.db` and `chatbot.db`
   - run `scripts/migrate_sqlite_to_postgres.sh` for each
   - sample 5 random rows per critical table (`users`, `characters`,
     `settlements`, `event_info`, `info_list`, `temporary_image`) and
     compare SQLite vs Postgres column-by-column
   - produce a `cutover-dryrun.md` report under
     `specs/001-split-chatbot-postgres/` listing row counts, sample
     comparisons, and any data type quirks (e.g. JSON → JSONB, datetime
     timezone)
5. **T020** — Append a "Cutover Runbook" section to `plan.md` (or create a
   separate `cutover-runbook.md` in the same dir). Include the exact
   shell commands for the 7-step cutover from `plan.md` Phase 3, plus
   rollback commands.

### Hard limits

- Use only **non-production** SQLite copies. Never touch production data.
- Do not modify production `docker-compose.yml` overrides.
- Do not change Kakao webhook URLs.

### Done criteria

- All 5 tasks complete.
- `simulate_maesaeng_flow.py` passes against PG, asserts one Google Sheets
  registration call, and verifies temporary DB row cleanup.
- `cutover-dryrun.md` exists with row count + sample comparisons.
- Existing test suite still passes.

Report back per bootstrap rules.
````

---

## 4. Work Order — Phase 4: Chatbot extraction & new repo (T021–T033)

가장 큰 단위. 두 단계로 쪼개서 진행 권장.

### 4a. Extraction & new repo skeleton (T021–T031)

````markdown
## Work order: Phase 4a — Extract chatbot to new repo

Reference: `tasks.md` tasks **T021 to T031**. Goal: extract chatbot files
to a new repo `GC-MapleWind/maplewind-chatbot` with full git history.
**Do not modify the main repo yet** — that's the next work order.

### Specific tasks

1. **T021** — In a separate clone (NOT the working tree at
   `D:/01_Works/msgs13/dpbr_13_B`), run `git filter-repo` with the
   `--path` arguments listed in `tasks.md` T021. Place the resulting
   repo at `D:/01_Works/msgs13/maplewind-chatbot` (sibling directory).
2. **T022** — In the extracted repo:
   - rename `src/database_chatbot.py` to `src/database.py`
   - update all imports: `from src.database_chatbot` → `from
     src.database`
   - reorganize directories to match `plan.md` → "Source Code (new repo)"
3. **T023** — Create `pyproject.toml` for the new repo with:
   `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2.0.46`, `asyncpg`,
   `alembic`, `httpx`, `google-api-python-client`, `gspread`, `sqladmin`,
   `itsdangerous`, `python-dotenv`, `greenlet`. Use uv.
4. **T024** — Create `src/main.py` for the new repo: FastAPI app,
   lifespan that runs `alembic upgrade head`, register chatbot router and
   sqladmin. Mirror the patterns from the main repo's `src/main.py`.
5. **T025** — Create `src/admin.py` registering `EventInfoAdmin`,
   `InfoListAdmin`, `TemporaryImageAdmin` (extracted from main repo's
   `src/admin.py`).
6. **T026** — Initialize Alembic in the new repo with
   `target_metadata = ChatbotBase.metadata`. First revision must produce
   DDL for `event_info`, `info_list`, `temporary_image` tables that
   matches the current SQLite schema.
7. **T027** — Add `Dockerfile` and `docker-compose.dev.yml` to the new
   repo. Reuse the main repo's Dockerfile pattern. The dev compose file
   should include a postgres service for local development.
8. **T028** — Add `.env.example` with: `CHATBOT_DATABASE_URL`,
   `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_SHEET_ID`, all `KAKAO_*` vars.
9. **T029** — Add `.github/workflows/ci.yml`: ruff lint + unittest (or
   pytest) + Postgres service container for integration tests.
10. **T030** — Add `.github/workflows/deploy.yml`: on `main` push, build
    GHCR image (`ghcr.io/gc-maplewind/maplewind-chatbot:<sha>` and
    `:latest`), then SSH-deploy to production.
11. **T031** — Push the new repo:
    - `git push -u origin main`
    - also push `archive/chinbabang-submission` branch (FR-014)

### Hard limits

- Work on the extracted repo at `D:/01_Works/msgs13/maplewind-chatbot`,
  NOT on the main working tree at `D:/01_Works/msgs13/dpbr_13_B`.
- Do not delete chatbot files from the main repo yet (next work order).
- Do not push the GHCR image yet — only set up the workflow file.

### Done criteria

- New repo at `maplewind-chatbot` boots locally via `docker compose -f
  docker-compose.dev.yml up`.
- `alembic upgrade head` succeeds against a fresh PG.
- CI workflow passes on first push.
- `archive/chinbabang-submission` exists on the new remote.

Report back.
````

### 4b. Main repo cleanup (T032–T033)

````markdown
## Work order: Phase 4b — Main repo cleanup after extraction

Reference: `tasks.md` tasks **T032 to T033**. Run this only AFTER
Phase 4a is pushed to the new remote.

### Specific tasks

1. **T032** — Delete the following from the main repo:
   - `src/services/chatbot_service.py`
   - `src/services/google_sheet_service.py`
   - `src/repositories/chatbot_repo.py`
   - `src/models/chatbot.py`
   - `src/schemas/chatbot_dto.py`
   - `src/controller/v1/chatbot.py`
   - `src/database_chatbot.py`
   - `scripts/simulate_maesaeng_flow.py`

   Then update:
   - `src/main.py`: remove chatbot router import,
     `init_chatbot_db()` call, `app.include_router(chatbot_router, ...)`
   - `src/admin.py`: remove `EventInfoAdmin`, `InfoListAdmin`,
     `TemporaryImageAdmin` + their imports + `add_view` calls. Remove
     `chatbot_async_session` import.
   - `pyproject.toml`: `uv remove gspread google-api-python-client`
   - `docker-compose.yml`: remove the `google-credentials.json` mount
2. **T033** — Delete `tests/test_event_date_gating.py` from the main
   repo (it was moved to the new repo).

### Verification

- `uv run python -m unittest discover -s tests -v` passes.
- `docker compose up -d postgres backend` boots cleanly.
- Search for `chatbot` (case-insensitive) in `src/` returns no results
  except possibly historical comments.
- Search for `gspread`, `googleapiclient`, `aiosqlite` returns no
  results in `src/` or `pyproject.toml`.

### Done criteria

- Diff summary shows: 8 files deleted, 4 files modified
  (`src/main.py`, `src/admin.py`, `pyproject.toml`,
  `docker-compose.yml`), 1 test deleted.
- Test suite passes.
- Suggested commit message ready.

Report back.
````

---

## 5. Sanity Prompts (검증/리뷰용)

### 5a. Constitution check on a diff

````markdown
## Constitution check on current diff

Run `git diff --stat HEAD` and `git diff HEAD` against the working tree.
For each modified/created file, verify compliance with
`.specify/memory/constitution.md` core principles I–V.

Report:

- Per-file compliance status (PASS / FAIL with line refs).
- Any violation that requires a "Complexity Tracking" entry in
  `specs/001-split-chatbot-postgres/plan.md`.
- Suggested fixes for FAIL items.

Do not modify any file in this run.
````

### 5b. Spec ↔ tasks coverage check

````markdown
## Spec ↔ tasks coverage check

Cross-reference `specs/001-split-chatbot-postgres/spec.md` Functional
Requirements (FR-001 through FR-016) against tasks in
`specs/001-split-chatbot-postgres/tasks.md`.

For each FR, list the task IDs that implement or verify it. Flag any FR
with zero task coverage as a gap. Flag any task that doesn't trace back
to a FR or User Story.

Output as a markdown table. Do not modify files.
````

---

## Notes

- Phase 0 (T001–T004) and Phase 6 cutover (T038) involve production
  data and remote infrastructure. **Run those manually**, not via Codex.
- Phase 5 (T034–T037) requires a deployed staging environment for SLA
  testing. Wrap in a Codex prompt only if you have such an environment;
  otherwise treat as manual ops.
- All commit messages should be English imperative mood (project rule).
- Each work order is meant to produce one PR. Don't combine.
