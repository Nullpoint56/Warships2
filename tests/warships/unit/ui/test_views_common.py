from tests.warships.unit.ui.helpers import FakeRenderer
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.ui.views.common import draw_preset_preview, is_new_game_custom_button, truncate
from engine.api.ui_primitives import fit_text_to_rect


def test_truncate_behavior() -> None:
    assert truncate("abc", 5) == "abc"
    assert truncate("abcdef", 3) == "abc"
    assert truncate("abcdef", 5) == "ab..."


def test_draw_preset_preview_and_custom_button_detection() -> None:
    renderer = FakeRenderer()
    placements = [ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)]
    draw_preset_preview(
        renderer=renderer, key_prefix="x", placements=placements, x=10, y=10, cell=2
    )
    assert renderer.rects  # background + ship cells
    assert is_new_game_custom_button("new_game_toggle_difficulty")
    assert is_new_game_custom_button("new_game_select_preset:alpha")
    assert not is_new_game_custom_button("start_game")


def test_fit_text_to_rect_clamps_by_parent_bounds() -> None:
    text, size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=180.0,
        rect_h=44.0,
        base_font_size=14.0,
    )
    assert len(text) < len("Generate Random Fleet")
    assert text.endswith("...")
    assert size <= 16.0
