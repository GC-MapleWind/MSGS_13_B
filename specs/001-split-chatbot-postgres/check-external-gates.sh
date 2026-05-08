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
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/split-chatbot-gates.XXXXXX")"
trap 'rm -rf "${TMP_DIR}"' EXIT

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
if gh api "repos/${CHATBOT_REPO}/contents/.github/workflows?ref=${CHATBOT_BRANCH}" >"${TMP_DIR}/chatbot_workflow_gate.json" 2>"${TMP_DIR}/chatbot_workflow_gate.err"; then
  paths="$(gh api "repos/${CHATBOT_REPO}/contents/.github/workflows?ref=${CHATBOT_BRANCH}" --jq '.[].path' 2>"${TMP_DIR}/chatbot_workflow_gate.err" || true)"
  printf '%s\n' "${paths}"
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/ci.yml'; then pass "ci.yml exists"; else fail "ci.yml missing"; fi
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/deploy.yml'; then pass "deploy.yml exists"; else fail "deploy.yml missing"; fi
  if printf '%s\n' "${paths}" | grep -qx '.github/workflows/ci.yml' && printf '%s\n' "${paths}" | grep -qx '.github/workflows/deploy.yml'; then
    workflow_files_present=1
  fi
else
  fail "${CHATBOT_REPO} .github/workflows is not readable on ${CHATBOT_BRANCH}: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_workflow_gate.err")"
fi

if [[ "${workflow_files_present}" -eq 0 && "${has_workflow_scope}" -eq 0 ]]; then
  fail "workflow files are absent and current credential cannot apply them"
fi

section "Chatbot Actions runs"
runs_json="${TMP_DIR}/chatbot_runs_gate.json"
if gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" >"${runs_json}" 2>"${TMP_DIR}/chatbot_runs_gate.err"; then
  run_lines="$(gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" --jq '.workflow_runs[] | "\(.name) status=\(.status) conclusion=\(.conclusion) head=\(.head_sha) url=\(.html_url)"' 2>/dev/null || true)"
  success_count="$(gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" --jq '[.workflow_runs[] | select(.conclusion == "success")] | length' 2>/dev/null || printf '0')"
  if [[ -z "${run_lines}" ]]; then
    warn "no chatbot Actions runs visible on ${CHATBOT_BRANCH}"
  else
    printf '%s\n' "${run_lines}"
    if [[ "${success_count}" -gt 0 ]]; then pass "at least one successful chatbot Actions run is visible"; else warn "no successful chatbot Actions run visible"; fi
  fi
else
  warn "cannot list chatbot Actions runs via API: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_runs_gate.err")"
fi

section "Chatbot GHCR package"
chatbot_owner="${CHATBOT_REPO%%/*}"
chatbot_package="${CHATBOT_REPO##*/}"
if gh api "/orgs/${chatbot_owner}/packages/container/${chatbot_package}" >"${TMP_DIR}/chatbot_ghcr_package.json" 2>"${TMP_DIR}/chatbot_ghcr_package.err"; then
  pass "GHCR package ${chatbot_owner}/${chatbot_package} is visible"
  versions="$(gh api "/orgs/${chatbot_owner}/packages/container/${chatbot_package}/versions?per_page=10" --jq '.[] | "version=\(.id) updated=\(.updated_at) tags=\(.metadata.container.tags | join(","))"' 2>"${TMP_DIR}/chatbot_ghcr_versions.err" || true)"
  if [[ -n "${versions}" ]]; then
    printf '%s\n' "${versions}"
    if printf '%s\n' "${versions}" | grep -Eq 'tags=.*(^|,)latest(,|$)'; then pass "GHCR latest tag is visible"; else warn "GHCR latest tag not visible in recent versions"; fi
    if printf '%s\n' "${versions}" | grep -Eq 'tags=.*(^|,)main(,|$)'; then pass "GHCR main tag is visible"; else warn "GHCR main tag not visible in recent versions"; fi
  else
    warn "GHCR package visible but versions/tags not readable: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_ghcr_versions.err")"
  fi
else
  fail "GHCR package ${chatbot_owner}/${chatbot_package} is not visible/readable: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_ghcr_package.err")"
fi

section "Blocker issues"
for item in "${CHATBOT_REPO} 1 workflow" "${MAIN_REPO} 55 cutover"; do
  set -- ${item}
  repo="$1"; number="$2"; label="$3"
  issue_line="$(gh issue view "${number}" --repo "${repo}" --json state,title,url --jq '.state + "\t" + .title + "\t" + .url' 2>"${TMP_DIR}/issue_gate.err" || true)"
  if [[ -z "${issue_line}" ]]; then
    fail "cannot read ${repo}#${number}: $(tr '\n' ' ' <"${TMP_DIR}/issue_gate.err")"
    continue
  fi
  IFS=$'\t' read -r state title url <<<"${issue_line}"
  info "${repo}#${number} ${state} ${title} ${url}"
  if [[ "${state}" == "CLOSED" ]]; then pass "${label} blocker issue is closed"; else fail "${label} blocker issue remains ${state}"; fi
done

section "Summary"
info "failures=${failures} warnings=${warnings}"
if [[ "${failures}" -eq 0 ]]; then
  warn "No observable failure found. Still verify operator-handoff-index.md evidence before marking complete."
  exit 0
fi
exit 1
