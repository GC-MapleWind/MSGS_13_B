#!/usr/bin/env bash
# Dry-run helper for the MSGS_13_B dev -> main promotion gate.
# This script is intentionally non-destructive: it never pushes, creates PRs,
# merges branches, or changes protected branches. It only inspects remotes and
# performs a temporary no-commit merge rehearsal that is removed before exit.

set -u -o pipefail

MAIN_REPO="${MAIN_REPO:-GC-MapleWind/MSGS_13_B}"
DEV_BRANCH="${DEV_BRANCH:-dev}"
PROD_BRANCH="${PROD_BRANCH:-main}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
failures=0

usage() {
  cat <<USAGE
Usage: ${0##*/} [--self-test] [--help]

Dry-run the ${DEV_BRANCH} -> ${PROD_BRANCH} promotion gate for ${MAIN_REPO}.
No remote changes are made.

Environment overrides:
  MAIN_REPO=${MAIN_REPO}
  DEV_BRANCH=${DEV_BRANCH}
  PROD_BRANCH=${PROD_BRANCH}
USAGE
}

fail() { printf 'FAIL %s\n' "$*" >&2; failures=$((failures + 1)); return 1; }
info() { printf 'INFO %s\n' "$*"; }
pass() { printf 'PASS %s\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

check_promotion_pr_decision() {
  ahead_by="$1"
  prs="$2"

  if [[ "${ahead_by:-1}" -gt 0 ]]; then
    fail "origin/${DEV_BRANCH} has ${ahead_by} unpromoted commits relative to origin/${PROD_BRANCH}" || true
    if [[ -n "${prs}" ]]; then
      pass "open ${DEV_BRANCH} -> ${PROD_BRANCH} promotion PR exists"
      printf '%s\n' "${prs}"
    else
      fail "no open ${DEV_BRANCH} -> ${PROD_BRANCH} promotion PR is visible" || true
    fi
  else
    pass "origin/${DEV_BRANCH} has no unpromoted commits relative to origin/${PROD_BRANCH}"
    if [[ -n "${prs}" ]]; then
      info "open promotion PR is visible but no unpromoted commits remain"
      printf '%s\n' "${prs}"
    else
      info "no open ${DEV_BRANCH} -> ${PROD_BRANCH} promotion PR is required because no unpromoted commits remain"
    fi
  fi
}

run_self_test() {
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/main-promotion-helper-test.XXXXXX")"
  trap 'rm -rf "${tmp}"' RETURN

  # Positive case: main is behind only by an equivalent patch that dev already
  # carries independently, so a no-commit merge must leave no worktree diff.
  git init -q "${tmp}/clean"
  if (
    cd "${tmp}/clean" || exit 1
    git config user.email test@example.invalid
    git config user.name 'Test User'
    printf 'base\n' > file.txt
    git add file.txt
    git commit -q -m base
    git branch main
    git checkout -q -b dev
    printf 'shared\n' > shared.txt
    git add shared.txt
    git commit -q -m dev-shared
    git checkout -q main
    printf 'shared\n' > shared.txt
    git add shared.txt
    git commit -q -m main-shared
    git checkout -q dev
    git merge --no-commit --no-ff main >/dev/null 2>/dev/null
    git diff --quiet HEAD
    git merge --abort >/dev/null
  ); then
    pass "self-test clean no-commit rehearsal leaves no diff"
  else
    fail "self-test clean no-commit rehearsal unexpectedly produced a diff"
    return 1
  fi

  # Negative case: main carries a real additional file, so the same diff check
  # must detect that a no-commit merge would change the worktree.
  git init -q "${tmp}/dirty"
  if (
    cd "${tmp}/dirty" || exit 1
    git config user.email test@example.invalid
    git config user.name 'Test User'
    printf 'base\n' > file.txt
    git add file.txt
    git commit -q -m base
    git branch main
    git checkout -q -b dev
    printf 'dev\n' >> file.txt
    git commit -am dev -q
    git checkout -q main
    printf 'main\n' > other.txt
    git add other.txt
    git commit -q -m main
    git checkout -q dev
    git merge --no-commit --no-ff main >/dev/null 2>/dev/null
    git diff --quiet HEAD
  ); then
    fail "self-test dirty no-commit rehearsal failed to detect a diff"
    return 1
  else
    pass "self-test dirty no-commit rehearsal detects a diff"
  fi

  before_failures="${failures}"
  check_promotion_pr_decision 0 "" >"${tmp}/decision_complete.out" 2>&1
  if [[ "${failures}" -eq "${before_failures}" ]]; then
    pass "self-test completed promotion does not require stale PR"
  else
    fail "self-test completed promotion unexpectedly required a PR"
    return 1
  fi

  before_failures="${failures}"
  check_promotion_pr_decision 2 "" >"${tmp}/decision_unpromoted_no_pr.out" 2>&1
  added_failures=$((failures - before_failures))
  failures="${before_failures}"
  if [[ "${added_failures}" -eq 2 ]]; then
    pass "self-test unpromoted commits without PR fail"
  else
    fail "self-test unpromoted commits without PR did not add two failures"
    return 1
  fi

  before_failures="${failures}"
  check_promotion_pr_decision 2 "#123 Promote https://example.test/pr/123" >"${tmp}/decision_unpromoted_with_pr.out" 2>&1
  added_failures=$((failures - before_failures))
  failures="${before_failures}"
  if [[ "${added_failures}" -eq 1 ]]; then
    pass "self-test unpromoted commits with PR still fail"
  else
    fail "self-test unpromoted commits with PR did not add one failure"
    return 1
  fi
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--self-test" ]]; then
  run_self_test
  exit $?
fi
if [[ $# -gt 0 ]]; then
  usage >&2
  exit 2
fi

need_cmd git || exit 1
need_cmd gh || exit 1

cd "${ROOT_DIR}" || exit 1

git fetch origin "${DEV_BRANCH}" "${PROD_BRANCH}" --quiet || fail "cannot fetch origin ${DEV_BRANCH}/${PROD_BRANCH}"

dev_ref="$(git rev-parse "origin/${DEV_BRANCH}")" || exit 1
prod_ref="$(git rev-parse "origin/${PROD_BRANCH}")" || exit 1
info "origin/${DEV_BRANCH}=${dev_ref}"
info "origin/${PROD_BRANCH}=${prod_ref}"

owner="${MAIN_REPO%%/*}"
promotion_head="${owner}:${DEV_BRANCH}"
prs="$(gh pr list --repo "${MAIN_REPO}" --state open --base "${PROD_BRANCH}" --head "${promotion_head}" --json number,title,url --jq '.[] | "#" + (.number|tostring) + " " + .title + " " + .url' 2>/dev/null || true)"

compare_json="$(mktemp "${TMPDIR:-/tmp}/main-promotion-compare.XXXXXX")"
ahead_by=""
behind_by=""
if gh api "repos/${MAIN_REPO}/compare/${PROD_BRANCH}...${DEV_BRANCH}" >"${compare_json}"; then
  python3 - "${compare_json}" <<'PY'
import json, sys
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text())
print(f"INFO {p.get('html_url')}")
print(f"INFO status={p.get('status')} ahead_by={p.get('ahead_by')} behind_by={p.get('behind_by')}")
PY
  ahead_by="$(python3 - "${compare_json}" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text()).get('ahead_by', 0))
PY
)"
  behind_by="$(python3 - "${compare_json}" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text()).get('behind_by', 0))
PY
)"
else
  fail "cannot compare ${PROD_BRANCH}...${DEV_BRANCH}"
fi
rm -f "${compare_json}"

check_promotion_pr_decision "${ahead_by}" "${prs}"

behind_count="$(git rev-list --count "origin/${DEV_BRANCH}..origin/${PROD_BRANCH}")"
if [[ "${behind_count}" -gt 0 ]]; then
  fail "origin/${DEV_BRANCH} is behind origin/${PROD_BRANCH} by ${behind_count} commits" || true
  git log --oneline --decorate "origin/${DEV_BRANCH}..origin/${PROD_BRANCH}"
else
  pass "origin/${DEV_BRANCH} is not behind origin/${PROD_BRANCH}"
fi

rehearsal_root="$(mktemp -d "${TMPDIR:-/tmp}/main-promotion-rehearsal.XXXXXX")"
rehearsal_wt="${rehearsal_root}/wt"
cleanup() {
  if [[ -d "${rehearsal_wt}/.git" ]]; then
    git -C "${ROOT_DIR}" worktree remove --force "${rehearsal_wt}" >/dev/null 2>&1 || true
  fi
  rm -rf "${rehearsal_root}"
}
trap cleanup EXIT

git worktree add --detach "${rehearsal_wt}" "origin/${DEV_BRANCH}" --quiet || fail "cannot create rehearsal worktree"
set +e
git -C "${rehearsal_wt}" merge --no-commit --no-ff "origin/${PROD_BRANCH}" >"${rehearsal_root}/merge.out" 2>"${rehearsal_root}/merge.err"
merge_rc=$?
set -e
cat "${rehearsal_root}/merge.out"
cat "${rehearsal_root}/merge.err" >&2
if [[ "${merge_rc}" -ne 0 ]]; then
  fail "non-committal merge rehearsal has conflicts" || true
  git -C "${rehearsal_wt}" diff --name-only --diff-filter=U || true
else
  pass "non-committal merge rehearsal completed without conflicts"
fi
if [[ "${merge_rc}" -eq 0 ]] && git -C "${rehearsal_wt}" diff --quiet HEAD; then
  pass "non-committal merge rehearsal completed with no worktree diff"
else
  fail "non-committal merge rehearsal completed but produced a worktree diff" || true
  git -C "${rehearsal_wt}" diff --stat HEAD
fi

git -C "${rehearsal_wt}" merge --abort >/dev/null 2>&1 || true
info "No PR, push, or merge was created."
info "failures=${failures}"
if [[ "${failures}" -gt 0 ]]; then
  exit 1
fi
