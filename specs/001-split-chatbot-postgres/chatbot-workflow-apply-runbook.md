# Chatbot Workflow Apply Runbook

> Scope: apply the prepared chatbot CI/CD workflow patch to
> `GC-MapleWind/maplewind-chatbot` once a GitHub credential or GitHub App with
> `workflow` scope is available. This runbook does **not** perform production
> cutover.
> Capture the result with `chatbot-workflow-evidence-template.md`.

## Preconditions

- GitHub authentication can write `.github/workflows/*` in
  `GC-MapleWind/maplewind-chatbot`.
- `gh auth status` or API headers show `workflow` in the granted scopes.
- `GC-MapleWind/MSGS_13_B` `dev` contains
  `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`.
- Expected patch SHA-256:
  `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`.
- Expected chatbot base commit:
  `25ba79950d452fa07aadf486d253c4c7eb6f3b71` or a descendant where
  `git apply --check` still passes.

## Apply workflow files

```bash
set -euo pipefail

WORKDIR="${WORKDIR:-$HOME/workflow-apply-maplewind-chatbot}"
PATCH_SOURCE="${PATCH_SOURCE:-$HOME/dpbr_13_B/specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch}"

rm -rf "$WORKDIR"
git clone https://github.com/GC-MapleWind/maplewind-chatbot.git "$WORKDIR"
cd "$WORKDIR"
git checkout main
git pull --ff-only origin main

git apply --check "$PATCH_SOURCE"
sha256sum "$PATCH_SOURCE"
git apply "$PATCH_SOURCE"

git status --short
```

Expected `git status --short` output:

```text
A  .github/workflows/ci.yml
A  .github/workflows/deploy.yml
```

## Local pre-push verification

```bash
set -euo pipefail

uv sync --dev --frozen
uv run ruff check .
CHATBOT_DATABASE_URL=sqlite+aiosqlite:///./ci-chatbot.db \
  AUTO_CREATE_TABLES=true \
  GOOGLE_CREDENTIALS_PATH=./missing-google-credentials.json \
  ADMIN_SESSION_SECRET=ci-admin-secret \
  CHATBOT_AUTHORIZATION_KEY=ci-chatbot-key \
  uv run python -m unittest discover -s tests -v

CHATBOT_DATABASE_URL=postgresql+asyncpg://ci:ci@localhost:5432/chatbot \
  uv run alembic upgrade head --sql >/tmp/chatbot-alembic.sql

grep -n "type=sha,format=long,prefix=" .github/workflows/deploy.yml
```

Optional full local Docker smoke, matching the latest local audit:

```bash
docker build -t chatbot-ci-local:workflow-patch-apply .
```

## Commit and push

Use the Lore commit protocol required by the parent project:

```bash
git add .github/workflows/ci.yml .github/workflows/deploy.yml
git commit -m "Enable chatbot CI/CD workflows" \
  -m "Apply the prepared workflow patch so chatbot main can lint, test, build GHCR images, and deploy independently." \
  -m "Constraint: Requires a GitHub credential or app with workflow scope.\nRejected: Keeping workflows as a patch artifact | SC-005 requires remote workflow execution evidence.\nConfidence: high\nScope-risk: narrow\nDirective: Preserve GHCR tags :latest, :<full sha>, :main, and :main-* unless deploy consumers are updated.\nTested: git apply --check; uv sync --dev --frozen; uv run ruff check .; uv run python -m unittest discover -s tests -v; uv run alembic upgrade head --sql; docker build -t chatbot-ci-local:workflow-patch-apply .\nNot-tested: Production deploy until GitHub Actions run completes." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"

git push origin HEAD:main
```

## Remote verification

After push:

```bash
gh run list --repo GC-MapleWind/maplewind-chatbot --branch main --limit 5
gh run watch --repo GC-MapleWind/maplewind-chatbot <run-id>
gh run view --repo GC-MapleWind/maplewind-chatbot <run-id> --json conclusion,status,headSha,url
```

Required evidence before closing the workflow blocker:

- `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` exist on
  chatbot `main`.
- Chatbot CI run completes successfully.
- Deploy workflow builds/pushes GHCR image tags `:latest` and `:<full sha>`.
- If production deploy is enabled, deploy job completes successfully and
  `/health` on the deployed chatbot returns 200.

## Rollback

If the workflows fail due a patch/application issue rather than missing secrets:

```bash
git revert HEAD
git push origin HEAD:main
```

Keep `GC-MapleWind/maplewind-chatbot/issues/1` open until the remote workflow
run and GHCR/deploy evidence are linked there.
