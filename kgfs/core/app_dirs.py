"""Cross-platform app directory resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

from kgfs.core.path_utils import expand_user_path

APP_NAME = "KG File Search"
APP_AUTHOR = "KGFS"


@dataclass(frozen=True)
class AppPaths:
    config_dir: Path
    data_dir: Path
    cache_dir: Path
    log_dir: Path
    default_config_path: Path
    default_database_path: Path


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _path_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return expand_user_path(value)


def get_app_paths(
    *,
    project_local: bool | None = None,
    project_root: Path | None = None,
    config_dir_override: Path | None = None,
    data_dir_override: Path | None = None,
    cache_dir_override: Path | None = None,
    log_dir_override: Path | None = None,
) -> AppPaths:
    """Return platform-specific config/data/cache/log paths.

    Project-local mode is intended for development and tests. It stores all app
    data under `.kgfs` inside the chosen project root.
    """

    if project_local is None:
        project_local = _env_truthy("KGFS_PROJECT_LOCAL")

    if project_local:
        root = (project_root or Path.cwd()) / ".kgfs"
        config_dir = config_dir_override or root
        data_dir = data_dir_override or root
        cache_dir = cache_dir_override or root / "cache"
        log_dir = log_dir_override or root / "logs"
    else:
        dirs = PlatformDirs(APP_NAME, APP_AUTHOR)
        config_dir = config_dir_override or _path_from_env("KGFS_CONFIG_DIR") or Path(dirs.user_config_dir)
        data_dir = data_dir_override or _path_from_env("KGFS_DATA_DIR") or Path(dirs.user_data_dir)
        cache_dir = cache_dir_override or _path_from_env("KGFS_CACHE_DIR") or Path(dirs.user_cache_dir)
        log_dir = log_dir_override or _path_from_env("KGFS_LOG_DIR") or Path(dirs.user_log_dir)

    return AppPaths(
        config_dir=config_dir,
        data_dir=data_dir,
        cache_dir=cache_dir,
        log_dir=log_dir,
        default_config_path=config_dir / "config.yaml",
        default_database_path=data_dir / "kgfs.sqlite3",
    )


def resolve_config_path(app_paths: AppPaths, cli_config_path: Path | None = None) -> Path:
    """Resolve config path with CLI taking precedence over environment."""

    if cli_config_path is not None:
        return expand_user_path(cli_config_path)
    env_path = _path_from_env("KGFS_CONFIG_PATH")
    return env_path or app_paths.default_config_path


def resolve_database_path(
    app_paths: AppPaths,
    cli_database_path: Path | None = None,
    config_database_path: Path | None = None,
) -> Path:
    """Resolve database path with CLI > environment > config > app-data order."""

    if cli_database_path is not None:
        return expand_user_path(cli_database_path)
    env_path = _path_from_env("KGFS_DATABASE_PATH")
    if env_path is not None:
        return env_path
    if config_database_path is not None:
        return expand_user_path(config_database_path)
    return app_paths.default_database_path
