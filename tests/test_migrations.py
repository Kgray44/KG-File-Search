from pathlib import Path

from kgfs.database import connect_database, initialize_database
from kgfs.migrations import CURRENT_SCHEMA_VERSION, get_schema_version, migrate_database


def test_new_database_initializes_with_current_schema_version(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")

    initialize_database(conn)

    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION


def test_database_initialization_is_idempotent(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")

    initialize_database(conn)
    initialize_database(conn)
    migrate_database(conn)

    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    assert conn.execute("SELECT COUNT(*) AS count FROM schema_version").fetchone()["count"] == 1

