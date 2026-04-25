from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings, VectorSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search.backends.base import BackendAvailability
from kgfs.vectors.recommend import recommend_vector_backend


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _indexed_config(tmp_path: Path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor.md").write_text("motor torque recommendation notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    return conn, config


def test_vector_recommend_no_chunks_recommends_building_vectors(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    recommendation = recommend_vector_backend(conn, KGFSConfig())

    assert recommendation.backend_name == "sqlite_scan"
    assert any("No semantic chunks" in reason for reason in recommendation.reasons)


def test_vector_recommend_small_index_prefers_sqlite_scan(tmp_path: Path) -> None:
    conn, config = _indexed_config(tmp_path)

    recommendation = recommend_vector_backend(conn, config)

    assert recommendation.backend_name == "sqlite_scan"
    assert any("simple and reliable" in reason for reason in recommendation.reasons)


def test_vector_recommend_unavailable_configured_backend_suggests_fallback(tmp_path: Path) -> None:
    conn, config = _indexed_config(tmp_path)
    config = config.model_copy(update={"vectors": VectorSettings(backend="missing_backend")})

    recommendation = recommend_vector_backend(conn, config)

    assert recommendation.backend_name == "sqlite_scan"
    assert any("configured backend" in reason.lower() for reason in recommendation.reasons)


def test_vector_recommend_large_index_uses_hnsw_when_available(tmp_path: Path, monkeypatch) -> None:
    conn, config = _indexed_config(tmp_path)
    monkeypatch.setattr("kgfs.vectors.recommend.count_chunks", lambda *_args, **_kwargs: 25000)
    monkeypatch.setattr(
        "kgfs.vectors.recommend.backend_availability_by_name",
        lambda *_args, **_kwargs: {
            "sqlite_scan": BackendAvailability(True, "ok"),
            "sqlite_vec": BackendAvailability(False, "missing"),
            "hnsw": BackendAvailability(True, "ok"),
            "faiss": BackendAvailability(False, "missing"),
        },
    )

    recommendation = recommend_vector_backend(conn, config)

    assert recommendation.backend_name == "hnsw"
    assert any("large" in reason.lower() for reason in recommendation.reasons)


def test_vector_recommend_installed_backend_missing_artifact_recommends_rebuild(tmp_path: Path, monkeypatch) -> None:
    conn, config = _indexed_config(tmp_path)
    config = config.model_copy(update={"vectors": VectorSettings(backend="hnsw")})

    class FakeBackend:
        name = "hnsw"

        def available(self, _context):
            return BackendAvailability(False, "hnsw index is missing. Run kgfs vector rebuild --backend hnsw.")

    monkeypatch.setattr("kgfs.vectors.recommend.get_vector_backend", lambda _name: FakeBackend())
    monkeypatch.setattr("kgfs.vectors.recommend.count_chunks", lambda *_args, **_kwargs: 25000)
    monkeypatch.setattr(
        "kgfs.vectors.recommend.backend_availability_by_name",
        lambda *_args, **_kwargs: {
            "sqlite_scan": BackendAvailability(True, "ok"),
            "sqlite_vec": BackendAvailability(False, "missing"),
            "hnsw": BackendAvailability(False, "hnsw index is missing. Run kgfs vector rebuild --backend hnsw."),
            "faiss": BackendAvailability(False, "missing"),
        },
    )

    recommendation = recommend_vector_backend(conn, config)

    assert recommendation.backend_name == "hnsw"
    assert any("rebuild" in reason.lower() for reason in recommendation.reasons)
