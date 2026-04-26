"""Read-only integration status for KGFS launcher scaffolds."""

from __future__ import annotations

from dataclasses import dataclass

from kgfs.core.platform_utils import current_platform_name


@dataclass(frozen=True)
class IntegrationStatus:
    name: str
    supported: bool
    scaffold_available: bool
    installed: bool
    command: str
    notes: str


def get_integration_status() -> list[IntegrationStatus]:
    system = current_platform_name().lower()
    is_windows = system == "windows"
    is_macos = system == "darwin"
    return [
        IntegrationStatus("raycast", is_macos, True, False, "kgfs integrations raycast export", "Manual Raycast script command scaffold."),
        IntegrationStatus("alfred", is_macos, True, False, "kgfs integrations alfred export", "Manual Alfred workflow script scaffold."),
        IntegrationStatus("powertoys", is_windows, True, False, "kgfs integrations powertoys scaffold", "PowerToys Run plugin notes/template only."),
        IntegrationStatus("finder", is_macos, True, False, "kgfs integrations finder scaffold", "Finder Quick Action script and README."),
        IntegrationStatus("explorer", is_windows, True, False, "kgfs integrations explorer scaffold", "Explorer context-menu README and opt-in .reg template."),
        IntegrationStatus("tray", True, True, False, "kgfs tray scaffold", "Optional tray/menu-bar scaffold; no background daemon is installed."),
        IntegrationStatus("vscode", True, False, False, "planned", "VS Code extension path is documented as future work."),
    ]
