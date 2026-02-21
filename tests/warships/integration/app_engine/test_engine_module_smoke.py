from __future__ import annotations

from types import SimpleNamespace

from engine.api.game_module import HostFrameContext
from engine.api.input_snapshot import InputSnapshot
from warships.game.app.engine_game_module import WarshipsGameModule


class _Framework:
    def sync_ui_state(self) -> None:
        return

    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        _ = snapshot
        return True


class _View:
    def render(self, ui, debug_ui: bool, labels: list[str]) -> list[str]:
        _ = (ui, debug_ui, labels)
        return labels

    def build_snapshot(self, *, frame_index: int, ui, debug_ui: bool, debug_labels_state: list[str]):
        _ = (frame_index, ui, debug_ui, debug_labels_state)
        from engine.api.render_snapshot import RenderSnapshot

        return RenderSnapshot(frame_index=frame_index), debug_labels_state


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
    assert module.on_input_snapshot(InputSnapshot(frame_index=0))
    module.simulate(HostFrameContext(frame_index=0, delta_seconds=0.0, elapsed_seconds=0.0))
    assert module.build_render_snapshot() is not None
    assert not module.should_close()
    module.on_shutdown()
