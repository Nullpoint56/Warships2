from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent
from engine.runtime.framework_engine import EngineUIFramework
from engine.ui_runtime.grid_layout import GridLayout
from tests.engine.conftest import (
    Box,
    FakeApp,
    FakeButton,
    FakeInteractionPlan,
    FakeModalWidget,
    FakeRenderer,
)


def test_pointer_down_routes_to_button_click() -> None:
    app = FakeApp()
    app.set_plan(
        FakeInteractionPlan(
            buttons=(FakeButton("new_game", True, Box(0, 0, 50, 50)),),
        )
    )
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    changed = framework.handle_pointer_event(PointerEvent("pointer_down", 10, 10, 1))
    assert changed
    assert app.calls[-1] == ("on_button", ("new_game",))


def test_pointer_down_routes_to_grid_click_when_target_present() -> None:
    app = FakeApp()
    app.set_plan(FakeInteractionPlan(grid_click_target="secondary"))
    layout = GridLayout(
        primary_origin_x=0, secondary_origin_x=100, origin_y=0, cell_size=10, grid_size=10
    )
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=layout)
    changed = framework.handle_pointer_event(PointerEvent("pointer_down", 115, 25, 1))
    assert changed
    assert app.calls[-1] == ("on_grid_click", ("secondary", 2, 1))


def test_pointer_down_modal_takes_precedence() -> None:
    app = FakeApp()
    app.set_modal(FakeModalWidget())
    app.set_plan(FakeInteractionPlan(buttons=(FakeButton("ignored", True, Box(0, 0, 100, 100)),)))
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    framework.sync_ui_state()
    changed = framework.handle_pointer_event(PointerEvent("pointer_down", 15, 15, 1))
    assert changed
    assert app.calls[-1] == ("on_button", ("prompt_confirm",))


def test_pointer_move_and_up_route_directly() -> None:
    app = FakeApp()
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    moved = framework.handle_pointer_event(PointerEvent("pointer_move", 1, 2, 0))
    released = framework.handle_pointer_event(PointerEvent("pointer_up", 3, 4, 1))
    assert moved and released
    assert app.calls[0] == ("on_pointer_move", (1.0, 2.0))
    assert app.calls[1] == ("on_pointer_release", (3.0, 4.0, 1))


def test_non_left_pointer_down_falls_back_to_on_pointer_down() -> None:
    app = FakeApp()
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    changed = framework.handle_pointer_event(PointerEvent("pointer_down", 10, 10, 2))
    assert changed
    assert app.calls[-1] == ("on_pointer_down", (10.0, 10.0, 2))


def test_key_routing_calls_controller_then_shortcut() -> None:
    app = FakeApp()
    app.on_key_result = False
    app.set_plan(FakeInteractionPlan(shortcut_buttons={"r": "randomize"}))
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    changed = framework.handle_key_event(KeyEvent("key_down", "R"))
    assert changed
    assert app.calls[0] == ("on_key", ("r",))
    assert app.calls[1] == ("on_button", ("randomize",))


def test_key_routing_stops_when_controller_handles() -> None:
    app = FakeApp()
    app.on_key_result = True
    app.set_plan(FakeInteractionPlan(shortcut_buttons={"r": "randomize"}))
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    changed = framework.handle_key_event(KeyEvent("key_down", "R"))
    assert changed
    assert app.calls == [("on_key", ("r",))]


def test_key_routing_ignores_unmapped_and_char_non_printable() -> None:
    app = FakeApp()
    app.set_plan(FakeInteractionPlan())
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    assert not framework.handle_key_event(KeyEvent("key_down", "F1"))
    assert not framework.handle_key_event(KeyEvent("char", "\n"))


def test_wheel_routes_only_inside_allowed_region() -> None:
    app = FakeApp()
    app.set_plan(FakeInteractionPlan(wheel_scroll_regions=(Box(0, 0, 100, 100),)))
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    changed_in = framework.handle_wheel_event(WheelEvent(50, 50, 1.0))
    changed_out = framework.handle_wheel_event(WheelEvent(200, 200, 1.0))
    assert changed_in
    assert not changed_out
    assert app.calls[-1] == ("on_wheel", (50, 50, 1.0))


def test_modal_char_routes_to_on_char() -> None:
    app = FakeApp()
    app.set_modal(FakeModalWidget())
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    framework.sync_ui_state()
    changed = framework.handle_key_event(KeyEvent("char", "x"))
    assert changed
    assert app.calls[-1] == ("on_char", ("x",))


def test_modal_key_swallow_without_action_returns_false() -> None:
    app = FakeApp()
    app.set_modal(FakeModalWidget())
    framework = EngineUIFramework(app=app, renderer=FakeRenderer(), layout=GridLayout())
    framework.sync_ui_state()
    changed = framework.handle_key_event(KeyEvent("key_down", "F1"))
    assert not changed
