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
   Patch SHA-256: `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`.
3. `chatbot-workflow-evidence-template.md` — paste the completed evidence into
   issue #1.

Minimum evidence to close this gate:

- `workflow` authority proof or GitHub App write authority for workflow files.
- `read:packages` authority, GitHub App/package permission, or public package UI/API proof for GHCR visibility.
- `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` exist on chatbot
  `main`.
- GitHub Actions CI run URL and `success` conclusion for the workflow commit.
- Deploy/build run URL and expected conclusion for the workflow commit.
- Remote `deploy.yml` preserves GHCR tag metadata for `:latest`, `:<full sha>`, and `:main-*`.
- GHCR image evidence for `:latest`, `:<full sha>`, `:main`, and `:main-*` tags, including visibility method and digest.

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

## Optional maintenance — Main workflow runtime refresh

This is not a split-chatbot-postgres completion gate. If GitHub Actions Node 20
deprecation warnings need cleanup, use:

1. `main-workflow-runtime-refresh-runbook.md` — apply instructions.
2. `main-workflow-runtime-refresh-pending.patch` — prepared `.github/workflows/deploy.yml` update.
   Patch SHA-256: `f52d29ef07b1164abf185c403f8d862862c3aca5cc899ca9bb9254cbcba9e2ee`.

The current session could not push this workflow-file change because the OAuth
credential lacks `workflow` scope.

## Observable checkpoint

- Historical gate-check input after the Gate A closure hard-stop update: `origin/dev` `415235d0fae96eb0bfb22539d843dba07ce4de3d` and chatbot `origin/main` `8240db28ff058a216b017da1effb877d81290ee1`.
- `check-external-gates.sh` still exits non-zero because chatbot workflow files are absent on remote, no chatbot Actions run or GHCR package evidence is visible, the current credential lacks `workflow` and `read:packages` scopes, and blocker issues #1/#55 remain open. The GHCR package check currently reports HTTP 404 for `GC-MapleWind/maplewind-chatbot`; if the package later becomes visible, missing `latest`, full-sha, `main`, or `main-*` tags fail the checker.
- Direct remote-tree cross-check: a shallow clone of `GC-MapleWind/maplewind-chatbot` `main` at `8240db28ff058a216b017da1effb877d81290ee1` has no `.github/workflows` directory. This corroborates the workflow gate blocker independently of the GitHub Contents API 404 response.
- Linked issue checkpoints are advisory handoff notes; rerun `check-completion-readiness.sh` for current status and use the issue timeline for the newest comment.
- Later documentation-only sync commits may advance `dev` without changing the
  external gate state; run the checker below for the current observable status.
- Documentation link-hygiene checkpoint: commit `f72d9197aca0893c2ac26cfc62c20664c4bafd8f` checked 34 local Markdown links with 0 missing and was echoed to chatbot #1 `#issuecomment-4409355366` and main #55 `#issuecomment-4409355456`.
- Placeholder-evidence checker checkpoint: commit `93f7bb3565978a0c27ab39849df64e842b1d92ab` rejects punctuated/spaced placeholder variants in required evidence fields; dev Actions run `25582935740` succeeded. This is main-dev checker evidence only and does not close external gates. Issue checkpoints: chatbot #1 `https://github.com/GC-MapleWind/maplewind-chatbot/issues/1#issuecomment-4410406164` and main #55 `https://github.com/GC-MapleWind/MSGS_13_B/issues/55#issuecomment-4410406223`.

## Quick observable status check

Run `./specs/001-split-chatbot-postgres/check-external-gates.sh` from a clone with `gh` authenticated to inspect observable remote status: current refs, workflow/read:packages scopes, chatbot workflow files, visible Actions runs, GHCR package visibility, required `:latest` / `:<full sha>` / `:main` / `:main-*` tags, required deploy.yml GHCR tag metadata, and blocker issue state. The script exits non-zero while observable blockers remain, including open blocker issues; that is expected before workflow/cutover evidence exists. It is diagnostic only, so a zero exit code is also not enough for completion proof; use the evidence templates above.

Run `bash specs/001-split-chatbot-postgres/check-external-gates.sh --self-test`
to verify the local GHCR tag parser without touching GitHub APIs. The self-test
checks exact required-tag matches and false-positive rejection for near-miss
`latest`, `main`, and `main-*` tags. The combined readiness wrapper runs this
parser self-test before live external diagnostics.

Run `python3 specs/001-split-chatbot-postgres/check-objective-coverage.py` to
verify that `completion-audit.md` still maps every task, FR, SC, prompt task ID,
and local Markdown link from the active objective inputs. This coverage guard is
documentation-only and does not replace live external gate evidence.

Run `bash specs/001-split-chatbot-postgres/check-completion-readiness.sh` when
you want both checks in one command. It fails if either the documentation
coverage guard or live external gate diagnostics fail, but it is still not a
substitute for the evidence transcripts requested by the templates above.
The external gate checker reads blocker issues with `gh issue view` first and
falls back to the REST issues API if GraphQL is transiently unavailable;
`check-external-gates.sh --self-test` verifies the fallback emits a clean
tab-separated issue line for the readiness parser and that issue evidence
summary markers are detected/rejected correctly. When blocker issues are closed,
the live checker still fails if the expected Gate A/Gate B evidence summary
markers are absent as standalone lines in the issue timeline, or if
representative required fields are missing from the same issue body/comment
block; advisory comments, empty headings, empty required-field labels,
placeholder values such as `TBD`/`pending`, or marker/field fragments split
across comments do not count.

## Final completion audit checklist

Before closing the overall split-chatbot-postgres objective or calling any goal
complete, perform all of the following on the current branches:

1. Restate the objective as concrete deliverables: chatbot repo/workflows/GHCR,
   PostgreSQL migration evidence, production/staging cutover, rollback/retention,
   and monitoring/SLA gates.
2. Rerun `python3 specs/001-split-chatbot-postgres/check-objective-coverage.py`
   and confirm it still covers every task ID, FR, SC, prompt task ID, and local
   Markdown link from `codex-prompts.md`, `spec.md`, `tasks.md`, `plan.md`, and
   `.cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md`.
3. Rerun `bash specs/001-split-chatbot-postgres/check-completion-readiness.sh`
   and require exit code `0`; if it exits non-zero, stop and treat the objective
   as incomplete.
4. Inspect issue #1 and issue #55 directly. Do not treat "CLOSED" as sufficient
   unless the issue timeline contains the completed template evidence listed in
   Gate A and Gate B above.
5. Verify the cited Actions, GHCR package/tag/digest, backup/hash, row-count,
   health-smoke, webhook, monitoring, and backup-retention links are current and
   correspond to the same branch refs being audited.
6. Update `completion-audit.md` with the final evidence refs and any residual
   risks. Only then may the objective be considered complete.

## Do not use as completion proof

- Closed blocker issues without their completed evidence templates.
- Local dry-run row counts alone.
- Local workflow patch simulation alone.
- A green main-repo CI run alone.
- The presence of this index, templates, or runbooks without the remote/ops
  transcripts they request.
