from tests.warships.unit.ui.helpers import FakeRenderer
from warships.game.app.state_machine import AppState
from warships.game.core.models import Orientation, ShipType
from warships.game.ui.views.status_overlay import draw_status_bar


def test_draw_status_bar_skips_main_menu() -> None:
    renderer = FakeRenderer()
    draw_status_bar(
        renderer=renderer,
        state=AppState.MAIN_MENU,
        status="x",
        placement_orientation=Orientation.HORIZONTAL,
        placements=[],
        ship_order=[],
    )
    assert not renderer.rects and not renderer.texts


def test_draw_status_bar_renders_for_placement_and_battle() -> None:
    renderer = FakeRenderer()
    draw_status_bar(
        renderer=renderer,
        state=AppState.PLACEMENT_EDIT,
        status="x",
        placement_orientation=Orientation.HORIZONTAL,
        placements=[],
        ship_order=[ShipType.DESTROYER],
    )
    assert renderer.rects and renderer.texts

    renderer2 = FakeRenderer()
    draw_status_bar(
        renderer=renderer2,
        state=AppState.BATTLE,
        status="x",
        placement_orientation=Orientation.HORIZONTAL,
        placements=[],
        ship_order=[],
    )
    assert renderer2.texts
