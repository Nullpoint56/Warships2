"""Frontend adapter contracts for application orchestration."""

from __future__ import annotations

from typing import Protocol


class FrontendWindow(Protocol):
    """Minimal UI window contract expected by app loop."""

    def show_fullscreen(self) -> None:
        """Show UI in fullscreen mode."""

    def show_maximized(self) -> None:
        """Show UI maximized or borderless."""

    def show_windowed(self, width: int, height: int) -> None:
        """Show UI in a normal window."""

    def sync_ui(self) -> None:
        """Synchronize rendered UI with latest controller state."""

