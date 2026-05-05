"""Run pgloader-based SQLite -> PostgreSQL migration.

This Python wrapper delegates to scripts/migrate_sqlite_to_postgres.sh so it can be
called consistently with `uv run python -m scripts.migrate_sqlite_to_postgres ...`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).with_suffix(".sh")
    return subprocess.call([str(script), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
