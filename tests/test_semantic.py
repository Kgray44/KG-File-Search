from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import hybrid_search, semantic_search
from kgfs.semantic import chunk_text, unpack_vector, vector_to_blob


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        lower = text.lower()
        if any(term in lower for term in ("torque", "rotational", "motor")):
            return [1.0, 0.0, 0.0]
        if any(term in lower for term in ("op amp", "op-amp", "thevenin")):
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


def test_chunk_text_preserves_offsets_and_overlap() -> None:
    text = "alpha beta gamma delta epsilon zeta eta theta"

    chunks = chunk_text(text, chunk_size_chars=20, chunk_overlap_chars=5)

    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].start_char == 0
    assert all(text[item.start_char : item.end_char] == item.text for item in chunks)
    assert chunks[1].start_char < chunks[0].end_char


def test_vector_blob_roundtrip_uses_local_sqlite_blob_storage() -> None:
    vector = [0.25, 0.5, 0.75]

    blob = vector_to_blob(vector)

    assert isinstance(blob, bytes)
    assert unpack_vector(blob, 3) == vector


def test_indexing_stores_semantic_chunks_with_embeddings(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor notes.md").write_text(
        "Motor torque lab report. I calculated rotational force from current.\n" * 3,
        encoding="utf-8",
    )
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    summary = index_configured_folders(_semantic_config(root), conn, semantic_embedder=FakeEmbedder())

    rows = conn.execute(
        "SELECT file_id, chunk_index, text, embedding, embedding_dim, start_char, end_char, model_name FROM chunks"
    ).fetchall()
    assert summary.indexed == 1
    assert len(rows) > 1
    assert rows[0]["file_id"] == 1
    assert rows[0]["chunk_index"] == 0
    assert rows[0]["embedding"]
    assert rows[0]["embedding_dim"] == 3
    assert rows[0]["start_char"] == 0
    assert rows[0]["end_char"] > rows[0]["start_char"]
    assert rows[0]["model_name"] == "fake-local-model"


def test_semantic_search_returns_best_matching_chunk(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor notes.md").write_text("rotational force calculations for a motor lab", encoding="utf-8")
    (root / "circuits.md").write_text("Thevenin equivalent and op amp circuit notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(_semantic_config(root), conn, semantic_embedder=FakeEmbedder())

    results = semantic_search(conn, "motor torque", embedder=FakeEmbedder(), model_name="fake-local-model")

    assert results[0].file_name == "motor notes.md"
    assert "rotational force" in results[0].snippet


def test_hybrid_search_combines_keyword_semantic_filename_and_recency(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    motor = root / "motor analysis.md"
    motor.write_text("rotational force calculations from current", encoding="utf-8")
    circuits = root / "circuits.md"
    circuits.write_text("op amp and Thevenin equivalent notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(_semantic_config(root), conn, semantic_embedder=FakeEmbedder())

    results = hybrid_search(conn, "motor torque", embedder=FakeEmbedder(), model_name="fake-local-model")

    assert results[0].file_name == "motor analysis.md"
    assert "rotational force" in results[0].snippet
