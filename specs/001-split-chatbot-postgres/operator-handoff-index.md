# Operator Handoff Index — split-chatbot-postgres

This index points operators to the exact artifact to use for each remaining
external gate. The implementation and local dry-run evidence are recorded in
`completion-audit.md`; do not mark the overall goal complete until both gates
below have current remote/production evidence.

## Current source of truth

- Main repo branch: `GC-MapleWind/MSGS_13_B` `dev`
- Chatbot repo branch: `GC-MapleWind/maplewind-chatbot` `main`
- Completion ledger: `specs/001-split-chatbot-postgres/completion-audit.md`
- Durable handoff: `omx_wiki/split-chatbot-postgresql-migration-handoff.md`

## Gate A — Chatbot workflow application

Tracking issue: <https://github.com/GC-MapleWind/maplewind-chatbot/issues/1>

Use these files in order:

1. `chatbot-workflow-apply-runbook.md` — apply the prepared workflow patch with
   a credential or GitHub App that can write `.github/workflows/*`.
2. `chatbot-workflows-pending.patch` — adds chatbot `ci.yml` and `deploy.yml`.
3. `chatbot-workflow-evidence-template.md` — paste the completed evidence into
   issue #1.

Minimum evidence to close this gate:

- `workflow` authority proof or GitHub App write authority for workflow files.
- `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` exist on chatbot
  `main`.
- GitHub Actions CI run URL and success conclusion for the workflow commit.
- Deploy/build run URL and conclusion.
- GHCR image evidence for `:latest` and `:<full sha>` tags.

## Gate B — Production/staging cutover

Tracking issue: <https://github.com/GC-MapleWind/MSGS_13_B/issues/55>

Use these files in order:

1. `cutover-runbook.md` — production/staging cutover and rollback commands.
2. `production-cutover-evidence-template.md` — paste the completed evidence into
   issue #55.
3. `cutover-dryrun.md` — local dry-run reference only; it is not production
   proof.

Minimum evidence to close this gate:

- Production/staging SQLite backup filenames and SHA-256 hashes.
- PostgreSQL migration row-count match for both `maplewind` and `chatbot` DBs.
- Backend and chatbot health/API smoke results.
- Kakao webhook route plus 7-day compatibility route evidence.
- 메생결산 Google Sheets smoke confirmation.
- Downtime duration, 24h chatbot p95/p99, 7d backend 5xx monitoring links.
- Chatbot-only redeploy evidence showing no backend restart and <=60s redeploy.
- Backup retention/cold-storage owner/date.

## Quick observable status check

Run `./specs/001-split-chatbot-postgres/check-external-gates.sh` from a clone with `gh` authenticated to inspect observable remote status: current refs, workflow scope, chatbot workflow files, visible Actions runs, and blocker issue state. The script exits non-zero while observable blockers remain; that is expected before workflow/cutover evidence exists. It is diagnostic only, so a zero exit code is also not enough for completion proof; use the evidence templates above.

## Do not use as completion proof

- Local dry-run row counts alone.
- Local workflow patch simulation alone.
- A green main-repo CI run alone.
- The presence of this index, templates, or runbooks without the remote/ops
  transcripts they request.
