# Cutover Runbook — split-chatbot-postgres

> Scope: production operator checklist for moving MapleWind backend and chatbot from SQLite to PostgreSQL 17. Run during the approved low-traffic cutover window. Do not run against production until SQLite backups are confirmed.

## Preconditions

- Current SQLite files are present on the production host:
  - `data/maplewind.db`
  - `data/chatbot.db`
- New backend and chatbot images are available in GHCR; Gate A (`GC-MapleWind/maplewind-chatbot#1`) is closed with workflow, CI, deploy/build, and GHCR tag evidence.
- `.env` contains `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `CHATBOT_DATABASE_URL`, backend secrets, and chatbot secrets.
- `scripts/postgres-init.sql` is present beside the production compose file.
- Docker can pull `postgres:17-alpine` and `dimitri/pgloader:latest`.

## Preflight evidence gate

Do not start the 7-step cutover until these checks are captured in
`production-cutover-evidence-template.md`:

```bash
set -euo pipefail

git ls-remote https://github.com/GC-MapleWind/MSGS_13_B.git refs/heads/dev
git ls-remote https://github.com/GC-MapleWind/maplewind-chatbot.git refs/heads/main

gh api 'repos/GC-MapleWind/maplewind-chatbot/contents/.github/workflows?ref=main'
gh api 'repos/GC-MapleWind/maplewind-chatbot/actions/runs?branch=main&per_page=5'
gh api '/orgs/GC-MapleWind/packages/container/maplewind-chatbot'

# Record the exact images/tags that production will deploy.
docker manifest inspect ghcr.io/gc-maplewind/msgs_13_b-backend:latest >/tmp/backend-image.json
docker manifest inspect ghcr.io/gc-maplewind/maplewind-chatbot:latest >/tmp/chatbot-image.json
```

Latest handoff refs before this runbook update: main `dev` `22e149c3de1a9b0ecf20361152a45693ee9e0f05` and chatbot
`main` `8240db28ff058a216b017da1effb877d81290ee1`. If either branch has advanced, record the new refs and verify
that the chatbot workflow patch has been applied and successful GHCR evidence
exists for the image tags being deployed.

## 7-step cutover

```bash
set -euo pipefail
cd ~/dpbr_deploy/dpbr_backend
CUTOVER_DATE="$(date +%F)"

# 1. Immutable SQLite backups.
mkdir -p data/backups
cp data/maplewind.db "data/backups/maplewind.db.bak.${CUTOVER_DATE}"
cp data/chatbot.db "data/backups/chatbot.db.bak.${CUTOVER_DATE}"
sha256sum "data/backups/maplewind.db.bak.${CUTOVER_DATE}" "data/backups/chatbot.db.bak.${CUTOVER_DATE}" \
  | tee "data/backups/sqlite-backup-sha256.${CUTOVER_DATE}.txt"

# 2. Stop old SQLite-backed services.
docker compose --env-file .env stop backend chatbot || true

# 3. Start PostgreSQL and create maplewind/chatbot databases.
docker compose --env-file .env up -d postgres
until docker compose --env-file .env exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres; do sleep 2; done

# 4. Apply schemas and migrate both SQLite files.
docker compose --env-file .env run --rm backend uv run alembic upgrade head

docker run --rm --network dpbr-main_default \
  -v "$PWD/data/backups:/data:ro" \
  dimitri/pgloader:latest \
  pgloader "sqlite:////data/maplewind.db.bak.${CUTOVER_DATE}" \
  "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/maplewind"

docker run --rm --network dpbr-main_default \
  -v "$PWD/data/backups:/data:ro" \
  dimitri/pgloader:latest \
  pgloader "sqlite:////data/chatbot.db.bak.${CUTOVER_DATE}" \
  "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/chatbot"

# 5. Pull and start the split services.
docker compose --env-file .env pull backend chatbot
docker compose --env-file .env images backend chatbot
docker compose --env-file .env up -d --remove-orphans postgres backend chatbot

# 6. Update Kakao OpenBuilder webhook to the new chatbot route.
# Preferred: https://chatbot.maplewind.com/chatbot/chat
# Temporary compatibility route for at least 7 days: old /chatbot/chat path forwards to chatbot.

# 7. Smoke test production.
curl -sf http://127.0.0.1:8013/health
curl -sf http://127.0.0.1:8014/health
docker compose --env-file .env exec -T backend env | grep -E "^(DATABASE_URL)="
! docker compose --env-file .env exec -T backend env | grep -E "^(CHATBOT_|GOOGLE_)"
docker compose --env-file .env exec -T chatbot env | grep -E "^(CHATBOT_DATABASE_URL)="
! docker compose --env-file .env exec -T chatbot env | grep -E "^(DATABASE_URL=)"
# Then perform one Kakao "메생결산" flow and confirm the Google Sheet row appears.
```

## Row-count verification

```bash
uv run python -m scripts.verify_postgres_counts \
  main "data/backups/maplewind.db.bak.${CUTOVER_DATE}" \
  "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/maplewind"

uv run python -m scripts.verify_postgres_counts \
  chatbot "data/backups/chatbot.db.bak.${CUTOVER_DATE}" \
  "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/chatbot"
```

## Rollback

Use rollback if pgloader fails, row counts mismatch, health checks fail, or the Kakao smoke flow fails.

```bash
set -euo pipefail
cd ~/dpbr_deploy/dpbr_backend

# Stop split services.
docker compose --env-file .env stop backend chatbot

# Restore the previous SQLite-backed compose/image bundle from the backup kept before deploy.
cp docker-compose.yml.bak docker-compose.yml
# If DB files were modified during cutover, restore the immutable backups.
cp "data/backups/maplewind.db.bak.${CUTOVER_DATE}" data/maplewind.db
cp "data/backups/chatbot.db.bak.${CUTOVER_DATE}" data/chatbot.db

docker compose --env-file .env up -d backend
curl -sf http://127.0.0.1:8013/health
```

## Post-cutover monitoring

- Keep SQLite backups for at least 30 days.
- Monitor backend `/health`, `/api/v1/characters`, `/api/v1/settlements` 5xx rate for 7 days.
- Monitor chatbot p95/p99 latency for 24 hours; rollback or scale if p99 exceeds 4 seconds.
