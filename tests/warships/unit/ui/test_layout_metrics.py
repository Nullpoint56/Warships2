from warships.game.ui.layout_metrics import (
    NEW_GAME_SETUP,
    PLACEMENT_PANEL,
    PRESET_PANEL,
    PROMPT,
    content_rect,
    root_rect,
    status_rect,
    top_bar_rect,
)


def test_root_and_sections_have_positive_dimensions() -> None:
    for rect in (root_rect(), top_bar_rect(), content_rect(), status_rect()):
        assert rect.w > 0 and rect.h > 0


def test_panel_and_row_rects_are_inside_expected_space() -> None:
    panel = PLACEMENT_PANEL.panel_rect()
    row = PLACEMENT_PANEL.row_rect(0)
    assert panel.contains(row.x + 1, row.y + 1)

    p_panel = PRESET_PANEL.panel_rect()
    p_row = PRESET_PANEL.row_rect(0)
    assert p_panel.contains(p_row.x + 1, p_row.y + 1)


def test_new_game_and_prompt_layout_helpers() -> None:
    list_rect = NEW_GAME_SETUP.preset_list_rect()
    row_rect = NEW_GAME_SETUP.preset_row_rect(0)
    assert list_rect.contains(row_rect.x + 1, row_rect.y + 1)
    assert NEW_GAME_SETUP.visible_row_capacity() >= 1
    assert PRESET_PANEL.visible_row_capacity() >= 1
    assert PROMPT.overlay_rect().contains(PROMPT.panel_rect().x, PROMPT.panel_rect().y)
