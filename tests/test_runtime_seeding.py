import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_python_snippet(code: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_seed_command(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.seed_real_data"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _count_rows(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0

    with sqlite3.connect(db_path) as conn:
        table_exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0]
        if table_exists == 0:
            return 0
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _create_seed_files(init_dir: Path) -> None:
    init_dir.mkdir(parents=True, exist_ok=True)

    roster_path = init_dir / "25-2 단풍바람 명부.xlsx"
    settlement_path = init_dir / "메생결산시트.xlsx"

    roster_wb = openpyxl.Workbook()
    roster_ws = roster_wb.active
    if roster_ws is None:
        raise RuntimeError("Failed to create roster worksheet")
    roster_ws.title = "25-2"
    roster_ws.append(
        [
            "name",
            "gender",
            "dept",
            "student_id",
            "nickname",
            "level",
            "server",
            "character_gender",
            "job",
        ]
    )
    roster_ws.append([
        "seed-user",
        "남자",
        "dev",
        20260001,
        "seednick",
        260,
        "LUNA",
        "",
        "Hero",
    ])
    roster_wb.save(roster_path)

    settlement_wb = openpyxl.Workbook()
    settlement_ws = settlement_wb.active
    if settlement_ws is None:
        raise RuntimeError("Failed to create settlement worksheet")
    settlement_ws.title = "Sheet1"
    settlement_ws.append(["id", "name", "nickname", "date", "img_name", "caption"])
    settlement_ws.append([1, "seed-user", "seednick", 260101, None, "Seed settlement"])
    settlement_wb.save(settlement_path)


class RuntimeSeedingTests(unittest.TestCase):
    def _base_env(self, db_path: Path, init_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
                "ADMIN_SESSION_SECRET": "test-admin-secret",
                "JWT_SECRET_KEY": "test-jwt-secret",
                "INIT_DATA_DIR": str(init_dir),
                "PYTHONPATH": str(PROJECT_ROOT),
            }
        )
        return env

    def test_startup_does_not_seed_without_explicit_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "runtime.db"
            init_dir = temp_root / "init-data"
            env = self._base_env(db_path, init_dir)

            result = _run_python_snippet(
                (
                    "import asyncio\n"
                    "from src.main import app\n"
                    "async def _run():\n"
                    "    async with app.router.lifespan_context(app):\n"
                    "        pass\n"
                    "asyncio.run(_run())\n"
                ),
                env,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(_count_rows(db_path, "users"), 0)
            self.assertEqual(_count_rows(db_path, "characters"), 0)
            self.assertEqual(_count_rows(db_path, "comments"), 0)

    def test_src_main_has_no_scripts_import(self) -> None:
        src_main = (PROJECT_ROOT / "src" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("from scripts.", src_main)

    def test_explicit_seed_command_uses_init_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "seed.db"
            init_dir = temp_root / "seed-input"
            _create_seed_files(init_dir)
            env = self._base_env(db_path, init_dir)

            result = _run_seed_command(env)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(_count_rows(db_path, "users"), 1)
            self.assertEqual(_count_rows(db_path, "characters"), 1)
            self.assertEqual(_count_rows(db_path, "settlements"), 1)

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT username, name FROM users WHERE name = ?", ("seed-user",)
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "20260001")

    def test_explicit_seed_command_fails_with_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "missing.db"
            init_dir = temp_root / "missing-seed-input"
            init_dir.mkdir(parents=True, exist_ok=True)
            env = self._base_env(db_path, init_dir)

            result = _run_seed_command(env)

            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
