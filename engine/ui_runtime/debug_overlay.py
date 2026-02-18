"""Lightweight engine debug overlay renderer."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.render import RenderAPI
from engine.runtime.metrics import MetricsSnapshot


@dataclass(frozen=True, slots=True)
class DebugOverlay:
    """Render a small metrics overlay using RenderAPI primitives."""

    key_prefix: str = "debug:overlay"
    x: float = 2.0
    y: float = 2.0
    line_height: float = 9.0
    font_size: float = 6.0
    z_text: float = 5001.0

    def draw(self, renderer: RenderAPI, snapshot: MetricsSnapshot) -> None:
        """Draw overlay for the current metrics snapshot."""
        lines = self._format_lines(snapshot)
        text_x, text_y = renderer.to_design_space(self.x, self.y)
        for idx, line in enumerate(lines):
            renderer.add_text(
                f"{self.key_prefix}:line:{idx}",
                line,
                text_x,
                text_y + idx * self.line_height,
                font_size=self.font_size,
                color="rgba(229,231,235,0.40)",
                anchor="top-left",
                z=self.z_text,
                static=False,
            )

    def _format_lines(self, snapshot: MetricsSnapshot) -> list[str]:
        last = snapshot.last_frame
        if last is None:
            return [
                "Diagnostics: waiting for first frame",
                "FPS=0.00",
                "FrameMs=0.00",
                "SchedulerQ=0",
                "Events=0",
                "1) -",
                "2) -",
                "3) -",
            ]
        lines = [
            f"Frame {last.frame_index}",
            f"FPS={snapshot.rolling_fps:.2f}",
            f"FrameMs={last.dt_ms:.2f}",
            f"SchedulerQ={last.scheduler_queue_size}",
            f"Events={last.event_publish_count}",
        ]
        top = snapshot.top_systems_last_frame
        for idx in range(3):
            if idx < len(top):
                system_id, elapsed_ms = top[idx]
                lines.append(f"{idx + 1}) {system_id}: {elapsed_ms:.2f} ms")
            else:
                lines.append(f"{idx + 1}) -")
        return lines
