from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.views.common import draw_preset_preview, is_new_game_custom_button, truncate

from tests.warships.unit.ui.helpers import FakeRenderer


def test_truncate_behavior() -> None:
    assert truncate("abc", 5) == "abc"
    assert truncate("abcdef", 3) == "abc"
    assert truncate("abcdef", 5) == "ab..."


def test_draw_preset_preview_and_custom_button_detection() -> None:
    renderer = FakeRenderer()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)]
    draw_preset_preview(renderer=renderer, key_prefix="x", placements=placements, x=10, y=10, cell=2)
    assert renderer.rects  # background + ship cells
    assert is_new_game_custom_button("new_game_toggle_difficulty")
    assert is_new_game_custom_button("new_game_select_preset:alpha")
    assert not is_new_game_custom_button("start_game")
