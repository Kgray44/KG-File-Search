from pathlib import Path


def test_resource_path_finds_source_tree_files() -> None:
    from kgfs.resources import resource_path

    assert resource_path("config.example.yaml").exists()
    assert resource_path("README.md").exists()
    assert resource_path("kgfs", "web", "templates", "base.html").exists()
    assert resource_path("kgfs", "web", "static", "style.css").exists()


def test_resource_path_uses_pyinstaller_meipass(monkeypatch, tmp_path: Path) -> None:
    from kgfs import resources

    bundled = tmp_path / "config.example.yaml"
    bundled.write_text("indexed_folders: []\n", encoding="utf-8")
    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resources.is_frozen()
    assert resources.bundle_root() == tmp_path
    assert resources.resource_path("config.example.yaml") == bundled


def test_doctor_reports_packaged_status(tmp_path) -> None:
    from typer.testing import CliRunner

    from kgfs.cli import app

    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    result = CliRunner().invoke(app, ["doctor", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code == 0
    assert "Packaged/frozen" in result.output
    assert "Executable path" in result.output
