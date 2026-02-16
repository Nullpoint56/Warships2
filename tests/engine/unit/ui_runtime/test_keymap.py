from engine.ui_runtime.keymap import map_key_name


def test_keymap_known_mappings() -> None:
    assert map_key_name("Enter") == "enter"
    assert map_key_name("RETURN") == "enter"
    assert map_key_name("Esc") == "escape"
    assert map_key_name("backspace") == "backspace"


def test_keymap_alpha_and_unknown() -> None:
    assert map_key_name("R") == "r"
    assert map_key_name("x") == "x"
    assert map_key_name("F1") is None
