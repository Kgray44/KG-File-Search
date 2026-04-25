"""Platform-specific file opening and path normalization helpers."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from kgfs.core.safety import risk_warning


def normalize_path(path: Path) -> tuple[Path, str]:
    """Return the original Path plus a stable lookup string.

    The original path object is preserved for display/opening. The normalized
    string is only for database uniqueness and lookup.
    """

    original = Path(path).expanduser()
    absolute = original if original.is_absolute() else Path.cwd() / original
    normalized = os.path.normpath(str(absolute))
    return original, normalized


def open_file(path: Path) -> None:
    """Open a file with the OS default application."""

    file_path = Path(path).expanduser()
    system = platform.system()
    if system == "Windows":
        os.startfile(str(file_path))  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.run(["open", str(file_path)], check=False)
    else:
        subprocess.run(["xdg-open", str(file_path)], check=False)


def reveal_file(path: Path) -> None:
    """Reveal a file in its containing folder when the OS supports it."""

    file_path = Path(path).expanduser()
    system = platform.system()
    reveal_target, can_select = _reveal_target(file_path)
    if system == "Windows":
        if can_select:
            subprocess.run(["explorer", f"/select,{reveal_target}"], check=False)
        else:
            subprocess.run(["explorer", str(reveal_target)], check=False)
    elif system == "Darwin":
        if can_select:
            subprocess.run(["open", "-R", str(reveal_target)], check=False)
        else:
            subprocess.run(["open", str(reveal_target)], check=False)
    else:
        subprocess.run(["xdg-open", str(reveal_target)], check=False)


def _reveal_target(file_path: Path) -> tuple[Path, bool]:
    if file_path.exists():
        if file_path.is_file():
            return file_path, True
        return file_path, False
    parent = file_path.parent
    if parent == file_path:
        return Path.cwd(), False
    return parent, False


def platform_diagnostics() -> dict[str, str]:
    """Return platform-specific behavior labels for doctor output."""

    system = platform.system()
    if system == "Windows":
        open_strategy = "os.startfile"
        reveal_strategy = "Explorer /select with folder fallback"
    elif system == "Darwin":
        open_strategy = "open"
        reveal_strategy = "Finder open -R with folder fallback"
    else:
        open_strategy = "xdg-open"
        reveal_strategy = "xdg-open containing folder"

    return {
        "platform": f"{system} {platform.release()}".strip(),
        "path_separator": os.sep,
        "home_directory": str(Path.home()),
        "open_files": open_strategy,
        "reveal_files": reveal_strategy,
    }


def current_platform_name() -> str:
    """Return the OS name used in index metadata."""

    return platform.system()
