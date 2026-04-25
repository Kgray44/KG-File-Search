from pathlib import Path

from fastapi.testclient import TestClient

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.web.app import create_app


def test_web_search_uses_filters_and_saves_results(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "pid.PDF").write_text("pid control design", encoding="utf-8")
    (root / "pid notes.md").write_text("pid control notes", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(
        f"""
indexed_folders:
  - "{root.as_posix()}"
include_extensions:
  - ".pdf"
  - ".md"
database_path: "{db_path.as_posix()}"
""",
        encoding="utf-8",
    )
    conn = connect_database(db_path)
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root], include_extensions=[".pdf", ".md"]), conn)
    conn.close()

    client = TestClient(create_app(config_path=config_path))
    response = client.get("/search", params={"q": "pid", "ext": ".pdf"})

    assert response.status_code == 200
    assert "pid.PDF" in response.text
    assert "pid notes.md" not in response.text


def test_web_open_and_reveal_use_latest_result_ids(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "notes.md"
    source.write_text("motor torque", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(
        f"""
indexed_folders:
  - "{root.as_posix()}"
database_path: "{db_path.as_posix()}"
""",
        encoding="utf-8",
    )
    conn = connect_database(db_path)
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    conn.close()
    opened: list[Path] = []
    revealed: list[Path] = []
    monkeypatch.setattr("kgfs.web.app.open_file", lambda path: opened.append(path))
    monkeypatch.setattr("kgfs.web.app.reveal_file", lambda path: revealed.append(path))

    client = TestClient(create_app(config_path=config_path))
    client.get("/search", params={"q": "motor torque"})

    assert client.get("/open/1").status_code == 200
    assert client.get("/reveal/1").status_code == 200
    assert opened == [source]
    assert revealed == [source]
