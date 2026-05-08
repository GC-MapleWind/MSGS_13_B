# Production Cutover Evidence Template — split-chatbot-postgres

> Purpose: paste this checklist into `GC-MapleWind/MSGS_13_B#55` while running
> the production/staging cutover. It is evidence capture, not a replacement for
> `cutover-runbook.md`.

## Run metadata

- Environment: `staging` / `production`
- Operator:
- Window start/end with timezone:
- Main deploy commit/image:
- Chatbot deploy commit/image:
- PostgreSQL image:
- Kakao webhook target after change:
- Compatibility route expiry date, at least 7 days after cutover:

## Pre-cutover backups — T001 / FR-003 / FR-012

```text
Command transcript:
- pwd:
- ls -lh data/maplewind.db data/chatbot.db:
- cp backup commands:
- sha256sum data/backups/maplewind.db.bak.<date> data/backups/chatbot.db.bak.<date>:
- backup retention/cold-storage target:
```

Evidence to attach:

- Backup filenames and SHA-256 hashes.
- Confirmation backups are immutable/read-only or copied to cold storage.
- Retention policy owner/date.

## Schema and migration — SC-001

```text
Command transcript:
- docker compose --env-file .env up -d postgres:
- pg_isready output:
- backend alembic upgrade output:
- chatbot alembic upgrade output, if run separately:
- pgloader maplewind output:
- pgloader chatbot output:
- verify_postgres_counts main output:
- verify_postgres_counts chatbot output:
```

Required result:

- Every migrated table row count matches the SQLite backup-time count.
- Any mismatch stops cutover and triggers rollback.

## Service startup — FR-001 / FR-002 / FR-004 / FR-005 / FR-010 / FR-016

```text
Command transcript:
- docker compose --env-file .env pull backend chatbot:
- docker compose --env-file .env up -d --remove-orphans postgres backend chatbot:
- docker compose --env-file .env ps:
- docker compose --env-file .env logs --tail=100 backend:
- docker compose --env-file .env logs --tail=100 chatbot:
- docker inspect env summary showing backend has DATABASE_URL only and chatbot has CHATBOT_DATABASE_URL only:
```

Required result:

- Backend container and chatbot container are separate images/services.
- Backend uses only the `maplewind` DB URL.
- Chatbot uses only the `chatbot` DB URL.
- Backend does not receive `GOOGLE_*` or `CHATBOT_*` secrets.
- Chatbot does not receive `DATABASE_URL`.

## Smoke tests — US1 / SC-002

```text
Command transcript:
- curl -sf http://127.0.0.1:8013/health:
- curl -sf http://127.0.0.1:8014/health:
- GET /v1/characters status:
- GET /v1/settlements status:
- one Kakao "메생결산" flow timestamp:
- Google Sheet row confirmation timestamp / row id:
- total downtime minutes:
```

Required result:

- Backend health and core read APIs return success.
- Chatbot health returns success.
- Exactly one 메생결산 submission is recorded in Google Sheets.
- Cutover downtime is 30 minutes or less.

## Webhook and compatibility routing — FR-009

```text
Command transcript / screenshots:
- Kakao OpenBuilder webhook URL after change:
- reverse proxy rule for https://chatbot.maplewind.com/chatbot/chat:
- temporary compatibility rule for old /chatbot/chat route:
- compatibility route planned removal date:
```

Required result:

- New chatbot route is active.
- Old route forwards to chatbot for at least 7 days.

## SLA and isolation validation — US3 / SC-003 / SC-004 / SC-007

```text
Command transcript:
- chatbot 10-call latency sample under main-backend load:
- p95 latency:
- p99 latency:
- chatbot-only redeploy command and elapsed seconds:
- backend container id before redeploy:
- backend container id after redeploy:
- chatbot crash test command:
- backend /health during chatbot crash:
- backend /v1/characters during chatbot crash:
```

Required result:

- Chatbot p95 <= 3s and p99 <= 4s during the validation window.
- Main backend 5xx rate stays <= 0.1% over the 7-day observation window.
- Chatbot-only redeploy completes in <= 60s without backend container restart.
- Chatbot crash does not break main backend health/core reads.

## Rollback decision

- Rollback needed: `yes` / `no`
- If yes, rollback commands run:
- Health after rollback:
- Issue/incident link:

## Post-cutover cleanup gates — T042 / T043

- Date `migrate_user_student_id_to_username` was confirmed unnecessary after cutover:
- Commit/PR removing that legacy helper, if completed:
- SQLite backup retention date or cold-storage location:
- Owner for deleting/archiving backups after 30 days:

## Final issue comment summary

```markdown
Cutover evidence summary:
- Environment:
- Window:
- Main image:
- Chatbot image:
- SQLite backup SHA-256 files:
- Row-count result:
- Backend health/core APIs:
- Chatbot health:
- Kakao/Google Sheets smoke:
- Downtime:
- Webhook route + 7-day compatibility expiry:
- SLA p95/p99:
- Chatbot-only redeploy elapsed/backend restart evidence:
- 24h/7d monitoring links:
- Rollback used?:
- Remaining follow-ups:
```
