"""SQLite database helpers."""

from kgfs.db.connection import KGFSRow, connect_database
from kgfs.db.latest_results import get_latest_result_path, save_latest_results
from kgfs.db.repositories import (
    count_chunks_for_file,
    delete_chunks_for_file,
    get_existing_file,
    replace_file_fts_row,
    upsert_file,
)
from kgfs.db.schema import check_fts5_available, initialize_database
from kgfs.db.stats import get_database_stats

__all__ = [
    "KGFSRow",
    "check_fts5_available",
    "connect_database",
    "count_chunks_for_file",
    "delete_chunks_for_file",
    "get_database_stats",
    "get_existing_file",
    "get_latest_result_path",
    "initialize_database",
    "replace_file_fts_row",
    "save_latest_results",
    "upsert_file",
]
