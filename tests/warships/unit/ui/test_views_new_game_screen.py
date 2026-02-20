from tests.warships.unit.ui.helpers import FakeRenderer, make_ui_state
from warships.game.app.state_machine import AppState
from warships.game.ui.views.new_game_screen import draw_new_game_setup


def test_draw_new_game_setup_renders_core_elements() -> None:
    renderer = FakeRenderer()
    ui = make_ui_state(
        state=AppState.NEW_GAME_SETUP,
        new_game_visible_presets=["alpha", "beta"],
    )
    draw_new_game_setup(renderer, ui)
    assert renderer.rects
    assert renderer.texts


def test_draw_new_game_setup_with_open_difficulty_dropdown() -> None:
    renderer = FakeRenderer()
    ui = make_ui_state(
        state=AppState.NEW_GAME_SETUP,
        new_game_visible_presets=["alpha"],
        new_game_difficulty_open=True,
    )
    draw_new_game_setup(renderer, ui)
    assert any(
        "newgame:diff:opt:bg:" in (args[0] if args else "") for args, _ in renderer.rects if args
    )


def test_draw_new_game_setup_random_button_text_is_fitted() -> None:
    renderer = FakeRenderer()
    ui = make_ui_state(
        state=AppState.NEW_GAME_SETUP,
        new_game_visible_presets=["alpha"],
    )

    draw_new_game_setup(renderer, ui)

    for _args, kwargs in renderer.texts:
        if kwargs.get("key") == "newgame:random:text":
            assert kwargs.get("text", "").endswith("...")
            assert float(kwargs.get("font_size", 99.0)) <= 16.0
            break
    else:
        raise AssertionError("newgame:random:text was not rendered")
