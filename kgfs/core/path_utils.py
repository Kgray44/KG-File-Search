"""Path helpers that avoid platform-specific branching."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def expand_user_path(value: Any, *, home: Path | None = None) -> Path:
    """Expand env vars and `~` paths, accepting `/` or `\\` after `~`.

    `Path.expanduser()` handles the current host well, but `~\\Documents` is
    only treated as a home-relative path on Windows. KGFS accepts that shape on
    any host so config files stay portable.
    """

    raw = _expand_environment_variables(str(value))
    if raw == "~":
        return home or Path.home()
    if raw.startswith("~/") or raw.startswith("~\\"):
        relative_text = raw[2:]
        relative_parts = [part for part in re.split(r"[\\/]+", relative_text) if part]
        return (home or Path.home()).joinpath(*relative_parts)
    return Path(raw).expanduser()


def _expand_environment_variables(value: str) -> str:
    expanded = os.path.expandvars(value)

    def replace_windows_var(match: re.Match[str]) -> str:
        name = match.group(1)
        return os.environ.get(name, match.group(0))

    return re.sub(r"%([^%]+)%", replace_windows_var, expanded)
