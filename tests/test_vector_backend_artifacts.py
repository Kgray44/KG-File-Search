from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.semantic import vector_to_blob
from kgfs.vectors.metadata import (
    backend_metadata_health,
    current_backend_metadata,
    read_backend_metadata,
    write_backend_metadata,
)
from kgfs.vectors.storage import backend_artifact_dir


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _indexed_config_and_db(tmp_path: Path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor.md").write_text("motor torque vector artifact notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        database_path=tmp_path / "kgfs.sqlite3",
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    return config, conn, root


def test_backend_artifacts_live_under_kgfs_database_area_not_source_folder(tmp_path: Path) -> None:
    config, _, source_root = _indexed_config_and_db(tmp_path)

    artifact_dir = backend_artifact_dir(config, "hnsw", model_name="fake-local-model")

    assert artifact_dir.is_relative_to(tmp_path)
    assert not artifact_dir.is_relative_to(source_root)


def test_backend_metadata_roundtrip_and_stale_detection(tmp_path: Path) -> None:
    config, conn, _ = _indexed_config_and_db(tmp_path)

    metadata = current_backend_metadata(conn, config, "hnsw", "fake-local-model")
    write_backend_metadata(config, metadata)

    loaded = read_backend_metadata(config, "hnsw", "fake-local-model")
    healthy = backend_metadata_health(conn, config, "hnsw", "fake-local-model")

    assert loaded is not None
    assert loaded.chunk_count == metadata.chunk_count
    assert healthy.ready is True
    assert healthy.status == "ready"

    conn.execute(
        "UPDATE chunks SET embedding = ? WHERE id = (SELECT MIN(id) FROM chunks)",
        (vector_to_blob([0.0, 1.0, 0.0]),),
    )
    conn.commit()

    stale = backend_metadata_health(conn, config, "hnsw", "fake-local-model")

    assert stale.ready is False
    assert stale.status == "stale"
    assert any("fingerprint" in reason for reason in stale.reasons)
