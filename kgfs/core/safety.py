"""Indexing safety checks for risky folder roots."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


class RiskyRootError(ValueError):
    """Raised when indexing is asked to scan a risky root without override."""


SYSTEM_ROOTS = {
    "/applications",
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/library",
    "/private",
    "/proc",
    "/root",
    "/sbin",
    "/system",
    "/usr",
    "/var",
}

WINDOWS_SYSTEM_ROOT_SUFFIXES = {
    "windows",
    "program files",
    "program files (x86)",
    "$recycle.bin",
    "system volume information",
}


def is_risky_index_root(path: str | Path, *, home: Path | None = None) -> bool:
    text = str(path).strip()
    if not text:
        return False

    expanded = Path(path).expanduser()
    if _is_filesystem_root(expanded):
        return True
    if _is_windows_drive_root(text):
        return True

    try:
        home_path = (home or Path.home()).expanduser()
        if expanded == home_path:
            return True
    except RuntimeError:
        pass

    normalized = _normalized_path_text(text)
    if normalized in SYSTEM_ROOTS:
        return True
    if _is_windows_system_root(normalized):
        return True

    return False


def find_risky_index_roots(paths: Iterable[str | Path], *, home: Path | None = None) -> list[Path]:
    return [Path(path).expanduser() for path in paths if is_risky_index_root(path, home=home)]


def risk_warning(path: str | Path) -> str:
    if not is_risky_index_root(path):
        return ""
    return "Risky root; kgfs index refuses this folder unless --allow-risky-root is used"


def format_risky_roots(paths: Iterable[str | Path]) -> str:
    return "\n".join(f"- {Path(path).expanduser()}" for path in paths)


def _is_filesystem_root(path: Path) -> bool:
    return path.parent == path


def _is_windows_drive_root(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z]:[\\/]*", value.strip()) is not None


def _normalized_path_text(value: str) -> str:
    text = value.strip().replace("\\", "/")
    text = re.sub(r"/+", "/", text)
    if len(text) > 1:
        text = text.rstrip("/")
    return text.lower()


def _is_windows_system_root(normalized: str) -> bool:
    match = re.fullmatch(r"[a-z]:/(.+)", normalized)
    if not match:
        return False
    return match.group(1) in WINDOWS_SYSTEM_ROOT_SUFFIXES
