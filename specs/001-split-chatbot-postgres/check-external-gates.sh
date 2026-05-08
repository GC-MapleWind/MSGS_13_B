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
has_read_packages_scope=0
workflow_files_present=0
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/split-chatbot-gates.XXXXXX")"
trap 'rm -rf "${TMP_DIR}"' EXIT

CHATBOT_WORKFLOW_EVIDENCE_FIELDS=(
  "- Applied from MSGS_13_B dev:"
  "- Patch SHA-256:"
  "- Chatbot workflow commit:"
  "- CI run URL/conclusion:"
  "- Deploy/build run URL/conclusion:"
  "- GHCR image tags/digest:"
  "- Remote workflow files API result:"
  "- Remaining follow-ups:"
)

CUTOVER_EVIDENCE_FIELDS=(
  "- Environment:"
  "- Window:"
  "- Main image:"
  "- Chatbot image:"
  "- SQLite backup SHA-256 files:"
  "- Row-count result:"
  "- Backend health/core APIs:"
  "- Chatbot health:"
  "- Kakao/Google Sheets smoke:"
  "- Downtime:"
  "- Webhook route + 7-day compatibility expiry:"
  "- SLA p95/p99:"
  "- Chatbot-only redeploy elapsed/backend restart evidence:"
  "- 24h/7d monitoring links:"
  "- Rollback used?:"
  "- Remaining follow-ups:"
)

section() { printf '\n== %s ==\n' "$1"; }
pass() { printf 'PASS %s\n' "$1"; }
warn() { printf 'WARN %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }
info() { printf 'INFO %s\n' "$1"; }

gh_api_retry_to_file() {
  api_path="$1"
  out_file="$2"
  err_file="$3"
  attempts="${4:-3}"

  attempt=1
  while [[ "${attempt}" -le "${attempts}" ]]; do
    if gh api "${api_path}" >"${out_file}" 2>"${err_file}"; then
      if [[ "${attempt}" -gt 1 ]]; then
        info "gh api ${api_path} succeeded on retry ${attempt}"
      fi
      return 0
    fi

    err_text="$(tr '
' ' ' <"${err_file}" 2>/dev/null || true)"
    if ! printf '%s' "${err_text}" | grep -Eiq '(i/o timeout|timed out|timeout|connection reset|TLS handshake timeout|502|503|504)'; then
      return 1
    fi
    if [[ "${attempt}" -lt "${attempts}" ]]; then
      warn "gh api ${api_path} transient failure on attempt ${attempt}/${attempts}: ${err_text}"
      sleep "${attempt}"
    fi
    attempt=$((attempt + 1))
  done
  return 1
}

issue_view_line() {
  repo="$1"
  number="$2"
  err_file="$3"

  if line="$(gh issue view "${number}" --repo "${repo}" --json state,title,url --jq '.state + "\t" + .title + "\t" + .url' 2>"${err_file}.graphql")" && [[ -n "${line}" ]]; then
    printf '%s\n' "${line}"
    return 0
  fi

  info "gh issue view failed for ${repo}#${number}; trying REST fallback" >&2
  if line="$(gh api "repos/${repo}/issues/${number}" --jq '(.state | ascii_upcase) + "\t" + .title + "\t" + .html_url' 2>"${err_file}.rest")" && [[ -n "${line}" ]]; then
    printf '%s\n' "${line}"
    return 0
  fi

  {
    printf 'graphql: '
    tr '\n' ' ' <"${err_file}.graphql" 2>/dev/null || true
    printf ' rest: '
    tr '\n' ' ' <"${err_file}.rest" 2>/dev/null || true
  } >"${err_file}"
  return 1
}

issue_has_complete_summary() {
  repo="$1"
  number="$2"
  marker="$3"
  err_file="$4"
  shift 4

  {
    printf '<<<OMX_ISSUE_BLOCK>>>\n'
    gh api "repos/${repo}/issues/${number}" --jq '.body // ""'
    gh api "repos/${repo}/issues/${number}/comments?per_page=100" --paginate --jq '"<<<OMX_ISSUE_BLOCK>>>\n" + (.body // "")'
  } >"${err_file}.body" 2>"${err_file}.api" || {
    tr '\n' ' ' <"${err_file}.api" >"${err_file}"
    return 1
  }

  fields_join="$(printf '%s\034' "$@")"
  fields_join="${fields_join%$'\034'}"
  if awk -v marker="${marker}" -v fields_join="${fields_join}" '
    BEGIN {
      RS = "<<<OMX_ISSUE_BLOCK>>>"
      FS = "\n"
      fields_count = split(fields_join, fields, "\034")
    }
    {
      has_marker = 0
      for (i = 1; i <= NF; i++) {
        if ($i == marker) {
          has_marker = 1
        }
      }
      if (has_marker) {
        has_fields = 1
        for (i = 1; i <= fields_count; i++) {
          field_has_value = 0
          for (line = 1; line <= NF; line++) {
            field_pos = index($line, fields[i])
            if (field_pos == 1) {
              field_value = substr($line, length(fields[i]) + 1)
              gsub(/^[[:space:]]+|[[:space:]]+$/, "", field_value)
              normalized_value = tolower(field_value)
              gsub(/[`*_[:space:]]+/, "", normalized_value)
              gsub(/[[:punct:]]+$/, "", normalized_value)
              if (field_value != "" && normalized_value !~ /^(tbd|todo|pending|none|null|na|n\/a|placeholder|replace|replace-me|replaceme|changeme|unknown|tobedetermined|미정|대기|없음)$/) {
                field_has_value = 1
              }
            }
          }
          if (!field_has_value) {
            has_fields = 0
          }
        }
        if (has_fields) {
          found = 1
        }
      }
    }
    END { exit found ? 0 : 1 }
  ' "${err_file}.body"; then
    return 0
  fi

  printf 'missing complete summary block for marker: %s' "${marker}" >"${err_file}"
  return 1
}

ghcr_tag_visible() {
  pattern="$1"
  printf '%s\n' "${versions}" | awk -F'tags=' 'NF > 1 {print $2}' | tr ',' '\n' | grep -Eq "${pattern}"
}

run_self_test() {
  section "GHCR tag parser self-test"
  versions='version=1 updated=now tags=latest,0123456789abcdef0123456789abcdef01234567,main,main-0123456'
  if ghcr_tag_visible '^latest$'; then pass "matches first-position latest tag"; else fail "misses first-position latest tag"; fi
  if ghcr_tag_visible '^[0-9a-f]{40}$'; then pass "matches full-sha tag"; else fail "misses full-sha tag"; fi
  if ghcr_tag_visible '^main$'; then pass "matches main tag"; else fail "misses main tag"; fi
  if ghcr_tag_visible '^main-[0-9a-f]{7,40}$'; then pass "matches main-* tag"; else fail "misses main-* tag"; fi

  versions='version=2 updated=now tags=latest,main'
  if ghcr_tag_visible '^[0-9a-f]{40}$'; then fail "unexpectedly matches missing full-sha tag"; else pass "rejects missing full-sha tag"; fi

  versions='version=3 updated=now tags=not-latest,mainline,main-123456'
  if ghcr_tag_visible '^latest$'; then fail "unexpectedly matches non-exact latest tag"; else pass "rejects non-exact latest tag"; fi
  if ghcr_tag_visible '^main$'; then fail "unexpectedly matches non-exact main tag"; else pass "rejects non-exact main tag"; fi
  if ghcr_tag_visible '^main-[0-9a-f]{7,40}$'; then fail "unexpectedly matches too-short main-* tag"; else pass "rejects too-short main-* tag"; fi

  section "Issue reader fallback self-test"
  gh() {
    if [[ "$1" == "issue" && "$2" == "view" ]]; then
      printf 'simulated GraphQL outage\n' >&2
      return 1
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/7" ]]; then
      printf 'CLOSED\tFallback title\thttps://example.test/issues/7\n'
      return 0
    fi
    printf 'unexpected gh call: %s\n' "$*" >&2
    return 127
  }
  issue_line="$(issue_view_line "example/repo" "7" "${TMP_DIR}/issue_fallback_selftest.err" 2>"${TMP_DIR}/issue_fallback_selftest.info" || true)"
  if [[ "${issue_line}" == $'CLOSED\tFallback title\thttps://example.test/issues/7' ]]; then
    pass "REST fallback returns a clean issue line"
  else
    fail "REST fallback returned unexpected issue line: ${issue_line}"
  fi
  unset -f gh


  section "API retry self-test"
  retry_count_file="${TMP_DIR}/api_retry_count"
  printf '0' >"${retry_count_file}"
  gh() {
    if [[ "$1" == "api" && "$2" == "repos/example/repo/actions/runs?branch=main&per_page=10" ]]; then
      count="$(cat "${retry_count_file}")"
      count=$((count + 1))
      printf '%s' "${count}" >"${retry_count_file}"
      if [[ "${count}" -eq 1 ]]; then
        printf 'Get "https://api.github.com/repos/example/repo/actions/runs": dial tcp 127.0.0.1:443: i/o timeout
' >&2
        return 1
      fi
      printf '{"workflow_runs":[]}
'
      return 0
    fi
    printf 'unexpected gh call: %s
' "$*" >&2
    return 127
  }
  sleep() { :; }
  warnings_before_retry_selftest="${warnings}"
  if gh_api_retry_to_file "repos/example/repo/actions/runs?branch=main&per_page=10" "${TMP_DIR}/api_retry.json" "${TMP_DIR}/api_retry.err" 2 >/dev/null; then
    pass "retries transient gh api timeout"
  else
    fail "did not retry transient gh api timeout"
  fi
  warnings="${warnings_before_retry_selftest}"
  unset -f gh sleep


  section "Issue evidence marker self-test"
  gh() {
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/8" ]]; then
      printf 'Issue body without marker\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/8/comments?per_page=100" ]]; then
      printf 'Chatbot workflow evidence summary:\n- Applied from MSGS_13_B dev: 0123456789abcdef0123456789abcdef01234567\n- Patch SHA-256: ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4\n- Applied from MSGS_13_B dev: 0123456789abcdef0123456789abcdef01234567\n- Patch SHA-256: ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4\n- Chatbot workflow commit: abcdef1234567890\n- CI run URL/conclusion: https://example.test/ci success\n- Deploy/build run URL/conclusion: https://example.test/deploy success\n- GHCR image tags/digest: latest sha main main-abc digest sha256:abc\n- Remote workflow files API result: ci.yml deploy.yml present\n- Remaining follow-ups: monitor deploy evidence handoff\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/9" ]]; then
      printf 'Issue body without marker\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/9/comments?per_page=100" ]]; then
      printf 'Advisory note mentions `Cutover evidence summary:` but is not the evidence heading\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/10" ]]; then
      printf 'Chatbot workflow evidence summary:\n- Applied from MSGS_13_B dev:\n- Patch SHA-256:\n- Chatbot workflow commit:\n- CI run URL/conclusion:\n- Deploy/build run URL/conclusion:\n- GHCR image tags/digest:\n- Remote workflow files API result:\n- Remaining follow-ups:\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/10/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/11" ]]; then
      printf 'Chatbot workflow evidence summary:\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/11/comments?per_page=100" ]]; then
      printf '- Applied from MSGS_13_B dev: 0123456789abcdef0123456789abcdef01234567\n- Patch SHA-256: ceb61e156d10e4cde98a6bc9d2cbf903ae2205b1cc790f861881a1f1fe21cac4\n- Chatbot workflow commit: abcdef1234567890\n- CI run URL/conclusion: https://example.test/ci success\n- Deploy/build run URL/conclusion: https://example.test/deploy success\n- GHCR image tags/digest: latest sha main main-abc digest sha256:abc\n- Remote workflow files API result: ci.yml deploy.yml present\n- Remaining follow-ups: monitor deploy evidence handoff\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/12" ]]; then
      printf 'Chatbot workflow evidence summary:\n- Applied from MSGS_13_B dev: TBD\n- Patch SHA-256: pending\n- Chatbot workflow commit: TBD\n- CI run URL/conclusion: TBD\n- Deploy/build run URL/conclusion: pending\n- GHCR image tags/digest: replace-me\n- Remote workflow files API result: unknown\n- Remaining follow-ups: none\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/12/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/13" ]]; then
      printf 'Cutover evidence summary:\n- SQLite backup SHA-256 files: 미정\n- Row-count result: 대기\n- 24h/7d monitoring links: 없음\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/13/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/14" ]]; then
      printf 'Cutover evidence summary:
- Environment: staging
- Window: 2026-05-09 01:00-01:25 KST
- Main image: ghcr.io/gc-maplewind/msgs_13_b-backend:sha256:abc
- Chatbot image: ghcr.io/gc-maplewind/maplewind-chatbot:sha256:def
- SQLite backup SHA-256 files: maplewind.db.bak sha256:abc chatbot.db.bak sha256:def
- Row-count result: all counts match
- Backend health/core APIs: /health /v1/characters /v1/settlements success
- Chatbot health: /health success
- Kakao/Google Sheets smoke: row 123 recorded
- Downtime: 12 minutes
- Webhook route + 7-day compatibility expiry: chatbot.maplewind.com active; old route forwards until 2026-05-16
- SLA p95/p99: p95 1.2s p99 2.1s
- Chatbot-only redeploy elapsed/backend restart evidence: 42s; backend container id unchanged
- 24h/7d monitoring links: https://example.test/monitoring
- Rollback used?: no
- Remaining follow-ups: remove compatibility route after expiry
'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/14/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/15" ]]; then
      printf 'Chatbot workflow evidence summary:\n- Applied from MSGS_13_B dev: TBD.\n- Patch SHA-256: To be determined\n- Chatbot workflow commit: TBD.\n- CI run URL/conclusion: To be determined\n- Deploy/build run URL/conclusion: replace me\n- GHCR image tags/digest: placeholder.\n- Remote workflow files API result: unknown.\n- Remaining follow-ups: unknown.\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/15/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    printf 'unexpected gh call: %s\n' "$*" >&2
    return 127
  }
  if issue_has_complete_summary "example/repo" "8" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_positive_selftest.err" "${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}"; then
    pass "detects complete workflow evidence summary with all required fields"
  else
    fail "misses complete workflow evidence summary with all required fields"
  fi
  if issue_has_complete_summary "example/repo" "9" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_advisory_selftest.err" "- Row-count result:" "- 24h/7d monitoring links:"; then
    fail "unexpectedly detects advisory marker mention as evidence"
  else
    pass "rejects advisory marker mention without standalone evidence heading"
  fi
  if issue_has_complete_summary "example/repo" "10" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_empty_fields_selftest.err" "${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}"; then
    fail "unexpectedly accepts empty required evidence fields"
  else
    pass "rejects empty required evidence fields"
  fi
  if issue_has_complete_summary "example/repo" "11" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_split_selftest.err" "${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}"; then
    fail "unexpectedly accepts marker and fields split across issue blocks"
  else
    pass "rejects marker and fields split across issue blocks"
  fi
  if issue_has_complete_summary "example/repo" "12" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_placeholder_selftest.err" "${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}"; then
    fail "unexpectedly accepts placeholder evidence field values"
  else
    pass "rejects placeholder evidence field values"
  fi
  if issue_has_complete_summary "example/repo" "13" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_korean_placeholder_selftest.err" "${CUTOVER_EVIDENCE_FIELDS[@]}"; then
    fail "unexpectedly accepts Korean placeholder evidence field values"
  else
    pass "rejects Korean placeholder evidence field values"
  fi
  if issue_has_complete_summary "example/repo" "14" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_cutover_positive_selftest.err" "${CUTOVER_EVIDENCE_FIELDS[@]}"; then
    pass "detects complete cutover evidence summary with all required fields"
  else
    fail "misses complete cutover evidence summary with all required fields"
  fi
  if issue_has_complete_summary "example/repo" "15" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_placeholder_variants_selftest.err" "${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}"; then
    fail "unexpectedly accepts punctuated or spaced placeholder evidence field values"
  else
    pass "rejects punctuated and spaced placeholder evidence field values"
  fi
  unset -f gh

  section "Self-test summary"
  info "failures=${failures} warnings=${warnings}"
  [[ "${failures}" -eq 0 ]]
}

if [[ "${1:-}" == "--self-test" ]]; then
  run_self_test
  exit $?
fi

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
  if printf '%s' "${scopes}" | grep -Eq '(^|, *)read:packages(,|$)'; then
    has_read_packages_scope=1
    pass "credential includes read:packages scope"
  else
    warn "credential lacks read:packages scope; private GHCR package visibility may be inconclusive"
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
  if gh api "repos/${CHATBOT_REPO}/contents/.github/workflows/deploy.yml?ref=${CHATBOT_BRANCH}" --jq '.content' 2>"${TMP_DIR}/chatbot_deploy_workflow.err" | base64 --decode >"${TMP_DIR}/chatbot_deploy.yml"; then
    if grep -q 'type=raw,value=latest' "${TMP_DIR}/chatbot_deploy.yml"; then pass "deploy.yml preserves GHCR latest tag metadata"; else fail "deploy.yml missing type=raw,value=latest metadata"; fi
    if grep -q 'type=sha,format=long,prefix=' "${TMP_DIR}/chatbot_deploy.yml"; then pass "deploy.yml preserves full-sha GHCR tag metadata"; else fail "deploy.yml missing type=sha,format=long,prefix= metadata"; fi
    if grep -q 'type=sha,prefix=main-' "${TMP_DIR}/chatbot_deploy.yml"; then pass "deploy.yml preserves main-* GHCR tag metadata"; else fail "deploy.yml missing type=sha,prefix=main- metadata"; fi
  else
    fail "deploy.yml content is not readable on ${CHATBOT_BRANCH}: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_deploy_workflow.err")"
  fi
else
  fail "${CHATBOT_REPO} .github/workflows is not readable on ${CHATBOT_BRANCH}: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_workflow_gate.err")"
fi

if [[ "${workflow_files_present}" -eq 0 && "${has_workflow_scope}" -eq 0 ]]; then
  fail "workflow files are absent and current credential cannot apply them"
fi

section "Chatbot workflow files via direct clone"
chatbot_tree_dir="${TMP_DIR}/chatbot-remote-tree"
if gh repo clone "${CHATBOT_REPO}" "${chatbot_tree_dir}" -- --depth 1 --branch "${CHATBOT_BRANCH}" >"${TMP_DIR}/chatbot_clone.out" 2>"${TMP_DIR}/chatbot_clone.err"; then
  pass "direct shallow clone of ${CHATBOT_REPO}@${CHATBOT_BRANCH} succeeded"
  if [[ -d "${chatbot_tree_dir}/.github/workflows" ]]; then
    clone_paths="$(cd "${chatbot_tree_dir}" && find .github/workflows -maxdepth 1 -type f | sed 's#^./##' | sort)"
    printf '%s
' "${clone_paths}"
    if printf '%s
' "${clone_paths}" | grep -qx '.github/workflows/ci.yml' && printf '%s
' "${clone_paths}" | grep -qx '.github/workflows/deploy.yml'; then
      pass "direct clone contains required chatbot workflow files"
    else
      fail "direct clone is missing one or more required chatbot workflow files"
    fi
  else
    fail "direct shallow clone confirms ${CHATBOT_REPO}@${CHATBOT_BRANCH} has no .github/workflows directory"
  fi
else
  warn "direct shallow clone of ${CHATBOT_REPO}@${CHATBOT_BRANCH} failed; API workflow check remains authoritative for this run: $(tr '
' ' ' <"${TMP_DIR}/chatbot_clone.err")"
fi

section "Chatbot Actions runs"
runs_json="${TMP_DIR}/chatbot_runs_gate.json"
actions_api="repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10"
if gh_api_retry_to_file "${actions_api}" "${runs_json}" "${TMP_DIR}/chatbot_runs_gate.err" 3; then
  run_lines="$(python3 - "${runs_json}" <<'PY_ACTION_LINES'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
for run in payload.get("workflow_runs", []):
    print(f"{run.get('name')} status={run.get('status')} conclusion={run.get('conclusion')} head={run.get('head_sha')} url={run.get('html_url')}")
PY_ACTION_LINES
)"
  success_count="$(python3 - "${runs_json}" <<'PY_ACTION_COUNT'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
print(sum(1 for run in payload.get("workflow_runs", []) if run.get("conclusion") == "success"))
PY_ACTION_COUNT
)"
  if [[ -z "${run_lines}" ]]; then
    fail "no chatbot Actions runs visible on ${CHATBOT_BRANCH}"
  else
    printf '%s
' "${run_lines}"
    if [[ "${success_count}" -gt 0 ]]; then pass "at least one successful chatbot Actions run is visible"; else fail "no successful chatbot Actions run visible"; fi
  fi
else
  fail "cannot list chatbot Actions runs via API after retries: $(tr '
' ' ' <"${TMP_DIR}/chatbot_runs_gate.err")"
fi

section "Chatbot GHCR package"
chatbot_owner="${CHATBOT_REPO%%/*}"
chatbot_package="${CHATBOT_REPO##*/}"
if gh api "/orgs/${chatbot_owner}/packages/container/${chatbot_package}" >"${TMP_DIR}/chatbot_ghcr_package.json" 2>"${TMP_DIR}/chatbot_ghcr_package.err"; then
  pass "GHCR package ${chatbot_owner}/${chatbot_package} is visible"
  versions="$(gh api "/orgs/${chatbot_owner}/packages/container/${chatbot_package}/versions?per_page=10" --jq '.[] | "version=\(.id) updated=\(.updated_at) tags=\(.metadata.container.tags | join(","))"' 2>"${TMP_DIR}/chatbot_ghcr_versions.err" || true)"
  if [[ -n "${versions}" ]]; then
    printf '%s\n' "${versions}"
    if ghcr_tag_visible '^latest$'; then pass "GHCR latest tag is visible"; else fail "GHCR latest tag not visible in recent versions"; fi
    if ghcr_tag_visible '^[0-9a-f]{40}$'; then pass "GHCR full-sha tag is visible"; else fail "GHCR full-sha tag not visible in recent versions"; fi
    if ghcr_tag_visible '^main$'; then pass "GHCR main tag is visible"; else fail "GHCR main tag not visible in recent versions"; fi
    if ghcr_tag_visible '^main-[0-9a-f]{7,40}$'; then pass "GHCR main-* tag is visible"; else fail "GHCR main-* tag not visible in recent versions"; fi
  else
    fail "GHCR package visible but versions/tags not readable: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_ghcr_versions.err")"
  fi
else
  if [[ "${has_read_packages_scope}" -eq 0 ]]; then
    fail "GHCR package ${chatbot_owner}/${chatbot_package} is not visible/readable with current credential, and credential lacks read:packages scope: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_ghcr_package.err")"
  else
    fail "GHCR package ${chatbot_owner}/${chatbot_package} is not visible/readable despite read:packages scope: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_ghcr_package.err")"
  fi
fi

section "Blocker issues"
for item in "${CHATBOT_REPO} 1 workflow" "${MAIN_REPO} 55 cutover"; do
  set -- ${item}
  repo="$1"; number="$2"; label="$3"
  issue_line="$(issue_view_line "${repo}" "${number}" "${TMP_DIR}/issue_gate_${number}.err" || true)"
  if [[ -z "${issue_line}" ]]; then
    fail "cannot read ${repo}#${number}: $(tr '\n' ' ' <"${TMP_DIR}/issue_gate_${number}.err")"
    continue
  fi
  IFS=$'\t' read -r state title url <<<"${issue_line}"
  info "${repo}#${number} ${state} ${title} ${url}"
  if [[ "${state}" == "CLOSED" ]]; then pass "${label} blocker issue is closed"; else fail "${label} blocker issue remains ${state}"; fi
  if [[ "${state}" == "CLOSED" ]]; then
    marker=""
    if [[ "${label}" == "workflow" ]]; then
      marker="Chatbot workflow evidence summary:"
      fields=("${CHATBOT_WORKFLOW_EVIDENCE_FIELDS[@]}")
    elif [[ "${label}" == "cutover" ]]; then
      marker="Cutover evidence summary:"
      fields=("${CUTOVER_EVIDENCE_FIELDS[@]}")
    fi
    if [[ -n "${marker}" ]]; then
      if issue_has_complete_summary "${repo}" "${number}" "${marker}" "${TMP_DIR}/issue_summary_${number}.err" "${fields[@]}"; then
        pass "${label} evidence summary marker and required fields are present in one issue timeline block"
      else
        fail "${label} evidence summary block is incomplete or missing from issue timeline: $(tr '\n' ' ' <"${TMP_DIR}/issue_summary_${number}.err")"
      fi
    fi
  fi
done

section "Summary"
info "failures=${failures} warnings=${warnings}"
if [[ "${failures}" -eq 0 ]]; then
  warn "No observable failure found. Still verify operator-handoff-index.md evidence before marking complete."
  exit 0
fi
exit 1
