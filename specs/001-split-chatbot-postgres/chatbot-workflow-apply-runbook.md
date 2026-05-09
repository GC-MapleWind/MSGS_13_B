# Chatbot Workflow Apply Runbook

> Scope: apply the prepared chatbot CI/CD workflow patch to
> `GC-MapleWind/maplewind-chatbot` once a GitHub credential or GitHub App with
> `workflow` scope is available; GHCR verification later in this runbook also
> needs `read:packages`, equivalent GitHub App/package permission, or public
> package evidence. This runbook does **not** perform production cutover.
> Capture the result with `chatbot-workflow-evidence-template.md`.

## Preconditions

- GitHub authentication can write `.github/workflows/*` in
  `GC-MapleWind/maplewind-chatbot`.
- `gh auth status` succeeds and API headers show `workflow` in the granted scopes, or a GitHub App has equivalent permission to write workflow files.
- GHCR package verification can use `read:packages`, equivalent GitHub App/package permission, or public package evidence.
- `GC-MapleWind/MSGS_13_B` `dev` contains
  `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`.
- Expected patch SHA-256:
  `ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4`.
- Expected verified chatbot base checkpoint:
  `8240db28ff058a216b017da1effb877d81290ee1` or a descendant where
  `git apply --check` still passes.

## Optional helper script

For a guarded, non-pushing preparation flow, run:

```bash
specs/001-split-chatbot-postgres/prepare-chatbot-workflows.sh --allow-missing-workflow-scope
```

With a workflow-scoped credential, use the same helper without
`--allow-missing-workflow-scope`; add `--run-local-checks` for local lint/test
checks and `--commit --push` only when ready to write chatbot `main`. The helper
verifies the pending patch SHA-256, applies it to a fresh chatbot clone, checks
the required GHCR tag metadata, and stops before push by default.

## Verify credential and patch inputs

```bash
set -euo pipefail

EXPECTED_PATCH_SHA="ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4"
EXPECTED_CHATBOT_BASE="8240db28ff058a216b017da1effb877d81290ee1"

gh auth status -h github.com
gh api -i user | awk 'BEGIN{IGNORECASE=1} /^x-oauth-scopes:/ {print}'
gh api -i user | awk 'BEGIN{IGNORECASE=1; ok=0} /^x-oauth-scopes:/ && $0 ~ /workflow/ {ok=1} END{exit ok ? 0 : 1}'
# Required for private GHCR API verification; if this fails, attach public package UI/API proof instead.
gh api -i user | awk 'BEGIN{IGNORECASE=1; ok=0} /^x-oauth-scopes:/ && $0 ~ /read:packages/ {ok=1} END{exit ok ? 0 : 1}' || echo 'read:packages missing; use GitHub App/package permission or public GHCR evidence later'

sha256sum --check <<EOF
${EXPECTED_PATCH_SHA}  ${PATCH_SOURCE:-$HOME/dpbr_13_B/specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch}
EOF

git ls-remote https://github.com/GC-MapleWind/maplewind-chatbot.git refs/heads/main
```

If the `workflow` scope check fails, stop and use a workflow-scoped PAT or GitHub App. If only the `read:packages` check fails, continue only if the package will be public or equivalent package-visibility evidence can be attached.
The documented patch check in the main handoff verified clean application to
chatbot `main` `8240db28ff058a216b017da1effb877d81290ee1`; if `main` has
advanced, `git apply --check` below is the authority.

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

base_commit=$(git rev-parse HEAD)
echo "chatbot_base_commit=$base_commit"
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

Optional full local Docker smoke, matching the documented local audit:

```bash
docker build -t chatbot-ci-local:workflow-patch-apply .
```

## Commit and push

Use the Lore commit protocol required by the parent project:

```bash
git add .github/workflows/ci.yml .github/workflows/deploy.yml
commit_body=$(cat <<'EOF_COMMIT_BODY'
Apply the prepared workflow patch so chatbot main can lint, test, build GHCR images, and deploy independently.

Constraint: Requires a GitHub credential or app with workflow scope.
Rejected: Keeping workflows as a patch artifact | SC-005 requires remote workflow execution evidence.
Confidence: high
Scope-risk: narrow
Directive: Preserve GHCR tags :latest, :<full sha>, :main, and :main-* unless deploy consumers are updated.
Tested: git apply --check; uv sync --dev --frozen; uv run ruff check .; uv run python -m unittest discover -s tests -v; uv run alembic upgrade head --sql; docker build -t chatbot-ci-local:workflow-patch-apply .
Not-tested: Production deploy until GitHub Actions run completes.
Co-authored-by: OmX <omx@oh-my-codex.dev>
EOF_COMMIT_BODY
)
git commit -m "Enable chatbot CI/CD workflows" -m "$commit_body"

git push origin HEAD:main
```

## Remote verification

After push:

```bash
gh api 'repos/GC-MapleWind/maplewind-chatbot/actions/runs?branch=main&per_page=5'
gh run watch --repo GC-MapleWind/maplewind-chatbot <run-id>
gh run view --repo GC-MapleWind/maplewind-chatbot <run-id> --json conclusion,status,headSha,url
gh api '/orgs/GC-MapleWind/packages/container/maplewind-chatbot'
gh api '/orgs/GC-MapleWind/packages/container/maplewind-chatbot/versions?per_page=10'
```

Required evidence before closing the workflow blocker:

- `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` exist on
  chatbot `main`.
- Chatbot CI run completes successfully.
- Deploy workflow builds/pushes GHCR image tags `:latest` and `:<full sha>`.
- GHCR package/tag visibility is confirmed with a `read:packages`-capable credential, GitHub App/package permission, or public package evidence.
- If GHCR API access uses a private package, the credential/package permission used for verification is recorded in `chatbot-workflow-evidence-template.md`.
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
