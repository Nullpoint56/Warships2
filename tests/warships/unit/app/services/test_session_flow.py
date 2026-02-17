from warships.game.app.services.session_flow import SessionFlowService
from warships.game.app.state_machine import AppState


def test_session_flow_transitions() -> None:
    manage = SessionFlowService.to_manage_presets(AppState.MAIN_MENU)
    assert manage is not None
    assert manage.state is AppState.PRESET_MANAGE
    assert manage.refresh_preset_rows

    new_game = SessionFlowService.to_new_game_setup(AppState.MAIN_MENU)
    assert new_game is not None
    assert new_game.state is AppState.NEW_GAME_SETUP
    assert new_game.enter_new_game_setup

    create = SessionFlowService.to_create_preset(AppState.PRESET_MANAGE)
    assert create is not None
    assert create.state is AppState.PLACEMENT_EDIT
    assert create.reset_editor and create.clear_editing_preset_name

    main = SessionFlowService.to_main_menu(AppState.BATTLE)
    assert main is not None
    assert main.state is AppState.MAIN_MENU
    assert main.clear_session

    back = SessionFlowService.to_back_to_presets(AppState.RESULT)
    assert back is not None
    assert back.state is AppState.PRESET_MANAGE
    assert back.refresh_preset_rows
