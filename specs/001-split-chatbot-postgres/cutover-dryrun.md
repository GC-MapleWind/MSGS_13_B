# Cutover Dry-run Report — split-chatbot-postgres

Date: 2026-05-09
Environment: local workspace `/mnt/d/01_Works/msgs13/dpbr_13_B` with Docker Desktop temporary PostgreSQL container `dpbr-postgres-dryrun`.

## Local SQLite source inventory

| DB | Table | SQLite rows | PostgreSQL rows | Status |
| --- | --- | ---: | ---: | --- |
| maplewind.db | users | 105 | 105 | OK |
| maplewind.db | characters | 105 | 105 | OK |
| maplewind.db | settlements | 84 | 84 | OK |
| maplewind.db | comments | 0 | 0 | OK |
| maplewind.db | team_members | 15 | 15 | OK |
| maplewind.db | team_messages | 15 | 15 | OK |
| chatbot.db | eventinfo | 0 | 0 | OK |
| chatbot.db | infolist | 3 | 3 | OK |
| chatbot.db | temporary_images | 0 | 0 | OK |

## Commands executed

```bash
# Temporary local PostgreSQL 17 container, no persistent volume.
docker run -d --name dpbr-postgres-dryrun \
  -e POSTGRES_USER=maplewind \
  -e POSTGRES_PASSWORD=maplewind \
  -e POSTGRES_DB=postgres \
  -p 55413:5432 \
  postgres:17-alpine

# Create the two target databases with the repo init SQL.
cat scripts/postgres-init.sql \
  | docker exec -i dpbr-postgres-dryrun psql -U maplewind -d postgres

# Apply both Alembic schemas.
DATABASE_URL=postgresql+asyncpg://maplewind:maplewind@localhost:55413/maplewind \
  ADMIN_SESSION_SECRET=dryrun \
  uv run alembic upgrade head

(cd ../maplewind-chatbot && \
  CHATBOT_DATABASE_URL=postgresql+asyncpg://maplewind:maplewind@localhost:55413/chatbot \
  uv run alembic upgrade head)

# pgloader migration + row-count verification through the wrapper.
PATH="/tmp/docker-bin:$PATH" scripts/migrate_sqlite_to_postgres.sh \
  main maplewind.db postgresql://maplewind:maplewind@host.docker.internal:55413/maplewind
PATH="/tmp/docker-bin:$PATH" scripts/migrate_sqlite_to_postgres.sh \
  chatbot chatbot.db postgresql://maplewind:maplewind@host.docker.internal:55413/chatbot
```

## Row-count result

`maplewind.db` migrated 324 rows across the main tables checked by `scripts.verify_postgres_counts`.
`chatbot.db` migrated 3 rows across the chatbot tables checked by `scripts.verify_postgres_counts`.
Both wrapper runs ended with `==> Done. Row counts match.`

## Sample row comparisons

Column-by-column comparison sampled up to five rows ordered by `id` from the critical tables.

| DB | Table | Sample IDs | Mismatches |
| --- | --- | --- | --- |
| maplewind.db | users | 1, 2, 3, 4, 5 | 0 |
| maplewind.db | characters | 1, 2, 3, 4, 5 | 0 |
| maplewind.db | settlements | 1, 2, 3, 4, 5 | 0 |
| chatbot.db | eventinfo | none: table empty | 0 |
| chatbot.db | infolist | 1, 2, 3 | 0 |
| chatbot.db | temporary_images | none: table empty | 0 |

## Additional verification performed

- Main repo lint: `uv run ruff check .` — PASS.
- Main repo unit tests: `uv run python -m unittest discover -s tests -v` — PASS (4 tests).
- Main Alembic PostgreSQL online migration against dry-run container — PASS.
- Chatbot repo lint: `uv run ruff check .` — PASS.
- Chatbot repo unit tests: `uv run python -m unittest discover -s tests -v` — PASS (6 tests).
- Chatbot Alembic PostgreSQL online migration against dry-run container — PASS.
- Chatbot 메생결산 simulation with mocked Google/Kakao I/O:
  - SQLite fallback: `uv run python scripts/simulate_maesaeng_flow.py` — PASS; `register_final_data` called once, callback called once, temporary session cleaned.
  - PostgreSQL-backed run: `CHATBOT_DATABASE_URL=postgresql+asyncpg://maplewind:maplewind@localhost:55414/chatbot uv run python scripts/simulate_maesaeng_flow.py` against temporary `postgres:17-alpine` container `dpbr-chatbot-sim-pg` — PASS; `register_final_data` called once, callback called once, temporary session cleaned.

## Data type notes

- Chatbot `TemporaryImage.data` uses SQLAlchemy `JSON().with_variant(JSONB, "postgresql")`; Alembic creates PostgreSQL JSONB and the SQLite fallback uses a plain JSON default.
- The current local `chatbot.db` includes legacy empty `activity_submissions` and `submitter_profiles` tables. They are migrated by pgloader but are not part of the current chatbot ORM/Alembic target and are excluded from the service row-count gate.
- Empty critical tables (`eventinfo`, `temporary_images`) have no sample rows to compare; row-count equality is the evidence for those tables in this dry-run.

## Follow-up before production

Repeat this dry-run with immutable production backup copies during cutover rehearsal. Do not use live SQLite files as pgloader input.
