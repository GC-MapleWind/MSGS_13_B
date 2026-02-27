from pathlib import Path

from database import _sqlite_db_path, ensure_sqlite_directory


def test_sqlite_path_parsing_relative_path() -> None:
    parsed = _sqlite_db_path("sqlite+aiosqlite:///./data/maplewind.db")
    assert parsed == Path("./data/maplewind.db")


def test_ensure_sqlite_directory_creates_parent(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "maplewind.db"
    url = f"sqlite+aiosqlite:///{db_file}"

    ensure_sqlite_directory(url)

    assert (tmp_path / "nested").exists()
    assert (tmp_path / "nested").is_dir()
