# Chatbot Workflow Evidence Template — split-chatbot-postgres

> Purpose: paste this checklist into `GC-MapleWind/maplewind-chatbot#1` when a
> GitHub credential or app with `workflow` scope applies
> `chatbot-workflows-pending.patch`. It captures the proof needed for T029/T030
> and SC-005. Use `chatbot-workflow-apply-runbook.md` for the commands.

## Run metadata

- Operator:
- Credential type: user PAT / GitHub App / other
- Granted scopes shown by `gh api -i user` or equivalent:
- MSGS_13_B dev commit containing the patch: `4f4097cfdb9cd774b67df29f83008f3a10f742fc` or later `dev` descendant containing `chatbot-workflows-pending.patch`
- Patch SHA-256: `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`
- Chatbot base commit before applying patch: latest verified base `8240db28ff058a216b017da1effb877d81290ee1`, or a later `main` descendant where `git apply --check` passes
- Chatbot commit after applying patch:
- Workflow application time with timezone:

## Pre-apply checks

```text
Command transcript:
- gh auth status:
- gh api -i user scope headers, including `workflow` or equivalent GitHub App permission:
- git ls-remote origin refs/heads/main:
- sha256sum --check for chatbot-workflows-pending.patch:
- git apply --check chatbot-workflows-pending.patch:
```

Required result:

- Granted scopes include `workflow` or the GitHub App can write workflow files.
- Patch SHA-256 matches the value in `chatbot-workflow-apply-runbook.md`.
- `git apply --check` passes on current chatbot `main` or a documented
  descendant.

## Local verification before push

```text
Command transcript:
- uv sync --dev --frozen:
- uv run ruff check .:
- CHATBOT_DATABASE_URL=sqlite+aiosqlite:///./ci-chatbot.db AUTO_CREATE_TABLES=true ... uv run python -m unittest discover -s tests -v:
- CHATBOT_DATABASE_URL=postgresql+asyncpg://ci:ci@localhost:5432/chatbot uv run alembic upgrade head --sql:
- grep -n "type=sha,format=long,prefix=" .github/workflows/deploy.yml:
- optional docker build output:
```

Required result:

- Lint passes.
- Unit tests pass.
- Alembic offline SQL renders.
- Deploy workflow keeps `:latest` and `:<full sha>` GHCR tag support.

## Push evidence

```text
Command transcript:
- git status --short:
- git commit output:
- git push origin HEAD:main output:
- git ls-remote origin refs/heads/main after push:
- gh api repos/GC-MapleWind/maplewind-chatbot/contents/.github/workflows?ref=main:
```

Required result:

- `.github/workflows/ci.yml` exists on chatbot `main`.
- `.github/workflows/deploy.yml` exists on chatbot `main`.
- The pushed commit uses the Lore commit protocol and includes
  `Co-authored-by: OmX <omx@oh-my-codex.dev>`.

## GitHub Actions evidence — SC-005

```text
Command transcript:
- gh run list --repo GC-MapleWind/maplewind-chatbot --limit 10:
- gh run view <ci-run-id> --repo GC-MapleWind/maplewind-chatbot --json status,conclusion,headSha,url:
- gh run view <deploy-run-id> --repo GC-MapleWind/maplewind-chatbot --json status,conclusion,headSha,url:
- gh run view <deploy-run-id> --repo GC-MapleWind/maplewind-chatbot --log-failed, if failed:
```

Required result:

- CI workflow conclusion is `success` for the workflow commit.
- Deploy workflow reaches the expected conclusion for the environment.
- GHCR push/build step succeeds, or any environment-secret deployment skip is
  clearly documented separately from image build success.

## GHCR image evidence

```text
Evidence to paste:
- Package URL:
- Image digest:
- Tags observed: latest, <full sha>, main, main-*
- Command/API used to confirm tags:
```

Required result:

- `ghcr.io/gc-maplewind/maplewind-chatbot:latest` exists.
- `ghcr.io/gc-maplewind/maplewind-chatbot:<full sha>` exists for the workflow
  commit.

## Post-apply issue summary

```markdown
Chatbot workflow evidence summary:
- Applied from MSGS_13_B dev:
- Patch SHA-256:
- Chatbot workflow commit:
- CI run URL/conclusion:
- Deploy/build run URL/conclusion:
- GHCR image tags/digest:
- Remote workflow files API result:
- Remaining follow-ups:
```
