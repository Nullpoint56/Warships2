from tests.warships.unit.ui.helpers import FakeRenderer, make_ui_state
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import PresetRowView
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.views.preset_manage_screen import draw_preset_manage


def test_draw_preset_manage_renders_rows_and_buttons() -> None:
    renderer = FakeRenderer()
    row = PresetRowView(
        name="alpha",
        placements=[ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)],
    )
    ui = make_ui_state(state=AppState.PRESET_MANAGE, preset_rows=[row])
    draw_preset_manage(renderer, ui)
    assert renderer.rects
    assert renderer.texts
