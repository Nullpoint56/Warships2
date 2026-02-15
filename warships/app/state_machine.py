"""Application state transitions for menus, placement, and battle."""

from enum import Enum, auto


class AppState(Enum):
    """Top-level application states."""

    BOOT = auto()
    MAIN_MENU = auto()
    PRESET_MANAGE = auto()
    PLACEMENT_EDIT = auto()
    PLACEMENT_LOAD = auto()
    BATTLE = auto()
    RESULT = auto()
    EXIT = auto()
