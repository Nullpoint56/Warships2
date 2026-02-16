from __future__ import annotations

from types import SimpleNamespace

from engine.api.game_module import HostFrameContext
from warships.game.app.engine_game_module import WarshipsGameModule


class _Framework:
    def __init__(self) -> None:
        self.synced = 0
        self.calls: list[str] = []

    def sync_ui_state(self) -> None:
        self.synced += 1

    def handle_pointer_event(self, event) -> bool:
        _ = event
        self.calls.append("pointer")
        return True

    def handle_key_event(self, event) -> bool:
        _ = event
        self.calls.append("key")
        return True

    def handle_wheel_event(self, event) -> bool:
        _ = event
        self.calls.append("wheel")
        return True


class _View:
    def __init__(self) -> None:
        self.calls = 0

    def render(self, ui, debug_ui: bool, labels: list[str]) -> list[str]:
        _ = (ui, debug_ui, labels)
        self.calls += 1
        return ["next"]


class _Controller:
    def __init__(self, is_closing: bool = False) -> None:
        self._ui = SimpleNamespace(is_closing=is_closing)

    def ui_state(self):
        return self._ui


class _Host:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def test_game_module_forwards_input_events() -> None:
    module = WarshipsGameModule(
        controller=_Controller(), framework=_Framework(), view=_View(), debug_ui=False
    )
    assert module.on_pointer_event(object())
    assert module.on_key_event(object())
    assert module.on_wheel_event(object())


def test_game_module_frame_and_close_lifecycle() -> None:
    framework = _Framework()
    view = _View()
    host = _Host()
    module = WarshipsGameModule(
        controller=_Controller(is_closing=True), framework=framework, view=view, debug_ui=False
    )
    module.on_start(host)
    module.on_frame(HostFrameContext(frame_index=0))
    assert framework.synced == 1
    assert view.calls == 1
    assert host.closed == 1
    assert module.should_close()
