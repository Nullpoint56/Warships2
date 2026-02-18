"""Lightweight engine debug overlay renderer."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.render import RenderAPI
from engine.runtime.metrics import MetricsSnapshot


@dataclass(frozen=True, slots=True)
class DebugOverlay:
    """Render a small metrics overlay using RenderAPI primitives."""

    key_prefix: str = "debug:overlay"
    x: float = 12.0
    y: float = 12.0
    line_height: float = 18.0
    font_size: float = 15.0
    z_bg: float = 5000.0
    z_text: float = 5001.0

    def draw(self, renderer: RenderAPI, snapshot: MetricsSnapshot) -> None:
        """Draw overlay for the current metrics snapshot."""
        lines = self._format_lines(snapshot)
        width = 440.0
        height = 12.0 + len(lines) * self.line_height
        renderer.add_rect(
            f"{self.key_prefix}:bg",
            self.x,
            self.y,
            width,
            height,
            "#111827",
            z=self.z_bg,
            static=False,
        )
        text_x = self.x + 10.0
        text_y = self.y + 8.0
        for idx, line in enumerate(lines):
            renderer.add_text(
                f"{self.key_prefix}:line:{idx}",
                line,
                text_x,
                text_y + idx * self.line_height,
                font_size=self.font_size,
                color="#e5e7eb",
                anchor="top-left",
                z=self.z_text,
                static=False,
            )

    def _format_lines(self, snapshot: MetricsSnapshot) -> list[str]:
        last = snapshot.last_frame
        if last is None:
            return [
                "Diagnostics: waiting for first frame",
                "FPS: 0.00 | Frame: 0.00 ms",
                "Scheduler: 0 | Events: 0",
                "1) -",
                "2) -",
                "3) -",
            ]
        lines = [
            f"Frame {last.frame_index}",
            f"FPS: {snapshot.rolling_fps:.2f} | Frame: {last.dt_ms:.2f} ms",
            f"Scheduler: {last.scheduler_queue_size} | Events: {last.event_publish_count}",
        ]
        top = snapshot.top_systems_last_frame
        for idx in range(3):
            if idx < len(top):
                system_id, elapsed_ms = top[idx]
                lines.append(f"{idx + 1}) {system_id}: {elapsed_ms:.2f} ms")
            else:
                lines.append(f"{idx + 1}) -")
        return lines
