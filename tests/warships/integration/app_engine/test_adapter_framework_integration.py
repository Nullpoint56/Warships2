from __future__ import annotations

from engine.input.input_controller import PointerEvent, WheelEvent
from engine.runtime.framework_engine import EngineUIFramework
from engine.ui_runtime.grid_layout import GridLayout
from warships.game.app.events import ButtonPressed
from warships.game.app.engine_adapter import WarshipsAppAdapter
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


class _Renderer:
    @staticmethod
    def to_design_space(x: float, y: float) -> tuple[float, float]:
        return x, y


def test_framework_click_through_adapter_moves_to_new_game(tmp_path) -> None:
    from warships.game.app.controller import GameController
    import random

    controller = GameController(PresetService(PresetRepository(tmp_path)), random.Random(1))
    adapter = WarshipsAppAdapter(controller)
    framework = EngineUIFramework(app=adapter, renderer=_Renderer(), layout=GridLayout())

    ui = controller.ui_state()
    new_game_btn = next(button for button in ui.buttons if button.id == "new_game")
    x = new_game_btn.x + 1.0
    y = new_game_btn.y + 1.0
    changed = framework.handle_pointer_event(PointerEvent("pointer_down", x, y, 1))
    assert changed
    assert controller.ui_state().state.name == "NEW_GAME_SETUP"


def test_framework_wheel_routing_through_adapter(tmp_path, valid_fleet) -> None:
    from warships.game.app.controller import GameController
    import random
    from warships.game.ui.layout_metrics import PRESET_PANEL

    service = PresetService(PresetRepository(tmp_path))
    for idx in range(10):
        service.save_preset(f"p{idx}", valid_fleet)
    controller = GameController(service, random.Random(2))
    controller.handle_button(ButtonPressed("manage_presets"))
    adapter = WarshipsAppAdapter(controller)
    framework = EngineUIFramework(app=adapter, renderer=_Renderer(), layout=GridLayout())

    panel = PRESET_PANEL.panel_rect()
    before = controller.ui_state().preset_rows[0].name
    changed = framework.handle_wheel_event(WheelEvent(panel.x + 1, panel.y + 1, 1.0))
    after = controller.ui_state().preset_rows[0].name
    assert changed
    assert before != after
