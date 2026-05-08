#!/usr/bin/env bash
# Run the local objective coverage guard and live external gate diagnostics.
# This wrapper is diagnostic only: a zero exit still requires inspecting the
# evidence templates and production/cutover artifacts before completion.

set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

failures=0

printf '== Objective coverage audit ==\n'
if python3 specs/001-split-chatbot-postgres/check-objective-coverage.py; then
  printf 'PASS objective coverage audit\n'
else
  printf 'FAIL objective coverage audit\n'
  failures=$((failures + 1))
fi

printf '\n== Live external gate diagnostics ==\n'
if bash specs/001-split-chatbot-postgres/check-external-gates.sh; then
  printf 'PASS live external gate diagnostics returned zero observable failures\n'
else
  printf 'FAIL live external gate diagnostics reported blockers\n'
  failures=$((failures + 1))
fi

printf '\n== Readiness wrapper summary ==\n'
if [[ "${failures}" -eq 0 ]]; then
  printf 'INFO wrapper checks returned zero failures; still inspect operator evidence before marking complete\n'
  exit 0
fi
printf 'INFO wrapper failures=%s; objective is not ready for completion\n' "${failures}"
exit 1
