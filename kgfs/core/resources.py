"""Runtime resource lookup for source and PyInstaller packaged builds."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return true when KGFS is running from a PyInstaller bundle."""

    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Return the root directory that contains bundled resource files."""

    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass).resolve() if meipass else Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def executable_path() -> Path:
    """Return the active executable path for doctor diagnostics."""

    return Path(sys.executable if is_frozen() else sys.argv[0]).resolve()


def resource_path(*parts: str | Path) -> Path:
    """Return a resource path in source checkouts and frozen bundles."""

    return bundle_root().joinpath(*(Path(part) for part in parts))


def web_templates_dir() -> Path:
    return resource_path("kgfs", "web", "templates")


def web_static_dir() -> Path:
    return resource_path("kgfs", "web", "static")
