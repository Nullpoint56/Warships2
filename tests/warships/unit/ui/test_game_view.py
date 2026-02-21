from __future__ import annotations

from dataclasses import replace

from engine.api.ui_primitives import ButtonStyle
from engine.ui_runtime.widgets import Button
from engine.ui_runtime.grid_layout import GridLayout
from tests.warships.unit.ui.helpers import FakeRenderer, make_ui_state
from warships.game.app.state_machine import AppState
from warships.game.ui.game_view import GameView


class _Render(FakeRenderer):
    def __init__(self) -> None:
        super().__init__()
        self.begun = 0
        self.ended = 0
        self.window_fill = 0
        self.titles: list[str] = []

    def begin_frame(self) -> None:
        self.begun += 1

    def end_frame(self) -> None:
        self.ended += 1

    def fill_window(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        self.window_fill += 1

    def set_title(self, title: str) -> None:
        self.titles.append(title)


def test_game_view_render_main_menu() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    labels = view.render(ui, debug_ui=False, debug_labels_state=[])
    assert renderer.begun == 1 and renderer.ended == 1 and renderer.window_fill == 1
    assert labels


def test_game_view_skips_new_game_custom_buttons_in_overlay() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.NEW_GAME_SETUP, new_game_visible_presets=["a"])
    labels = view.render(ui, debug_ui=False, debug_labels_state=[])
    assert renderer.begun == 1 and renderer.ended == 1
    assert isinstance(labels, list)


def test_game_view_build_snapshot_contains_scalar_render_payloads() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)

    snapshot, _labels = view.build_snapshot(
        frame_index=7,
        ui=ui,
        debug_ui=False,
        debug_labels_state=[],
    )

    assert snapshot.frame_index == 7
    assert snapshot.passes
    for render_pass in snapshot.passes:
        for command in render_pass.commands:
            assert len(command.transform.values) == 16
            for key, value in command.data:
                assert isinstance(key, str)
                assert value is None or isinstance(value, (bool, int, float, str))


def test_game_view_snapshot_recorder_tolerates_new_style_rect_kwargs(monkeypatch) -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)

    def _draw_rounded_rect_with_extra(renderer_obj, *, key, x, y, w, h, radius, color, z) -> None:
        renderer_obj.add_style_rect(
            style_kind="rounded_rect",
            key=key,
            x=x,
            y=y,
            w=w,
            h=h,
            color=color,
            z=z,
            radius=radius,
            edge_softness=0.25,
        )

    monkeypatch.setattr(
        "warships.game.ui.game_view.draw_rounded_rect",
        _draw_rounded_rect_with_extra,
    )

    snapshot, _labels = view.build_snapshot(
        frame_index=8,
        ui=ui,
        debug_ui=False,
        debug_labels_state=[],
    )

    assert snapshot.passes


def test_game_view_fits_button_text_to_button_bounds() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    ui = replace(
        ui,
        buttons=[Button("this_is_a_very_long_button_label_for_testing", 10.0, 10.0, 90.0, 28.0)],
    )

    view.render(ui, debug_ui=False, debug_labels_state=[])

    text_calls = [kwargs for _args, kwargs in renderer.texts if kwargs.get("key", "").startswith("button:text:")]
    assert text_calls
    text_payload = text_calls[0]
    assert isinstance(text_payload.get("text"), str)
    assert len(text_payload["text"]) < len("this_is_a_very_long_button_label_for_testing")
    assert float(text_payload.get("font_size", 99.0)) <= 17.0


def test_game_view_skips_overlay_render_for_preset_row_action_buttons() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.PRESET_MANAGE)
    ui = replace(
        ui,
        buttons=[Button("preset_delete:Alpha", 10.0, 10.0, 120.0, 40.0)],
    )

    view.render(ui, debug_ui=False, debug_labels_state=[])

    bg_rects = [
        args
        for args, _kwargs in renderer.rects
        if args and str(args[0]).startswith("button:bg:preset_delete:Alpha")
    ]
    assert not bg_rects


def test_game_view_allows_button_style_overrides() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    ui = replace(
        ui,
        buttons=[
            Button(
                "custom",
                10.0,
                10.0,
                120.0,
                40.0,
                style={
                    "bg_color": "#00ff00",
                    "border_color": "#ff00ff",
                    "highlight_color": "#ffffff22",
                    "text_color": "#111111",
                    "radius": 10.0,
                },
            )
        ],
    )

    view.render(ui, debug_ui=False, debug_labels_state=[])

    bg_rects = [args for args, _kwargs in renderer.rects if args and str(args[0]).startswith("button:bg:custom")]
    text_calls = [kwargs for _args, kwargs in renderer.texts if kwargs.get("key") == "button:text:custom"]
    assert bg_rects
    assert any(str(args[5]) == "#00ff00" for args in bg_rects)
    assert text_calls
    assert str(text_calls[0].get("color")) == "#111111"


def test_game_view_allows_typed_button_style_with_shadow_and_no_gloss() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    ui = replace(
        ui,
        buttons=[
            Button(
                "custom2",
                10.0,
                10.0,
                120.0,
                40.0,
                style=ButtonStyle(
                    bg_color="#224466",
                    border_color="#335577",
                    text_color="#ffffff",
                    glossy=False,
                    shadow_enabled=True,
                    shadow_color="#00000044",
                    shadow_layers=1,
                    shadow_spread=2.0,
                ),
            )
        ],
    )

    view.render(ui, debug_ui=False, debug_labels_state=[])

    shadow_rects = [
        args for args, _kwargs in renderer.rects if args and str(args[0]).startswith("button:shadow:custom2")
    ]
    highlight_rects = [
        args for args, _kwargs in renderer.rects if args and str(args[0]).startswith("button:highlight:custom2")
    ]
    assert shadow_rects
    assert not highlight_rects


def test_game_view_default_buttons_do_not_render_shadow_layer() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    ui = replace(ui, buttons=[Button("new_game", 10.0, 10.0, 120.0, 40.0)])

    view.render(ui, debug_ui=False, debug_labels_state=[])

    shadow_rects = [
        args for args, _kwargs in renderer.rects if args and str(args[0]).startswith("button:shadow:new_game")
    ]
    assert not shadow_rects
