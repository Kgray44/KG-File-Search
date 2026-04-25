from pathlib import Path

from kgfs.app_dirs import AppPaths, get_app_paths, resolve_database_path


def test_project_local_app_paths_are_inside_project(tmp_path: Path) -> None:
    paths = get_app_paths(project_local=True, project_root=tmp_path)

    assert paths.config_dir == tmp_path / ".kgfs"
    assert paths.data_dir == tmp_path / ".kgfs"
    assert paths.cache_dir == tmp_path / ".kgfs" / "cache"
    assert paths.default_config_path == tmp_path / ".kgfs" / "config.yaml"
    assert paths.default_database_path == tmp_path / ".kgfs" / "kgfs.sqlite3"


def test_database_path_prefers_cli_then_env_then_config(tmp_path: Path, monkeypatch) -> None:
    app_paths = AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        default_config_path=tmp_path / "config" / "config.yaml",
        default_database_path=tmp_path / "data" / "default.sqlite3",
    )
    monkeypatch.setenv("KGFS_DATABASE_PATH", str(tmp_path / "env.sqlite3"))

    assert resolve_database_path(app_paths, tmp_path / "cli.sqlite3", tmp_path / "config.sqlite3") == tmp_path / "cli.sqlite3"
    assert resolve_database_path(app_paths, None, tmp_path / "config.sqlite3") == tmp_path / "env.sqlite3"

    monkeypatch.delenv("KGFS_DATABASE_PATH")
    assert resolve_database_path(app_paths, None, tmp_path / "config.sqlite3") == tmp_path / "config.sqlite3"
    assert resolve_database_path(app_paths, None, None) == tmp_path / "data" / "default.sqlite3"


def test_default_app_paths_come_from_platformdirs(tmp_path: Path, monkeypatch) -> None:
    class FakePlatformDirs:
        def __init__(self, app_name: str, app_author: str) -> None:
            self.user_config_dir = str(tmp_path / "Config Dir")
            self.user_data_dir = str(tmp_path / "Data Dir")
            self.user_cache_dir = str(tmp_path / "Cache Dir")
            self.user_log_dir = str(tmp_path / "Log Dir")

    monkeypatch.setattr("kgfs.app_dirs.PlatformDirs", FakePlatformDirs)

    paths = get_app_paths(project_local=False)

    assert paths.config_dir == tmp_path / "Config Dir"
    assert paths.data_dir == tmp_path / "Data Dir"
    assert paths.cache_dir == tmp_path / "Cache Dir"
    assert paths.log_dir == tmp_path / "Log Dir"
