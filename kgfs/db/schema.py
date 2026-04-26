"""SQLite schema creation helpers."""

from __future__ import annotations

import sqlite3

from kgfs.db.migrations import migrate_database


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            normalized_path TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            extension TEXT NOT NULL,
            size INTEGER NOT NULL,
            modified_time REAL NOT NULL,
            modified_time_ns INTEGER,
            content_hash TEXT,
            extracted_text TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            platform_indexed_from TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            extraction_error TEXT,
            extraction_source TEXT NOT NULL DEFAULT 'text'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            file_name,
            path,
            extracted_text,
            tokenize='porter unicode61'
        );

        CREATE TABLE IF NOT EXISTS latest_results (
            result_id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            embedding_dim INTEGER NOT NULL,
            start_char INTEGER,
            end_char INTEGER,
            model_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(file_id, chunk_index, model_name)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_model_name ON chunks(model_name);

        CREATE TABLE IF NOT EXISTS ocr_cache (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            normalized_path TEXT NOT NULL,
            content_hash TEXT,
            size INTEGER NOT NULL,
            modified_time_ns INTEGER NOT NULL,
            backend TEXT NOT NULL,
            language TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(normalized_path, content_hash, size, modified_time_ns, backend, language, source_kind)
        );

        CREATE INDEX IF NOT EXISTS idx_ocr_cache_lookup
        ON ocr_cache(normalized_path, content_hash, size, modified_time_ns, backend, language, source_kind);

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            folders_json TEXT NOT NULL DEFAULT '[]',
            extensions_json TEXT NOT NULL DEFAULT '[]',
            default_mode TEXT NOT NULL DEFAULT 'auto',
            boost_terms_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            query TEXT NOT NULL,
            mode TEXT,
            filters_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collection_items (
            id INTEGER PRIMARY KEY,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            result_id INTEGER,
            note TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(collection_id, file_id)
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS file_tags (
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY(file_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS file_notes (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_items (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            role TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(project_id, file_id)
        );

        CREATE TABLE IF NOT EXISTS assignment_runs (
            id INTEGER PRIMARY KEY,
            topic TEXT NOT NULL,
            created_at TEXT NOT NULL,
            query_json TEXT,
            result_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name);
        CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name);
        CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name);
        CREATE INDEX IF NOT EXISTS idx_collection_items_collection ON collection_items(collection_id);
        CREATE INDEX IF NOT EXISTS idx_collection_items_file ON collection_items(file_id);
        CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
        CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id);
        CREATE INDEX IF NOT EXISTS idx_file_notes_file ON file_notes(file_id);
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        CREATE INDEX IF NOT EXISTS idx_project_items_project ON project_items(project_id);
        CREATE INDEX IF NOT EXISTS idx_project_items_file ON project_items(file_id);
        """
    )
    migrate_database(conn)
    conn.commit()


def check_fts5_available() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE fts_check USING fts5(content)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
