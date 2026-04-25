from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search


runner = CliRunner()


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _indexed_db(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "motor.md"
    source.write_text("motor torque vector command source", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
indexed_folders:
  - {root.as_posix()!r}
semantic:
  enabled: true
  model_name: "fake-local-model"
vectors:
  backend: "sqlite_scan"
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    conn.close()
    return config_path, db_path, source


def test_vector_status_command(tmp_path: Path) -> None:
    config_path, db_path, _ = _indexed_db(tmp_path)

    result = runner.invoke(app, ["vector", "status", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code == 0
    assert "sqlite_scan" in result.output
    assert "fake-local-model" in result.output


def test_vector_clear_requires_yes(tmp_path: Path) -> None:
    config_path, db_path, _ = _indexed_db(tmp_path)

    result = runner.invoke(app, ["vector", "clear", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code != 0
    assert "--yes" in result.output


def test_vector_rebuild_and_clear_touch_only_vector_data(tmp_path: Path, mocker) -> None:
    config_path, db_path, source = _indexed_db(tmp_path)
    before_text = source.read_text(encoding="utf-8")
    mocker.patch("kgfs.vectors.index_manager.get_embedder", return_value=FakeEmbedder())

    rebuild = runner.invoke(app, ["vector", "rebuild", "--config", str(config_path), "--database", str(db_path)])

    assert rebuild.exit_code == 0
    conn = connect_database(db_path)
    assert conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"] > 0
    assert search(conn, "motor torque")

    clear = runner.invoke(app, ["vector", "clear", "--yes", "--config", str(config_path), "--database", str(db_path)])

    assert clear.exit_code == 0
    assert conn.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"] == 1
    assert conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"] == 0
    assert search(conn, "motor torque")
    conn.close()
    assert source.read_text(encoding="utf-8") == before_text
