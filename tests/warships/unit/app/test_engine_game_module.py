from __future__ import annotations

from types import SimpleNamespace

from engine.api.game_module import HostFrameContext
from engine.api.input_snapshot import InputSnapshot
from engine.api.render_snapshot import RenderSnapshot
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

    def handle_input_snapshot(self, snapshot) -> bool:
        _ = snapshot
        self.calls.append("snapshot")
        return True


class _View:
    def __init__(self) -> None:
        self.calls = 0

    def render(self, ui, debug_ui: bool, labels: list[str]) -> list[str]:
        _ = (ui, debug_ui, labels)
        self.calls += 1
        return ["next"]

    def build_snapshot(self, *, frame_index: int, ui, debug_ui: bool, debug_labels_state: list[str]):
        _ = (frame_index, ui, debug_ui, debug_labels_state)
        self.calls += 1
        return RenderSnapshot(frame_index=frame_index), ["next"]


class _Controller:
    def __init__(self, is_closing: bool = False) -> None:
        self._ui = SimpleNamespace(is_closing=is_closing)

    def ui_state(self):
        return self._ui


class _Host:
    def __init__(self) -> None:
        self.closed = 0
        self.cancelled: list[int] = []
        self.next_task_id = 1

    def close(self) -> None:
        self.closed += 1

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
        self.cancelled.append(task_id)


def test_game_module_forwards_input_events() -> None:
    module = WarshipsGameModule(
        controller=_Controller(), framework=_Framework(), view=_View(), debug_ui=False
    )
    assert module.on_pointer_event(object())
    assert module.on_key_event(object())
    assert module.on_wheel_event(object())
    assert module.on_input_snapshot(InputSnapshot(frame_index=0))


def test_game_module_frame_and_close_lifecycle() -> None:
    framework = _Framework()
    view = _View()
    host = _Host()
    module = WarshipsGameModule(
        controller=_Controller(is_closing=True), framework=framework, view=view, debug_ui=False
    )
    module.on_start(host)
    module.on_frame(HostFrameContext(frame_index=0, delta_seconds=0.0, elapsed_seconds=0.0))
    snapshot = module.build_render_snapshot()
    assert framework.synced == 1
    assert view.calls == 1
    assert snapshot is not None
    assert host.closed == 1
    assert not module.should_close()
