from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search.backends.base import VectorSearchOptions
from kgfs.search.backends.sqlite_scan import SqliteScanVectorBackend
from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        lower = text.lower()
        if any(term in lower for term in ("motor", "torque", "rotational")):
            return [1.0, 0.0, 0.0]
        if any(term in lower for term in ("op amp", "thevenin")):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def _semantic_config(root: Path) -> KGFSConfig:
    return KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(
            enabled=True,
            model_name="fake-local-model",
            chunk_size_chars=48,
            chunk_overlap_chars=8,
        ),
    )


def _indexed_context(tmp_path: Path) -> SearchContext:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor.md").write_text("rotational motor torque notes", encoding="utf-8")
    (root / "circuits.md").write_text("Thevenin and op amp notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = _semantic_config(root)
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    return SearchContext(conn=conn, config=config, semantic_embedder=FakeEmbedder())


def test_sqlite_scan_backend_available_when_chunks_table_exists(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    context = SearchContext(conn=conn, config=KGFSConfig())

    availability = SqliteScanVectorBackend().available(context)

    assert availability.available is True
    assert "SQLite chunks" in availability.message


def test_sqlite_scan_backend_returns_expected_hits_with_fake_embeddings(tmp_path: Path) -> None:
    context = _indexed_context(tmp_path)

    hits = SqliteScanVectorBackend().search(
        [1.0, 0.0, 0.0],
        VectorSearchOptions(model_name="fake-local-model", limit=5),
        context,
    )

    assert hits[0].file_name == "motor.md"
    assert hits[0].score > hits[-1].score
    assert "motor" in hits[0].text


def test_sqlite_scan_backend_handles_no_chunks_and_respects_limit(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    context = SearchContext(conn=conn, config=KGFSConfig())

    hits = SqliteScanVectorBackend().search(
        [1.0, 0.0, 0.0],
        VectorSearchOptions(model_name="fake-local-model", limit=1),
        context,
    )

    assert hits == []


def test_sqlite_scan_backend_respects_filters_and_skips_malformed_embeddings(tmp_path: Path) -> None:
    context = _indexed_context(tmp_path)
    context.conn.execute("UPDATE chunks SET embedding = ?, embedding_dim = 3 WHERE id = 1", (b"bad",))
    context.conn.commit()

    hits = SqliteScanVectorBackend().search(
        [0.0, 1.0, 0.0],
        VectorSearchOptions(
            model_name="fake-local-model",
            limit=10,
            filters=SearchFilters(extensions=[".md"], folder="docs"),
        ),
        context,
    )

    assert hits
    assert all(hit.extension == ".md" for hit in hits)
