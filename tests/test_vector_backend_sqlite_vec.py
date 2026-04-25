from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from kgfs.config import KGFSConfig, SemanticSettings, SqliteVecSettings, VectorSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search.backends.base import VectorSearchOptions
from kgfs.search.backends.sqlite_vec import SqliteVecVectorBackend
from kgfs.search.engine import SearchContext


def _context(tmp_path: Path) -> SearchContext:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        database_path=tmp_path / "kgfs.sqlite3",
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
        vectors=VectorSettings(backend="sqlite_vec", sqlite_vec=SqliteVecSettings(enabled=True)),
    )
    return SearchContext(conn=conn, config=config)


def test_sqlite_vec_rebuild_missing_dependency_is_helpful(tmp_path: Path) -> None:
    if importlib.util.find_spec("sqlite_vec") is not None:
        pytest.skip("sqlite-vec is installed; installed-backend tests cover rebuild behavior.")

    with pytest.raises(RuntimeError, match="sqlite-vec"):
        SqliteVecVectorBackend().rebuild(_context(tmp_path), model_name="fake-local-model")


@pytest.mark.skipif(importlib.util.find_spec("sqlite_vec") is None, reason="sqlite-vec optional dependency is not installed")
def test_sqlite_vec_rebuild_search_and_clear_when_dependency_installed(tmp_path: Path) -> None:
    context, source = _indexed_context(tmp_path)
    before_text = source.read_text(encoding="utf-8")
    backend = SqliteVecVectorBackend()

    rebuild = backend.rebuild(context, model_name="fake-local-model")
    assert backend.available(context).available is True
    hits = backend.search([1.0, 0.0, 0.0], VectorSearchOptions(model_name="fake-local-model", limit=2), context)
    removed = backend.clear(context, model_name="fake-local-model")

    assert rebuild.chunk_count > 0
    assert hits[0].file_name == "motor.md"
    assert removed > 0
    assert context.conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"] > 0
    assert source.read_text(encoding="utf-8") == before_text


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] if "motor" in text.lower() else [0.0, 1.0, 0.0] for text in texts]


def _indexed_context(tmp_path: Path) -> tuple[SearchContext, Path]:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "motor.md"
    source.write_text("motor torque sqlite vec notes", encoding="utf-8")
    (root / "circuits.md").write_text("op amp sqlite vec notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        database_path=tmp_path / "kgfs.sqlite3",
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
        vectors=VectorSettings(backend="sqlite_vec", sqlite_vec=SqliteVecSettings(enabled=True)),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    return SearchContext(conn=conn, config=config), source
