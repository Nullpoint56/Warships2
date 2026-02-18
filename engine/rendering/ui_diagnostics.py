"""UI diagnostics collection and anomaly dumps for rendering pipeline debugging."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

_LOG = logging.getLogger("engine.rendering")


@dataclass(frozen=True, slots=True)
class UIDiagnosticsConfig:
    """Configuration for UI diagnostics collection and dumps."""

    ui_trace_enabled: bool
    resize_trace_enabled: bool
    sampling_n: int = 10
    max_frames: int = 300
    auto_dump_on_anomaly: bool = True
    dump_dir: str = "logs"
    dump_frame_count: int = 120


class UIDiagnostics:
    """Collect frame-level UI diagnostics and dump recent history on anomalies."""

    def __init__(self, config: UIDiagnosticsConfig) -> None:
        self._cfg = config
        self._frames: deque[dict[str, object]] = deque(maxlen=max(1, config.max_frames))
        self._pending_reasons: set[str] = set()
        self._pending_reason_events: list[dict[str, object]] = []
        self._latest_resize: dict[str, object] | None = None
        self._frame_seq = 0
        self._resize_seq = 0
        self._current: dict[str, object] | None = None
        self._last_button_rect: dict[str, tuple[int, int, float, float]] = {}
        self._dump_count = 0
        self._session_dump_path: Path | None = None
        self._latest_summary: dict[str, int] = {"revision": 0, "resize_seq": 0, "jitter_count": 0}

    def note_frame_reason(self, reason: str) -> None:
        if not self._cfg.ui_trace_enabled:
            return
        normalized = reason.strip()
        if normalized:
            self._pending_reasons.add(normalized)
            self._pending_reason_events.append({"reason": normalized, "ts": perf_counter()})

    def note_resize_event(
        self,
        *,
        event_size: tuple[float, float] | None,
        logical_size: tuple[float, float] | None,
        physical_size: tuple[int, int] | None,
        applied_size: tuple[int, int],
        viewport: tuple[float, float, float, float],
    ) -> None:
        if not self._cfg.resize_trace_enabled:
            return
        self._resize_seq += 1
        sx, sy, ox, oy = viewport
        payload: dict[str, object] = {
            "resize_seq": self._resize_seq,
            "applied_size": [applied_size[0], applied_size[1]],
            "viewport": {"sx": sx, "sy": sy, "ox": ox, "oy": oy},
        }
        if event_size is not None:
            payload["event_size"] = [event_size[0], event_size[1]]
        if logical_size is not None:
            payload["logical_size"] = [logical_size[0], logical_size[1]]
        if physical_size is not None:
            payload["physical_size"] = [physical_size[0], physical_size[1]]
        self._latest_resize = payload

    def begin_frame(self) -> None:
        if not self._cfg.ui_trace_enabled and not self._cfg.resize_trace_enabled:
            return
        self._frame_seq += 1
        self._current = {
            "frame_seq": self._frame_seq,
            "reasons": sorted(self._pending_reasons),
            "reason_events": list(self._pending_reason_events),
            "resize": self._latest_resize,
            "viewport": None,
            "buttons": {},
            "anomalies": [],
        }
        self._pending_reasons.clear()
        self._pending_reason_events.clear()

    def note_viewport(
        self,
        *,
        width: int,
        height: int,
        viewport_revision: int,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
    ) -> None:
        if self._current is None:
            return
        self._current["viewport"] = {
            "width": width,
            "height": height,
            "revision": viewport_revision,
            "sx": sx,
            "sy": sy,
            "ox": ox,
            "oy": oy,
        }

    def note_button_rect(
        self,
        button_id: str,
        *,
        x: float,
        y: float,
        w: float,
        h: float,
        tx: float,
        ty: float,
        tw: float,
        th: float,
    ) -> None:
        if self._current is None:
            return
        buttons = self._current["buttons"]
        if not isinstance(buttons, dict):
            return
        entry = buttons.setdefault(button_id, {})
        if isinstance(entry, dict):
            entry["source_rect"] = {"x": x, "y": y, "w": w, "h": h}
            entry["rect"] = {"x": tx, "y": ty, "w": tw, "h": th}

    def note_button_text(self, button_id: str, *, text_size: float) -> None:
        if self._current is None:
            return
        buttons = self._current["buttons"]
        if not isinstance(buttons, dict):
            return
        entry = buttons.setdefault(button_id, {})
        if isinstance(entry, dict):
            entry["text_size"] = text_size

    def end_frame(self) -> None:
        frame = self._current
        self._current = None
        if frame is None:
            return
        anomalies = self._detect_anomalies(frame)
        frame["anomalies"] = anomalies
        revision = 0
        if isinstance(frame.get("viewport"), dict):
            revision = int(frame["viewport"].get("revision", 0))
        jitter_count = sum(
            1 for item in anomalies if isinstance(item, str) and item.startswith("button_jitter:")
        )
        self._latest_summary = {
            "revision": revision,
            "resize_seq": self._resize_seq,
            "jitter_count": jitter_count,
        }
        self._frames.append(frame)
        frame_seq = int(frame.get("frame_seq", 0))
        if self._cfg.ui_trace_enabled and frame_seq % max(1, self._cfg.sampling_n) == 0:
            _LOG.debug("ui_diag frame=%d anomalies=%d", frame_seq, len(anomalies))
        if anomalies and self._cfg.auto_dump_on_anomaly:
            path = self.dump_recent_frames()
            if path is not None:
                _LOG.warning("ui_diag_anomaly_dumped file=%s anomalies=%s", path, anomalies)

    def dump_recent_frames(self) -> str | None:
        if not self._frames:
            return None
        path = self._resolve_session_dump_path()
        if path is None:
            return None
        keep = max(1, self._cfg.dump_frame_count)
        with path.open("a", encoding="utf-8") as out:
            for record in list(self._frames)[-keep:]:
                out.write(json.dumps(record, separators=(",", ":")))
                out.write("\n")
        return str(path)

    def recent_frames(self) -> list[dict[str, object]]:
        """Return collected frame diagnostics (oldest to newest)."""
        return list(self._frames)

    def latest_summary(self) -> dict[str, int]:
        """Return latest compact UI diagnostic summary for overlay display."""
        return dict(self._latest_summary)

    def _detect_anomalies(self, frame: dict[str, object]) -> list[str]:
        anomalies: list[str] = []
        viewport = frame.get("viewport")
        revision = -1
        if isinstance(viewport, dict):
            rev_value = viewport.get("revision")
            if isinstance(rev_value, int):
                revision = rev_value
        resize_seq = self._resize_seq
        resize = frame.get("resize")
        if isinstance(resize, dict):
            resize_value = resize.get("resize_seq")
            if isinstance(resize_value, int):
                resize_seq = resize_value
        buttons = frame.get("buttons")
        if not isinstance(buttons, dict) or not buttons:
            return anomalies

        ratios: list[float] = []
        for button_id, payload in buttons.items():
            if not isinstance(payload, dict):
                continue
            rect = payload.get("rect")
            text_size = payload.get("text_size")
            if isinstance(rect, dict):
                width = rect.get("w")
                height = rect.get("h")
                if isinstance(width, (float, int)) and isinstance(height, (float, int)):
                    prev = self._last_button_rect.get(str(button_id))
                    if prev is not None and prev[0] == revision and prev[1] == resize_seq:
                        if abs(prev[2] - float(width)) > 0.5 or abs(prev[3] - float(height)) > 0.5:
                            anomalies.append(f"button_jitter:{button_id}")
                    self._last_button_rect[str(button_id)] = (
                        revision,
                        resize_seq,
                        float(width),
                        float(height),
                    )
            if isinstance(rect, dict) and isinstance(text_size, (float, int)) and float(text_size) > 0.0:
                height = rect.get("h")
                if isinstance(height, (float, int)):
                    ratios.append(float(height) / float(text_size))

        if len(ratios) >= 2:
            spread = max(ratios) - min(ratios)
            if spread > 0.25:
                anomalies.append(f"button_ratio_spread:{spread:.3f}")
        return anomalies

    def _resolve_session_dump_path(self) -> Path | None:
        if self._session_dump_path is not None:
            return self._session_dump_path
        dump_root = Path(self._cfg.dump_dir)
        dump_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        self._dump_count += 1
        self._session_dump_path = dump_root / f"ui_diag_run_{stamp}_{self._dump_count:02d}.jsonl"
        return self._session_dump_path
