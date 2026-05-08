# Production Cutover Evidence Template — split-chatbot-postgres

> Purpose: paste this checklist into `GC-MapleWind/MSGS_13_B#55` while running
> the production/staging cutover. It is evidence capture, not a replacement for
> `cutover-runbook.md`.

## Run metadata

- Environment: `staging` / `production`
- Operator:
- Window start/end with timezone:
- Main deploy commit/image/tag/digest:
- Chatbot deploy commit/image/tag/digest:
- Gate A evidence issue/comment proving chatbot workflows and GHCR tags are present:
- Gate A issue #1 state / closure URL:
- PostgreSQL image:
- Kakao webhook target after change:
- Compatibility route expiry date, at least 7 days after cutover:

## Preflight dependency evidence — Gate A / SC-005

```text
Command transcript:
- git ls-remote https://github.com/GC-MapleWind/MSGS_13_B.git refs/heads/dev:
- git ls-remote https://github.com/GC-MapleWind/maplewind-chatbot.git refs/heads/main:
- gh issue view 1 --repo GC-MapleWind/maplewind-chatbot --json state,title,url:
- gh api repos/GC-MapleWind/maplewind-chatbot/contents/.github/workflows?ref=main:
- gh api 'repos/GC-MapleWind/maplewind-chatbot/actions/runs?branch=main&per_page=5':
- gh api /orgs/GC-MapleWind/packages/container/maplewind-chatbot or package UI link:
- docker manifest inspect ghcr.io/gc-maplewind/msgs_13_b-backend:<tag>:
- docker manifest inspect ghcr.io/gc-maplewind/maplewind-chatbot:<tag>:
```

Required result:

- `GC-MapleWind/maplewind-chatbot#1` is `CLOSED` before production/staging cutover starts.
- Chatbot `.github/workflows/ci.yml` and `deploy.yml` exist on remote `main`.
- Chatbot CI/deploy or image-build evidence is linked from `maplewind-chatbot#1`.
- `ghcr.io/gc-maplewind/maplewind-chatbot:<tag>` exists for the exact tag/digest being deployed.
- Main and chatbot refs are recorded from fresh `git ls-remote` output; do not rely on stale handoff examples for production evidence.

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
- docker compose --env-file .env images backend chatbot:
- docker compose --env-file .env up -d --remove-orphans postgres backend chatbot:
- docker compose --env-file .env ps:
- docker compose --env-file .env logs --tail=100 backend:
- docker compose --env-file .env logs --tail=100 chatbot:
- docker compose --env-file .env exec -T backend env filtered to DATABASE_URL and absence of CHATBOT_/GOOGLE_ variables:
- docker compose --env-file .env exec -T chatbot env filtered to CHATBOT_DATABASE_URL and absence of DATABASE_URL:
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


Before posting the final summary to issue #55, save the draft to a local file and run:

```bash
specs/001-split-chatbot-postgres/validate-cutover-evidence-summary.sh <draft.md>
```

This only checks that the required `Cutover evidence summary:` fields are present
in one block with non-placeholder values; it does not replace the live readiness
checker after the comment is posted.

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
