from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database, save_latest_results
from kgfs.indexing import index_configured_folders
from kgfs.search import search
from kgfs.workflows.collections import add_results_to_collection, create_collection
from kgfs.workflows.projects import add_results_to_project, create_project
from kgfs.workflows.tags import tag_result


runner = CliRunner()


def _make_corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "corpus"
    root.mkdir()
    source = root / "motor torque notes.md"
    source.write_text("motor torque derivation and gearbox notes", encoding="utf-8")
    (root / "audio filter.txt").write_text("op amp crossover filter", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(
        f"""
indexed_folders:
  - "{root.as_posix()}"
database_path: "{db_path.as_posix()}"
search:
  default_mode: "keyword"
api:
  require_token: true
  token_env: "KGFS_TEST_API_TOKEN"
""",
        encoding="utf-8",
    )
    conn = connect_database(db_path)
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[root], database_path=db_path)
    index_configured_folders(config, conn)
    results = search(conn, "motor torque", limit=5)
    save_latest_results(conn, "motor torque", results)
    create_collection(conn, "Motor Project")
    add_results_to_collection(conn, "Motor Project", [1])
    create_project(conn, "Robotics")
    add_results_to_project(conn, "Robotics", [1])
    tag_result(conn, 1, ["robotics"])
    conn.close()
    return root, config_path, db_path


def test_phase9_config_defaults_are_safe() -> None:
    config = KGFSConfig()

    assert config.ui.default_surface == "cli"
    assert config.ui.tui_enabled is True
    assert config.ui.web_enabled is True
    assert config.api.enabled is False
    assert config.api.host == "127.0.0.1"
    assert config.api.require_token is True
    assert config.api.allow_file_actions is False
    assert config.integrations.enabled is True
    assert config.integrations.tray_enabled is False


def test_web_dashboard_enhanced_local_pages_and_mode_search(tmp_path: Path) -> None:
    from kgfs.web.app import create_app

    _, config_path, _ = _make_corpus(tmp_path)
    client = TestClient(create_app(config_path=config_path))

    response = client.get(
        "/search",
        params={"q": "motor torque", "mode": "keyword", "ext": ".md", "limit": 5},
    )

    assert response.status_code == 200
    assert 'name="mode"' in response.text
    assert "motor torque notes.md" in response.text
    assert "Mode used" in response.text
    assert "robotics" in response.text
    for path in ("/collections", "/tags", "/projects", "/health", "/graph?q=motor+torque"):
        page = client.get(path)
        assert page.status_code == 200
        assert "KG File Search" in page.text


def test_local_api_requires_token_and_uses_bounded_actions(tmp_path: Path, monkeypatch) -> None:
    from kgfs.api.app import create_api_app

    _, config_path, _ = _make_corpus(tmp_path)
    monkeypatch.setenv("KGFS_TEST_API_TOKEN", "secret-token")
    client = TestClient(create_api_app(config_path=config_path))

    assert client.get("/health").status_code == 401
    headers = {"Authorization": "Bearer secret-token"}
    health = client.get("/health", headers=headers)
    search_response = client.get("/search", params={"q": "motor torque", "mode": "keyword"}, headers=headers)
    arbitrary_open = client.post("/open", json={"path": "C:/Users/kkids/secret.txt"}, headers=headers)
    latest_open = client.post("/open/1", headers=headers)

    assert health.status_code == 200
    assert health.json()["local_only"] is True
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["file_name"] == "motor torque notes.md"
    assert arbitrary_open.status_code == 404
    assert latest_open.status_code == 403


def test_serve_refuses_non_local_host_without_explicit_network_flag(tmp_path: Path, monkeypatch) -> None:
    _, config_path, db_path = _make_corpus(tmp_path)
    monkeypatch.setenv("KGFS_TEST_API_TOKEN", "secret-token")

    refused = runner.invoke(
        app,
        [
            "serve",
            "--host",
            "0.0.0.0",
            "--dry-run",
            "--config",
            str(config_path),
            "--database",
            str(db_path),
        ],
    )
    allowed = runner.invoke(
        app,
        [
            "serve",
            "--host",
            "0.0.0.0",
            "--allow-network",
            "--dry-run",
            "--config",
            str(config_path),
            "--database",
            str(db_path),
        ],
    )

    assert refused.exit_code != 0
    assert "127.0.0.1" in refused.output or "network" in refused.output.casefold()
    assert allowed.exit_code == 0
    assert "Dry run" in allowed.output


def test_integration_status_and_scaffolds_write_only_to_output_dir(tmp_path: Path) -> None:
    from kgfs.integrations.status import get_integration_status

    output = tmp_path / "integrations"
    source = tmp_path / "source.md"
    source.write_text("do not touch", encoding="utf-8")
    before = source.read_bytes()

    statuses = get_integration_status()
    result = runner.invoke(app, ["integrations", "raycast", "export", "--output", str(output / "raycast")])
    explorer = runner.invoke(app, ["integrations", "explorer", "scaffold", "--output", str(output / "explorer")])
    tray = runner.invoke(app, ["tray", "scaffold", "--output", str(output / "tray")])

    assert {item.name for item in statuses} >= {"raycast", "alfred", "powertoys", "finder", "explorer", "tray"}
    assert result.exit_code == 0
    assert explorer.exit_code == 0
    assert tray.exit_code == 0
    assert (output / "raycast" / "kgfs-search.sh").exists()
    assert (output / "explorer" / "README.md").exists()
    assert (output / "tray" / "README.md").exists()
    assert source.read_bytes() == before
    assert not any(path.name == ".kgfs" for path in tmp_path.rglob("*"))


def test_tui_command_is_lazy_and_has_dependency_check() -> None:
    cli_module = importlib.import_module("kgfs.cli.app")

    assert cli_module.app is app
    assert "kgfs.tui.app" not in importlib.sys.modules

    result = runner.invoke(app, ["tui", "--check"])

    assert result.exit_code == 0
    assert "Textual" in result.output
