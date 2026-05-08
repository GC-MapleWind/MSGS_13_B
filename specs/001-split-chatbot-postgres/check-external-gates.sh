#!/usr/bin/env bash
# Check observable external gates for split-chatbot-postgres.
# This script is diagnostic only: a PASS here is not sufficient completion proof.
# Completion still requires the evidence requested by operator-handoff-index.md.

set -u -o pipefail

MAIN_REPO="${MAIN_REPO:-GC-MapleWind/MSGS_13_B}"
CHATBOT_REPO="${CHATBOT_REPO:-GC-MapleWind/maplewind-chatbot}"
MAIN_BRANCH="${MAIN_BRANCH:-dev}"
CHATBOT_BRANCH="${CHATBOT_BRANCH:-main}"

failures=0
warnings=0
has_workflow_scope=0
workflow_files_present=0

section() { printf '\n== %s ==\n' "$1"; }
pass() { printf 'PASS %s\n' "$1"; }
warn() { printf 'WARN %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }
info() { printf 'INFO %s\n' "$1"; }

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "missing required command: $1"
    return 1
  fi
}

section "Prerequisites"
need_cmd git || true
need_cmd gh || true
if command -v jq >/dev/null 2>&1; then
  info "jq available"
else
  info "jq not installed; using gh --jq filters where needed"
fi

section "Remote refs"
main_ref="$(git ls-remote "https://github.com/${MAIN_REPO}.git" "refs/heads/${MAIN_BRANCH}" 2>/dev/null | awk '{print $1}')"
chatbot_ref="$(git ls-remote "https://github.com/${CHATBOT_REPO}.git" "refs/heads/${CHATBOT_BRANCH}" 2>/dev/null | awk '{print $1}')"
if [[ -n "${main_ref}" ]]; then pass "${MAIN_REPO} ${MAIN_BRANCH} ${main_ref}"; else fail "cannot read ${MAIN_REPO} ${MAIN_BRANCH}"; fi
if [[ -n "${chatbot_ref}" ]]; then pass "${CHATBOT_REPO} ${CHATBOT_BRANCH} ${chatbot_ref}"; else fail "cannot read ${CHATBOT_REPO} ${CHATBOT_BRANCH}"; fi

section "GitHub credential scope"
headers="$(gh api -i user 2>/dev/null || true)"
if [[ -z "${headers}" ]]; then
  fail "gh api -i user failed; cannot inspect credential scope"
else
  scopes="$(printf '%s\n' "${headers}" | awk 'BEGIN{IGNORECASE=1}/^X-Oauth-Scopes:/{sub(/^[^:]+:[[:space:]]*/, ""); print}')"
  info "X-Oauth-Scopes: ${scopes:-<none>}"
  if printf '%s' "${scopes}" | grep -Eq '(^|, *)workflow(,|$)'; then
    has_workflow_scope=1
    pass "credential includes workflow scope"
  else
    warn "credential lacks workflow scope; workflow-file application is expected to be blocked if workflows are still absent"
  fi
fi

section "Chatbot workflow files on remote"
if gh api "repos/${CHATBOT_REPO}/contents/.github/workflows?ref=${CHATBOT_BRANCH}" >/tmp/chatbot_workflow_gate.json 2>/tmp/chatbot_workflow_gate.err; then
  paths="$(gh api "repos/${CHATBOT_REPO}/contents/.github/workflows?ref=${CHATBOT_BRANCH}" --jq '.[].path' 2>/tmp/chatbot_workflow_gate.err || true)"
  printf '%s\n' "${paths}"
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/ci.yml'; then pass "ci.yml exists"; else fail "ci.yml missing"; fi
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/deploy.yml'; then pass "deploy.yml exists"; else fail "deploy.yml missing"; fi
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/ci.yml' && printf '%s\n' "${paths}" | grep -qx '.github/workflows/deploy.yml'; then
    workflow_files_present=1
  fi
else
  fail "${CHATBOT_REPO} .github/workflows is not readable on ${CHATBOT_BRANCH}: $(tr '\n' ' ' </tmp/chatbot_workflow_gate.err)"
fi

if [[ "${workflow_files_present}" -eq 0 && "${has_workflow_scope}" -eq 0 ]]; then
  fail "workflow files are absent and current credential cannot apply them"
fi

section "Chatbot Actions runs"
run_lines="$(gh run list --repo "${CHATBOT_REPO}" --limit 10 --json name,status,conclusion,headSha,url --jq '.[] | "\(.name) status=\(.status) conclusion=\(.conclusion) head=\(.headSha) url=\(.url)"' 2>/tmp/chatbot_runs_gate.err || true)"
success_count="$(gh run list --repo "${CHATBOT_REPO}" --limit 10 --json conclusion --jq '[.[] | select(.conclusion == "success")] | length' 2>/dev/null || printf '0')"
if [[ -z "${run_lines}" ]]; then
  warn "no chatbot Actions runs visible or gh run list failed: $(tr '\n' ' ' </tmp/chatbot_runs_gate.err)"
else
  printf '%s\n' "${run_lines}"
  if [[ "${success_count}" -gt 0 ]]; then pass "at least one successful chatbot Actions run is visible"; else warn "no successful chatbot Actions run visible"; fi
fi

section "Blocker issues"
for item in "${CHATBOT_REPO} 1 workflow" "${MAIN_REPO} 55 cutover"; do
  set -- ${item}
  repo="$1"; number="$2"; label="$3"
  issue_line="$(gh issue view "${number}" --repo "${repo}" --json state,title,url --jq '.state + "\t" + .title + "\t" + .url' 2>/tmp/issue_gate.err || true)"
  if [[ -z "${issue_line}" ]]; then
    fail "cannot read ${repo}#${number}: $(tr '\n' ' ' </tmp/issue_gate.err)"
    continue
  fi
  IFS=$'\t' read -r state title url <<<"${issue_line}"
  info "${repo}#${number} ${state} ${title} ${url}"
  if [[ "${state}" == "CLOSED" ]]; then pass "${label} blocker issue is closed"; else warn "${label} blocker issue remains ${state}"; fi
done

section "Summary"
info "failures=${failures} warnings=${warnings}"
if [[ "${failures}" -eq 0 ]]; then
  warn "No observable failure found. Still verify operator-handoff-index.md evidence before marking complete."
  exit 0
fi
exit 1
