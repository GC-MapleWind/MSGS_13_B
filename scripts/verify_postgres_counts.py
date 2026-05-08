"""Compare SQLite and PostgreSQL table row counts after pgloader migration."""
from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Iterable
from pathlib import Path

import psycopg

MAIN_TABLES = ["users", "characters", "settlements", "comments", "team_members", "team_messages"]
CHATBOT_TABLES = ["eventinfo", "infolist", "temporary_images"]


def sqlite_count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0]
        if not exists:
            return 0
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def postgres_count(conn: psycopg.Connection, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        if cur.fetchone()[0] is None:
            return 0
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return int(cur.fetchone()[0])


def compare(sqlite_db: Path, postgres_url: str, tables: Iterable[str]) -> int:
    failures = 0
    with psycopg.connect(postgres_url) as conn:
        for table in tables:
            s_count = sqlite_count(sqlite_db, table)
            p_count = postgres_count(conn, table)
            status = "OK" if s_count == p_count else "MISMATCH"
            print(f"{status:8} {table:20} sqlite={s_count:<8} postgres={p_count:<8}")
            failures += int(s_count != p_count)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["main", "chatbot"])
    parser.add_argument("sqlite_db", type=Path)
    parser.add_argument("postgres_url")
    args = parser.parse_args()
    tables = MAIN_TABLES if args.service == "main" else CHATBOT_TABLES
    return min(compare(args.sqlite_db, args.postgres_url, tables), 1)


if __name__ == "__main__":
    raise SystemExit(main())
