"""Frontend adapter contracts for application orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
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


@dataclass(frozen=True, slots=True)
class FrontendBundle:
    """Resolved frontend runtime artifacts."""

    window: FrontendWindow
    run_event_loop: Callable[[], None]
