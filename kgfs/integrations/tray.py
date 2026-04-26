"""Tray/menu-bar scaffold export."""

from __future__ import annotations

from pathlib import Path


def scaffold_tray(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    readme = output / "README.md"
    stub = output / "kgfs_tray_stub.py"
    readme.write_text(
        "# KGFS Tray/Menu-Bar Scaffold\n\nThis scaffold does not install a daemon or autostart entry. Future optional tray support can use `pystray` from the `tray` extra.\n",
        encoding="utf-8",
    )
    stub.write_text(
        '"""Optional KGFS tray scaffold. Install with python -m pip install -e ".[tray]" before experimenting."""\n',
        encoding="utf-8",
    )
    return [readme, stub]
