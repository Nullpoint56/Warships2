from __future__ import annotations

from engine.runtime.metrics import FrameMetrics, MetricsSnapshot
from engine.ui_runtime.debug_overlay import DebugOverlay


class _FakeRenderer:
    def __init__(self) -> None:
        self.text_calls: list[tuple[str | None, str]] = []

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (x, y)

    def add_text(
        self,
        key,
        text,
        x,
        y,
        font_size=18.0,
        color="#ffffff",
        anchor="top-left",
        z=2.0,
        static=False,
    ) -> None:
        _ = (x, y, font_size, color, anchor, z, static)
        self.text_calls.append((key, text))


def test_debug_overlay_draws_expected_primitives() -> None:
    overlay = DebugOverlay()
    renderer = _FakeRenderer()
    snapshot = MetricsSnapshot(
        last_frame=FrameMetrics(
            frame_index=10,
            dt_ms=16.4,
            fps_rolling=60.9,
            scheduler_queue_size=2,
            event_publish_count=5,
            system_timings_ms={"a": 4.0, "b": 2.0},
        ),
        rolling_dt_ms=16.4,
        rolling_fps=60.9,
        top_systems_last_frame=[("a", 4.0), ("b", 2.0)],
    )

    overlay.draw(renderer, snapshot)

    assert len(renderer.text_calls) == 8
    assert renderer.text_calls[0][0] == "debug:overlay:line:0"
    assert renderer.text_calls[0][1] == "Frame 10"
    assert renderer.text_calls[1][1] == "FPS=60.90"
    assert renderer.text_calls[2][1] == "FrameMs=16.40"
    assert renderer.text_calls[3][1] == "SchedulerQ=2"
    assert renderer.text_calls[4][1] == "Events=5"
    assert renderer.text_calls[5][1] == "1) a: 4.00 ms"
    assert renderer.text_calls[6][1] == "2) b: 2.00 ms"
    assert renderer.text_calls[7][1] == "3) -"


def test_debug_overlay_handles_empty_snapshot() -> None:
    overlay = DebugOverlay()
    renderer = _FakeRenderer()
    snapshot = MetricsSnapshot(
        last_frame=None,
        rolling_dt_ms=0.0,
        rolling_fps=0.0,
        top_systems_last_frame=[],
    )

    overlay.draw(renderer, snapshot)

    assert len(renderer.text_calls) == 8
    assert renderer.text_calls[0][1].startswith("Diagnostics:")
    assert renderer.text_calls[4][1] == "Events=0"
    assert renderer.text_calls[5][1] == "1) -"


def test_debug_overlay_adds_ui_diagnostics_row_when_provided() -> None:
    overlay = DebugOverlay()
    renderer = _FakeRenderer()
    snapshot = MetricsSnapshot(
        last_frame=FrameMetrics(
            frame_index=1,
            dt_ms=16.0,
            fps_rolling=62.5,
            scheduler_queue_size=0,
            event_publish_count=0,
        ),
        rolling_dt_ms=16.0,
        rolling_fps=62.5,
        top_systems_last_frame=[],
    )

    overlay.draw(
        renderer,
        snapshot,
        ui_diagnostics={"revision": 7, "resize_seq": 42, "jitter_count": 3},
    )

    assert renderer.text_calls[-1][1] == "UI rev=7 resize=42 jitter=3"
