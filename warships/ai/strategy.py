"""AI strategy interface and selection utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod

from warships.core.models import Coord, ShotResult


class AIStrategy(ABC):
    """Interface for AI shot selection."""

    @abstractmethod
    def choose_shot(self) -> Coord:
        """Return next coordinate to fire."""

    @abstractmethod
    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        """Update strategy state with shot result."""
