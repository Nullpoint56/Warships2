"""Typed UI command model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandType(str, Enum):
    NEW_GAME = "new_game"
    MANAGE_PRESETS = "manage_presets"
    QUIT = "quit"
    CREATE_PRESET = "create_preset"
    BACK_MAIN = "back_main"
    START_GAME = "start_game"
    PLAY_AGAIN = "play_again"
    BACK_TO_PRESETS = "back_to_presets"
    SAVE_PRESET = "save_preset"
    RANDOMIZE_EDITOR = "randomize"
    NEW_GAME_RANDOMIZE = "new_game_randomize"
    NEW_GAME_SET_DIFFICULTY = "new_game_set_difficulty"
    NEW_GAME_SELECT_PRESET = "new_game_select_preset"
    PRESET_EDIT = "preset_edit"
    PRESET_RENAME = "preset_rename"
    PRESET_DELETE = "preset_delete"
    PROMPT_CONFIRM_SAVE = "prompt_confirm_save"
    PROMPT_CONFIRM_RENAME = "prompt_confirm_rename"
    PROMPT_CONFIRM_OVERWRITE = "prompt_confirm_overwrite"
    PROMPT_CANCEL = "prompt_cancel"


@dataclass(frozen=True, slots=True)
class UICommand:
    kind: CommandType
    value: str | None = None
