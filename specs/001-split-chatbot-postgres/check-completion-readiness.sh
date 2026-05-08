#!/usr/bin/env bash
# Run local objective coverage, helper self-tests, and live external gate diagnostics.
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

printf '\n== External gate parser self-test ==\n'
if bash specs/001-split-chatbot-postgres/check-external-gates.sh --self-test; then
  printf 'PASS external gate parser self-test\n'
else
  printf 'FAIL external gate parser self-test\n'
  failures=$((failures + 1))
fi

printf '\n== Operator helper self-tests ==\n'
helper_failures=0
for helper in \
  specs/001-split-chatbot-postgres/prepare-chatbot-workflows.sh \
  specs/001-split-chatbot-postgres/validate-cutover-evidence-summary.sh
 do
  if [[ -x "${helper}" ]]; then
    printf 'PASS %s is executable\n' "${helper}"
  else
    printf 'FAIL %s is not executable\n' "${helper}"
    helper_failures=$((helper_failures + 1))
  fi

  if bash -n "${helper}"; then
    printf 'PASS %s bash syntax\n' "${helper}"
  else
    printf 'FAIL %s bash syntax\n' "${helper}"
    helper_failures=$((helper_failures + 1))
  fi
 done

if specs/001-split-chatbot-postgres/prepare-chatbot-workflows.sh --help >/dev/null; then
  printf 'PASS prepare-chatbot-workflows help\n'
else
  printf 'FAIL prepare-chatbot-workflows help\n'
  helper_failures=$((helper_failures + 1))
fi

if specs/001-split-chatbot-postgres/validate-cutover-evidence-summary.sh --self-test >/dev/null; then
  printf 'PASS cutover evidence validator self-test\n'
else
  printf 'FAIL cutover evidence validator self-test\n'
  helper_failures=$((helper_failures + 1))
fi

if [[ "${helper_failures}" -eq 0 ]]; then
  printf 'PASS operator helper self-tests\n'
else
  printf 'FAIL operator helper self-tests failures=%s\n' "${helper_failures}"
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
