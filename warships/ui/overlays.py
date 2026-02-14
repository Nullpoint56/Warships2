"""HUD/status overlays and button controls."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.state_machine import AppState


@dataclass(frozen=True, slots=True)
class Button:
    """Clickable rectangular button."""

    id: str
    x: float
    y: float
    w: float
    h: float
    visible: bool = True
    enabled: bool = True

    def contains(self, px: float, py: float) -> bool:
        """Return whether this button contains the point."""
        return self.visible and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


def buttons_for_state(
    state: AppState,
    placement_ready: bool,
    has_presets: bool,
) -> list[Button]:
    """Build buttons for the current app state."""
    base_y = 28.0
    gap = 16.0
    bw = 160.0
    bh = 50.0

    if state is AppState.MAIN_MENU:
        return [
            Button("new_game", 80.0, base_y, bw, bh),
            Button("load_preset", 80.0 + bw + gap, base_y, bw, bh, enabled=has_presets),
            Button("quit", 80.0 + 2 * (bw + gap), base_y, bw, bh),
        ]
    if state is AppState.PLACEMENT_EDIT:
        return [
            Button("rotate", 80.0, base_y, bw, bh),
            Button("randomize", 80.0 + bw + gap, base_y, bw, bh),
            Button("save_preset", 80.0 + 2 * (bw + gap), base_y, bw, bh),
            Button("start_battle", 80.0 + 3 * (bw + gap), base_y, bw, bh, enabled=placement_ready),
            Button("back_to_menu", 80.0 + 4 * (bw + gap), base_y, bw, bh),
        ]
    if state is AppState.BATTLE:
        return [Button("menu_from_battle", 80.0, base_y, bw, bh)]
    if state is AppState.RESULT:
        return [
            Button("play_again", 80.0, base_y, bw, bh),
            Button("quit", 80.0 + bw + gap, base_y, bw, bh),
        ]
    return []


def button_label(button_id: str) -> str:
    """Map button id to visible label."""
    labels = {
        "new_game": "New Game",
        "load_preset": "Load Preset",
        "quit": "Quit",
        "rotate": "Rotate",
        "randomize": "Randomize",
        "save_preset": "Save Preset",
        "start_battle": "Start Battle",
        "back_to_menu": "Back to Menu",
        "menu_from_battle": "Menu",
        "play_again": "Play Again",
    }
    return labels.get(button_id, button_id)
