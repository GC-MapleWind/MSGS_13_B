# Main Workflow Runtime Refresh Runbook

> Scope: optional maintenance for `GC-MapleWind/MSGS_13_B` after GitHub Actions
> warned that Node.js 20 actions are deprecated. This is not a completion gate
> for split-chatbot-postgres, but it reduces future CI risk.

## Why this exists

A local audit found that these action majors declare Node 24-compatible
runtimes in their upstream `action.yml` files:

- `actions/checkout@v5` → `using: node24`
- `docker/setup-buildx-action@v4` → `using: node24`
- `docker/login-action@v4` → `using: node24`
- `docker/metadata-action@v6` → `using: node24`

`docker/build-push-action@v6` still declares Node 20, so this patch leaves
`docker/build-push-action@v5` unchanged rather than making a major bump that
would not address the warning class.

Directly pushing `.github/workflows/deploy.yml` failed with the current OAuth
credential because it lacks `workflow` scope. The prepared patch is preserved at
`main-workflow-runtime-refresh-pending.patch` for a workflow-scoped operator.

Expected patch SHA-256: `f52d29ef07b1164abf185c403f8d862862c3aca5cc899ca9bb9254cbcba9e2ee`.

## Apply

```bash
set -euo pipefail

PATCH_SOURCE="${PATCH_SOURCE:-$PWD/specs/001-split-chatbot-postgres/main-workflow-runtime-refresh-pending.patch}"

git clone https://github.com/GC-MapleWind/MSGS_13_B.git msgs-main-workflow-refresh
cd msgs-main-workflow-refresh
git checkout dev
git pull --ff-only origin dev

sha256sum "$PATCH_SOURCE"
git apply --check "$PATCH_SOURCE"
git apply "$PATCH_SOURCE"

git diff --check
git diff -- .github/workflows/deploy.yml
```

## Commit and push

```bash
git add .github/workflows/deploy.yml
git commit -m "Refresh GitHub Actions runtimes" \
  -m "Move checkout, setup-buildx, login, and metadata actions to Node 24-capable major versions to reduce the runner deprecation risk while leaving build-push pinned because its current major still uses Node 20." \
  -m "Constraint: GitHub Actions warns that Node 20 actions will be forced toward Node 24 in 2026.\nRejected: Updating docker/build-push-action only for version freshness | v6 still declares node20, so it does not address the warning class.\nConfidence: medium\nScope-risk: narrow\nDirective: Re-check action.yml runtimes before changing build-push-action or future action majors.\nTested: inspected upstream action.yml runtime declarations for checkout v5, setup-buildx v4, login v4, metadata v6, and build-push v6; git diff --check.\nNot-tested: GitHub Actions run is triggered after push." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"

git push origin HEAD:dev
```

## Verify

```bash
gh run list --repo GC-MapleWind/MSGS_13_B --limit 5
gh run watch --repo GC-MapleWind/MSGS_13_B <run-id> --exit-status
gh run view --repo GC-MapleWind/MSGS_13_B <run-id> --json status,conclusion,headSha,url
```

Expected result: the dev build/deploy workflow succeeds. Some Node 20 warning
may remain while `docker/build-push-action` itself is still Node 20 upstream.
