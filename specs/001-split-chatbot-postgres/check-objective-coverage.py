#!/usr/bin/env python3
"""Check that split-chatbot-postgres audit docs cover the objective inputs.

This is a lightweight documentation/audit guard. It does not prove operational
completion; external workflow, GHCR, and production cutover gates still require
real evidence from their runbooks and `check-external-gates.sh`.
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ids(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text)))


def task_ids_with_ranges(text: str) -> list[str]:
    """Return task IDs, expanding forms like T005-T015 and T005–T015."""

    found = set(re.findall(r"\bT\d{3}\b", text))
    for start, end in re.findall(r"\bT(\d{3})\s*[-–]\s*T(\d{3})\b", text):
        start_num = int(start)
        end_num = int(end)
        if start_num > end_num:
            start_num, end_num = end_num, start_num
        found.update(f"T{num:03d}" for num in range(start_num, end_num + 1))
    return sorted(found)


def check_id_coverage(label: str, expected: list[str], audit: str) -> int:
    missing = [item for item in expected if item not in audit]
    if missing:
        print(f"FAIL {label} missing from completion-audit.md: {', '.join(missing)}")
        return 1
    print(f"PASS {label} coverage: {len(expected)} identifiers")
    return 0


def check_required_files() -> int:
    required = [
        ROOT / "codex-prompts.md",
        ROOT / "spec.md",
        ROOT / "plan.md",
        ROOT / "tasks.md",
        ROOT / "completion-audit.md",
        ROOT / "operator-handoff-index.md",
        ROOT / "check-completion-readiness.sh",
        ROOT / "check-external-gates.sh",
        REPO / ".cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"FAIL required file missing: {path.relative_to(REPO)}")
        return 1
    print(f"PASS required objective files: {len(required)} present")
    return 0


def check_local_markdown_links() -> int:
    files = [
        *ROOT.glob("*.md"),
        REPO / "omx_wiki/split-chatbot-postgresql-migration-handoff.md",
        REPO / ".cursor/plans/split_chatbot_postgres_migration_5a689f0e.plan.md",
    ]
    missing: list[tuple[Path, str]] = []
    checked = 0
    for path in files:
        if not path.exists():
            continue
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", read(path)):
            href = match.group(1).split("#", 1)[0]
            if (
                not href
                or "://" in href
                or href.startswith("mailto:")
                or href.startswith("#")
            ):
                continue
            checked += 1
            target = (path.parent / urllib.parse.unquote(href)).resolve()
            if not target.exists():
                missing.append((path, href))
    if missing:
        for path, href in missing:
            print(f"FAIL missing local markdown link: {path.relative_to(REPO)} -> {href}")
        return 1
    print(f"PASS local markdown links: {checked} checked")
    return 0


def check_blocker_language(audit: str) -> int:
    required_phrases = [
        "GAP; goal must not be marked complete",
        "workflow",
        "read:packages",
        "production/staging cutover",
        "GC-MapleWind/maplewind-chatbot#1",
        "CLOSED",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in audit]
    if missing:
        print(f"FAIL blocker language missing: {', '.join(missing)}")
        return 1
    print("PASS blocker language present")
    return 0


def main() -> int:
    status = check_required_files()
    tasks = read(ROOT / "tasks.md")
    spec = read(ROOT / "spec.md")
    audit = read(ROOT / "completion-audit.md")
    prompts = read(ROOT / "codex-prompts.md")

    status |= check_id_coverage("tasks", ids(r"\bT\d{3}\b", tasks), audit)
    status |= check_id_coverage("functional requirements", ids(r"\bFR-\d{3}\b", spec), audit)
    status |= check_id_coverage("success criteria", ids(r"\bSC-\d{3}\b", spec), audit)
    status |= check_id_coverage("prompt task IDs", task_ids_with_ranges(prompts), audit)
    status |= check_local_markdown_links()
    status |= check_blocker_language(audit)

    if status:
        return status
    print("INFO objective coverage audit is documentation-only; run check-external-gates.sh for live external gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
