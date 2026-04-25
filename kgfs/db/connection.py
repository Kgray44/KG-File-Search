"""SQLite connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterator


def connect_database(database_path: Path) -> sqlite3.Connection:
    database_path = database_path.expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class KGFSRow:
    def __init__(self, keys: list[str], values: tuple[Any, ...]) -> None:
        self._keys = keys
        self._values = values
        self._index = {key: index for index, key in enumerate(keys)}

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, str):
            return self._values[self._index[key]]
        return self._values[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return self._values == other
        if isinstance(other, KGFSRow):
            return self._values == other._values
        return False

    def keys(self) -> list[str]:
        return self._keys.copy()


def _row_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> KGFSRow:
    return KGFSRow([description[0] for description in cursor.description], row)
