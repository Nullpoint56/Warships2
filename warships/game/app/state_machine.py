"""Application state transitions for menus, placement, and battle."""

from enum import Enum, auto


class AppState(Enum):
    """Top-level application states."""

    MAIN_MENU = auto()
    NEW_GAME_SETUP = auto()
    PRESET_MANAGE = auto()
    PLACEMENT_EDIT = auto()
    BATTLE = auto()
    RESULT = auto()
