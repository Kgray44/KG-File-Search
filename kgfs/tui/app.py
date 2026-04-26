"""Optional Textual terminal UI launcher."""

from __future__ import annotations

from pathlib import Path


class TextualUnavailableError(RuntimeError):
    """Raised when the optional Textual dependency is not installed."""


def textual_available() -> bool:
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


def launch_tui(
    *,
    config_path: Path | None = None,
    database_path: Path | None = None,
    project_local: bool = False,
) -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Footer, Header, Input, Static
    except ImportError as exc:
        raise TextualUnavailableError(
            'Textual is not installed. Install with: python -m pip install -e ".[tui]"'
        ) from exc

    class KGFSApp(App):
        TITLE = "KGFS"

        def compose(self) -> ComposeResult:
            yield Header()
            yield Input(placeholder="Search local KGFS files...")
            yield Static("Use the CLI search command for full Phase 9 behavior while the TUI grows.")
            yield Footer()

    KGFSApp().run()
