from engine.runtime.action_dispatch import ActionDispatcher


def test_action_dispatch_direct_and_prefix_handlers() -> None:
    called: list[tuple[str, str | None]] = []

    def on_direct() -> bool:
        called.append(("direct", None))
        return True

    def on_prefix(value: str) -> bool:
        called.append(("prefix", value))
        return True

    dispatcher = ActionDispatcher(
        direct_handlers={"new_game": on_direct},
        prefixed_handlers=(("preset_edit:", on_prefix),),
    )
    assert dispatcher.dispatch("new_game") is True
    assert dispatcher.dispatch("preset_edit:alpha") is True
    assert dispatcher.dispatch("unknown") is None
    assert called == [("direct", None), ("prefix", "alpha")]
