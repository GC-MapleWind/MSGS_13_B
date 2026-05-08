#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: validate-cutover-evidence-summary.sh <markdown-file>
       validate-cutover-evidence-summary.sh --self-test

Validate that a local issue-comment draft contains one complete
`Cutover evidence summary:` block before posting it to
GC-MapleWind/MSGS_13_B#55. This is an operator-preflight check only; it does
not execute production cutover and does not prove completion by itself.

The validator rejects empty, placeholder, Korean placeholder, and split/advisory
summary blocks. The real readiness checker still re-reads issue #55 after the
comment is posted.
USAGE
}

required_fields=(
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

validate_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "Missing markdown file: $file" >&2
    return 2
  fi

  local fields_join
  fields_join="$(printf '%s\034' "${required_fields[@]}")"
  fields_join="${fields_join%$'\034'}"

  awk -v marker="Cutover evidence summary:" -v fields_join="$fields_join" '
    BEGIN {
      fields_count = split(fields_join, fields, "\034")
      in_block = 0
      found_marker = 0
      complete = 0
      for (i = 1; i <= fields_count; i++) {
        field_seen[i] = 0
        field_value[i] = ""
      }
    }
    function trim(value) {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      return value
    }
    function normalized(value, out) {
      out = tolower(value)
      gsub(/[`*_[:space:]]+/, "", out)
      gsub(/[[:punct:]]+$/, "", out)
      return out
    }
    function valid_value(value, norm) {
      value = trim(value)
      norm = normalized(value)
      return value != "" && norm !~ /^(tbd|todo|pending|none|null|na|n\/a|placeholder|replace|replace-me|replaceme|changeme|unknown|tobedetermined|미정|대기|없음)$/
    }
    function reset_block(i) {
      for (i = 1; i <= fields_count; i++) {
        field_seen[i] = 0
        field_value[i] = ""
      }
    }
    function evaluate_block(i) {
      if (!found_marker) {
        return
      }
      block_complete = 1
      for (i = 1; i <= fields_count; i++) {
        if (!field_seen[i]) {
          missing[++missing_count] = fields[i]
          block_complete = 0
        } else if (!valid_value(field_value[i])) {
          invalid[++invalid_count] = fields[i]
          block_complete = 0
        }
      }
      if (block_complete) {
        complete = 1
      }
    }
    $0 == marker {
      if (found_marker) {
        evaluate_block()
        reset_block()
      }
      found_marker = 1
      in_block = 1
      next
    }
    in_block && /^##[[:space:]]+/ {
      evaluate_block()
      in_block = 0
      next
    }
    in_block {
      for (i = 1; i <= fields_count; i++) {
        if (index($0, fields[i]) == 1) {
          field_seen[i] = 1
          field_value[i] = substr($0, length(fields[i]) + 1)
        }
      }
    }
    END {
      if (in_block) {
        evaluate_block()
      }
      if (!found_marker) {
        print "FAIL missing standalone Cutover evidence summary: marker" > "/dev/stderr"
        exit 1
      }
      if (complete) {
        print "PASS complete Cutover evidence summary block"
        exit 0
      }
      for (i = 1; i <= missing_count; i++) {
        print "FAIL missing required field: " missing[i] > "/dev/stderr"
      }
      for (i = 1; i <= invalid_count; i++) {
        print "FAIL empty or placeholder value for field: " invalid[i] > "/dev/stderr"
      }
      exit 1
    }
  ' "$file"
}

run_self_test() {
  local tmpdir
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/cutover-evidence-validator.XXXXXX")"
  trap 'rm -rf "$tmpdir"' RETURN

  cat >"$tmpdir/complete.md" <<'MARKDOWN'
Cutover evidence summary:
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
MARKDOWN

  cat >"$tmpdir/placeholder.md" <<'MARKDOWN'
Cutover evidence summary:
- Environment: production
- Window: TBD.
- Main image: pending
- Chatbot image: replace me
- SQLite backup SHA-256 files: 미정
- Row-count result: 대기
- Backend health/core APIs: unknown
- Chatbot health: 없음
- Kakao/Google Sheets smoke: placeholder
- Downtime: To be determined
- Webhook route + 7-day compatibility expiry: TODO
- SLA p95/p99: n/a
- Chatbot-only redeploy elapsed/backend restart evidence: changeme
- 24h/7d monitoring links:
- Rollback used?: none
- Remaining follow-ups: TBD
MARKDOWN

  cat >"$tmpdir/split.md" <<'MARKDOWN'
Cutover evidence summary:
- Environment: staging

## Later comment
- Window: 2026-05-09 01:00-01:25 KST
MARKDOWN

  validate_file "$tmpdir/complete.md" >/dev/null
  if validate_file "$tmpdir/placeholder.md" >/dev/null 2>&1; then
    echo "FAIL self-test accepted placeholder summary" >&2
    return 1
  fi
  if validate_file "$tmpdir/split.md" >/dev/null 2>&1; then
    echo "FAIL self-test accepted split summary" >&2
    return 1
  fi
  echo "PASS cutover evidence validator self-test"
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

case "$1" in
  -h|--help)
    usage
    ;;
  --self-test)
    run_self_test
    ;;
  *)
    validate_file "$1"
    ;;
esac
