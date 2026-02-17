from __future__ import annotations

from types import SimpleNamespace

from engine.api.game_module import HostFrameContext
from warships.game.app.engine_game_module import WarshipsGameModule


class _Framework:
    def sync_ui_state(self) -> None:
        return

    def handle_pointer_event(self, event) -> bool:
        _ = event
        return True

    def handle_key_event(self, event) -> bool:
        _ = event
        return True

    def handle_wheel_event(self, event) -> bool:
        _ = event
        return True


class _View:
    def render(self, ui, debug_ui: bool, labels: list[str]) -> list[str]:
        _ = (ui, debug_ui, labels)
        return labels


class _Controller:
    def __init__(self) -> None:
        self._ui = SimpleNamespace(is_closing=False)

    def ui_state(self):
        return self._ui


class _Host:
    def __init__(self) -> None:
        self.closed = False
        self.next_task_id = 1

    def close(self) -> None:
        self.closed = True

    def call_later(self, delay_seconds: float, callback) -> int:
        _ = delay_seconds
        task_id = self.next_task_id
        self.next_task_id += 1
        callback()
        return task_id

    def call_every(self, interval_seconds: float, callback) -> int:
        _ = (interval_seconds, callback)
        task_id = self.next_task_id
        self.next_task_id += 1
        return task_id

    def cancel_task(self, task_id: int) -> None:
        _ = task_id


def test_engine_module_smoke_lifecycle() -> None:
    module = WarshipsGameModule(
        controller=_Controller(), framework=_Framework(), view=_View(), debug_ui=False
    )
    host = _Host()
    module.on_start(host)
    assert module.on_pointer_event(object())
    assert module.on_key_event(object())
    assert module.on_wheel_event(object())
    module.on_frame(HostFrameContext(frame_index=0, delta_seconds=0.0, elapsed_seconds=0.0))
    assert not module.should_close()
    module.on_shutdown()
