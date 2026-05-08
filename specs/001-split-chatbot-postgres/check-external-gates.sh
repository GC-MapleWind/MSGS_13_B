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

section() { printf '\n== %s ==\n' "$1"; }
pass() { printf 'PASS %s\n' "$1"; }
warn() { printf 'WARN %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL %s\n' "$1"; failures=$((failures + 1)); }
info() { printf 'INFO %s\n' "$1"; }

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
              if (field_value != "" && normalized_value !~ /^(tbd|todo|pending|none|null|na|n\/a|placeholder|replace|replace-me|changeme|unknown|미정|대기|없음)$/) {
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

  section "Issue evidence marker self-test"
  gh() {
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/8" ]]; then
      printf 'Issue body without marker\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/8/comments?per_page=100" ]]; then
      printf 'Chatbot workflow evidence summary:\n- CI run URL/conclusion: https://example.test/ci success\n- Deploy/build run URL/conclusion: https://example.test/deploy success\n- GHCR image tags/digest: latest sha main main-abc digest sha256:abc\n'
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
      printf 'Chatbot workflow evidence summary:\n- CI run URL/conclusion:\n- Deploy/build run URL/conclusion:\n- GHCR image tags/digest:\n'
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
      printf '- CI run URL/conclusion: https://example.test/ci success\n- Deploy/build run URL/conclusion: https://example.test/deploy success\n- GHCR image tags/digest: latest sha main main-abc digest sha256:abc\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/12" ]]; then
      printf 'Chatbot workflow evidence summary:\n- CI run URL/conclusion: TBD\n- Deploy/build run URL/conclusion: pending\n- GHCR image tags/digest: replace-me\n'
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
      printf 'Cutover evidence summary:\n- SQLite backup SHA-256 files: maplewind.db.bak sha256:abc chatbot.db.bak sha256:def\n- Row-count result: all counts match\n- Backend health/core APIs: /health /v1/characters /v1/settlements success\n- Chatbot health: /health success\n- 24h/7d monitoring links: https://example.test/monitoring\n'
      return 0
    fi
    if [[ "$1" == "api" && "$2" == "repos/example/repo/issues/14/comments?per_page=100" ]]; then
      printf 'No comments\n'
      return 0
    fi
    printf 'unexpected gh call: %s\n' "$*" >&2
    return 127
  }
  if issue_has_complete_summary "example/repo" "8" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_positive_selftest.err" "- CI run URL/conclusion:" "- Deploy/build run URL/conclusion:" "- GHCR image tags/digest:"; then
    pass "detects complete evidence summary in one issue block"
  else
    fail "misses complete evidence summary in one issue block"
  fi
  if issue_has_complete_summary "example/repo" "9" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_advisory_selftest.err" "- Row-count result:" "- 24h/7d monitoring links:"; then
    fail "unexpectedly detects advisory marker mention as evidence"
  else
    pass "rejects advisory marker mention without standalone evidence heading"
  fi
  if issue_has_complete_summary "example/repo" "10" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_empty_fields_selftest.err" "- CI run URL/conclusion:" "- Deploy/build run URL/conclusion:" "- GHCR image tags/digest:"; then
    fail "unexpectedly accepts empty required evidence fields"
  else
    pass "rejects empty required evidence fields"
  fi
  if issue_has_complete_summary "example/repo" "11" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_split_selftest.err" "- CI run URL/conclusion:" "- Deploy/build run URL/conclusion:" "- GHCR image tags/digest:"; then
    fail "unexpectedly accepts marker and fields split across issue blocks"
  else
    pass "rejects marker and fields split across issue blocks"
  fi
  if issue_has_complete_summary "example/repo" "12" "Chatbot workflow evidence summary:" "${TMP_DIR}/issue_summary_placeholder_selftest.err" "- CI run URL/conclusion:" "- Deploy/build run URL/conclusion:" "- GHCR image tags/digest:"; then
    fail "unexpectedly accepts placeholder evidence field values"
  else
    pass "rejects placeholder evidence field values"
  fi
  if issue_has_complete_summary "example/repo" "13" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_korean_placeholder_selftest.err" "- SQLite backup SHA-256 files:" "- Row-count result:" "- 24h/7d monitoring links:"; then
    fail "unexpectedly accepts Korean placeholder evidence field values"
  else
    pass "rejects Korean placeholder evidence field values"
  fi
  if issue_has_complete_summary "example/repo" "14" "Cutover evidence summary:" "${TMP_DIR}/issue_summary_cutover_positive_selftest.err" "- SQLite backup SHA-256 files:" "- Row-count result:" "- Backend health/core APIs:" "- Chatbot health:" "- 24h/7d monitoring links:"; then
    pass "detects complete cutover evidence summary with backup field"
  else
    fail "misses complete cutover evidence summary with backup field"
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

section "Chatbot Actions runs"
runs_json="${TMP_DIR}/chatbot_runs_gate.json"
if gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" >"${runs_json}" 2>"${TMP_DIR}/chatbot_runs_gate.err"; then
  run_lines="$(gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" --jq '.workflow_runs[] | "\(.name) status=\(.status) conclusion=\(.conclusion) head=\(.head_sha) url=\(.html_url)"' 2>/dev/null || true)"
  success_count="$(gh api "repos/${CHATBOT_REPO}/actions/runs?branch=${CHATBOT_BRANCH}&per_page=10" --jq '[.workflow_runs[] | select(.conclusion == "success")] | length' 2>/dev/null || printf '0')"
  if [[ -z "${run_lines}" ]]; then
    fail "no chatbot Actions runs visible on ${CHATBOT_BRANCH}"
  else
    printf '%s\n' "${run_lines}"
    if [[ "${success_count}" -gt 0 ]]; then pass "at least one successful chatbot Actions run is visible"; else fail "no successful chatbot Actions run visible"; fi
  fi
else
  fail "cannot list chatbot Actions runs via API: $(tr '\n' ' ' <"${TMP_DIR}/chatbot_runs_gate.err")"
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
      fields=("- CI run URL/conclusion:" "- Deploy/build run URL/conclusion:" "- GHCR image tags/digest:")
    elif [[ "${label}" == "cutover" ]]; then
      marker="Cutover evidence summary:"
      fields=("- SQLite backup SHA-256 files:" "- Row-count result:" "- Backend health/core APIs:" "- Chatbot health:" "- 24h/7d monitoring links:")
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
