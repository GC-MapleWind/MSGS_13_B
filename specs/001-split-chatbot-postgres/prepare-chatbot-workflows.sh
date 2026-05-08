#!/usr/bin/env bash
set -euo pipefail

EXPECTED_PATCH_SHA="ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4"
CHATBOT_REPO_URL="https://github.com/GC-MapleWind/maplewind-chatbot.git"
CHATBOT_REPO="GC-MapleWind/maplewind-chatbot"
PATCH_SOURCE=""
WORKDIR=""
RUN_LOCAL_CHECKS=0
CREATE_COMMIT=0
PUSH=0
ALLOW_MISSING_WORKFLOW_SCOPE=0

usage() {
  cat <<'USAGE'
Usage: prepare-chatbot-workflows.sh [options]

Safely prepare the pending chatbot CI/CD workflow patch against
GC-MapleWind/maplewind-chatbot. By default this script clones a fresh worktree,
verifies the patch hash and GitHub scopes, applies the patch, and stops before
commit/push. Use it from a main-repo checkout that contains
specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch.

Options:
  --patch PATH                       Override patch path.
  --workdir DIR                      Use/create this clone directory instead of a temp dir.
  --run-local-checks                 Run uv sync, ruff, unittest, Alembic offline SQL, and tag-shape check.
  --commit                           Create the Lore-protocol workflow commit after applying the patch.
  --push                             Push HEAD to chatbot main; implies --commit.
  --allow-missing-workflow-scope      Allow local-only preparation without workflow scope; push remains blocked.
  -h, --help                         Show this help.

Evidence still required after push: remote workflow files, successful chatbot CI,
GHCR tags/digest, and issue #1 `Chatbot workflow evidence summary:` block.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --patch)
      PATCH_SOURCE="${2:?missing value for --patch}"
      shift 2
      ;;
    --workdir)
      WORKDIR="${2:?missing value for --workdir}"
      shift 2
      ;;
    --run-local-checks)
      RUN_LOCAL_CHECKS=1
      shift
      ;;
    --commit)
      CREATE_COMMIT=1
      shift
      ;;
    --push)
      CREATE_COMMIT=1
      PUSH=1
      shift
      ;;
    --allow-missing-workflow-scope)
      ALLOW_MISSING_WORKFLOW_SCOPE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

has_oauth_scope() {
  local scope="$1"
  gh api -i user 2>/dev/null | awk -v wanted="$scope" '
    BEGIN { IGNORECASE = 1; ok = 0 }
    /^x-oauth-scopes:/ {
      split($0, parts, ":")
      scopes = parts[2]
      gsub(/\r/, "", scopes)
      n = split(scopes, arr, ",")
      for (i = 1; i <= n; i++) {
        gsub(/^ +| +$/, "", arr[i])
        if (arr[i] == wanted) ok = 1
      }
    }
    END { exit ok ? 0 : 1 }
  '
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [[ -z "$PATCH_SOURCE" ]]; then
  PATCH_SOURCE="$repo_root/specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch"
fi

require_cmd git
require_cmd gh
require_cmd sha256sum

if [[ ! -f "$PATCH_SOURCE" ]]; then
  echo "Patch file not found: $PATCH_SOURCE" >&2
  exit 1
fi

actual_sha="$(sha256sum "$PATCH_SOURCE" | awk '{print $1}')"
if [[ "$actual_sha" != "$EXPECTED_PATCH_SHA" ]]; then
  echo "Patch SHA-256 mismatch" >&2
  echo "expected=$EXPECTED_PATCH_SHA" >&2
  echo "actual=$actual_sha" >&2
  exit 1
fi

echo "PASS patch_sha=$actual_sha"

gh auth status -h github.com >/dev/null
scopes_line="$(gh api -i user | awk 'BEGIN{IGNORECASE=1} /^x-oauth-scopes:/ {gsub(/\r/, ""); print}')"
echo "INFO ${scopes_line:-x-oauth-scopes header not found}"

if ! has_oauth_scope workflow; then
  if [[ "$ALLOW_MISSING_WORKFLOW_SCOPE" -eq 1 && "$PUSH" -eq 0 ]]; then
    echo "WARN workflow scope missing; continuing local-only because --allow-missing-workflow-scope was set"
  else
    echo "Missing required GitHub OAuth scope: workflow" >&2
    echo "Use a workflow-scoped credential or GitHub App before applying/pushing workflow files." >&2
    exit 1
  fi
fi

if ! has_oauth_scope read:packages; then
  echo "WARN read:packages scope missing; GHCR verification may require public package evidence or app/package permission"
fi

if [[ "$PUSH" -eq 1 ]] && ! has_oauth_scope workflow; then
  echo "Refusing --push without workflow scope" >&2
  exit 1
fi

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$(mktemp -d /tmp/maplewind-chatbot-workflows-XXXXXX)"
  rm -rf "$WORKDIR"
fi

if [[ -e "$WORKDIR" && -n "$(find "$WORKDIR" -mindepth 1 -maxdepth 1 2>/dev/null || true)" ]]; then
  echo "Workdir exists and is not empty: $WORKDIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$WORKDIR")"
git clone "$CHATBOT_REPO_URL" "$WORKDIR"
cd "$WORKDIR"
git checkout main
git pull --ff-only origin main

base_commit="$(git rev-parse HEAD)"
echo "INFO chatbot_base_commit=$base_commit"

git apply --check "$PATCH_SOURCE"
git apply "$PATCH_SOURCE"

status="$(git status --short --untracked-files=all)"
printf 'INFO applied_status:\n%s\n' "$status"
if [[ ! -f .github/workflows/ci.yml ]]; then
  echo "Expected .github/workflows/ci.yml to exist after patch application" >&2
  exit 1
fi
if [[ ! -f .github/workflows/deploy.yml ]]; then
  echo "Expected .github/workflows/deploy.yml to exist after patch application" >&2
  exit 1
fi

grep -n 'type=raw,value=latest' .github/workflows/deploy.yml
grep -n 'type=sha,format=long,prefix=' .github/workflows/deploy.yml
grep -n 'type=raw,value=main' .github/workflows/deploy.yml
grep -n 'type=sha,prefix=main-' .github/workflows/deploy.yml

if [[ "$RUN_LOCAL_CHECKS" -eq 1 ]]; then
  require_cmd uv
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
fi

if [[ "$CREATE_COMMIT" -eq 1 ]]; then
  tested_detail="git apply --check; GHCR tag metadata check"
  if [[ "$RUN_LOCAL_CHECKS" -eq 1 ]]; then
    tested_detail="$tested_detail; uv sync --dev --frozen; uv run ruff check .; uv run python -m unittest discover -s tests -v; uv run alembic upgrade head --sql"
  fi
  git add .github/workflows/ci.yml .github/workflows/deploy.yml
  git commit -m "Enable chatbot CI/CD workflows" \
    -m "Apply the prepared workflow patch so chatbot main can lint, test, build GHCR images, and deploy independently.\n\nConstraint: Requires a GitHub credential or app with workflow scope.\nRejected: Keeping workflows as a patch artifact | SC-005 requires remote workflow execution evidence.\nConfidence: high\nScope-risk: narrow\nDirective: Preserve GHCR tags :latest, :<full sha>, :main, and :main-* unless deploy consumers are updated.\nTested: $tested_detail.\nNot-tested: Production deploy until GitHub Actions run completes.\nCo-authored-by: OmX <omx@oh-my-codex.dev>"
fi

if [[ "$PUSH" -eq 1 ]]; then
  git push origin HEAD:main
  echo "PUSHED chatbot workflow commit=$(git rev-parse HEAD)"
else
  cat <<EOF_NEXT

Prepared chatbot workflow patch in: $WORKDIR
Base commit: $base_commit

Next steps:
1. Inspect the prepared diff:
   git -C '$WORKDIR' diff -- .github/workflows/ci.yml .github/workflows/deploy.yml
2. If local checks were not requested, rerun this helper from a fresh workdir with --run-local-checks before committing.
3. Commit and push with a workflow-scoped credential, or rerun with --commit --push.
4. Record issue #1 evidence using chatbot-workflow-evidence-template.md.
EOF_NEXT
fi
