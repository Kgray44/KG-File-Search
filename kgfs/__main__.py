"""Executable module entry point for `python -m kgfs` and PyInstaller."""

from __future__ import annotations

from kgfs.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
