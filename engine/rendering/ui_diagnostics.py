"""UI diagnostics collection and anomaly dumps for rendering pipeline debugging."""

from __future__ import annotations

import json
import logging
import math
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from time import perf_counter

_LOG = logging.getLogger("engine.rendering")


@dataclass(frozen=True, slots=True)
class UIDiagnosticsConfig:
    """Configuration for UI diagnostics collection and raw dumps."""

    ui_trace_enabled: bool
    resize_trace_enabled: bool
    sampling_n: int = 10
    max_frames: int = 300
    auto_dump_on_anomaly: bool = True
    dump_dir: str = "logs"
    dump_frame_count: int = 120
    primitive_trace_enabled: bool = True
    trace_key_prefixes: tuple[str, ...] = ()
    log_every_frame: bool = False


class UIDiagnostics:
    """Collect frame-level UI diagnostics and optionally stream raw frame dumps."""

    def __init__(self, config: UIDiagnosticsConfig) -> None:
        self._cfg = config
        self._frames: deque[dict[str, object]] = deque(maxlen=max(1, config.max_frames))
        self._pending_reasons: set[str] = set()
        self._pending_reason_events: list[dict[str, object]] = []
        self._latest_resize: dict[str, object] | None = None
        self._frame_seq = 0
        self._resize_seq = 0
        self._current: dict[str, object] | None = None
        self._dump_count = 0
        self._session_dump_path: Path | None = None
        self._latest_summary: dict[str, int] = {
            "revision": 0,
            "resize_seq": 0,
            "anomaly_count": 0,
            "jitter_count": 0,
        }
        self._primitive_seq = 0

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
            "ts_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "frame_seq": self._frame_seq,
            "reasons": sorted(self._pending_reasons),
            "reason_events": list(self._pending_reason_events),
            "resize": self._latest_resize,
            "viewport": None,
            "buttons": {},
            "primitives": [],
            "retained_ops": [],
            "frame_state": [],
            "scopes": [],
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

    def note_primitive(
        self,
        *,
        primitive_type: str,
        key: str | None,
        source: tuple[float, float, float, float],
        transformed: tuple[float, float, float, float],
        z: float,
        viewport_revision: int,
    ) -> None:
        if self._current is None or not self._cfg.primitive_trace_enabled:
            return
        if key is not None and self._cfg.trace_key_prefixes:
            if not any(key.startswith(prefix) for prefix in self._cfg.trace_key_prefixes):
                return
        primitives = self._current.get("primitives")
        if not isinstance(primitives, list):
            return
        self._primitive_seq += 1
        sx, sy, sw, sh = source
        tx, ty, tw, th = transformed
        primitives.append(
            {
                "seq": self._primitive_seq,
                "type": primitive_type,
                "key": key,
                "source": {"x": sx, "y": sy, "w": sw, "h": sh},
                "transformed": {"x": tx, "y": ty, "w": tw, "h": th},
                "z": z,
                "viewport_revision": viewport_revision,
            }
        )

    def note_retained_op(
        self,
        *,
        primitive_type: str,
        key: str | None,
        action: str,
        viewport_revision: int,
        before: tuple[float, float, float, float] | None,
        after: tuple[float, float, float, float],
    ) -> None:
        if self._current is None:
            return
        retained_ops = self._current.get("retained_ops")
        if not isinstance(retained_ops, list):
            return
        payload: dict[str, object] = {
            "type": primitive_type,
            "key": key,
            "action": action,
            "viewport_revision": viewport_revision,
            "after": {"x": after[0], "y": after[1], "w": after[2], "h": after[3]},
        }
        if before is not None:
            payload["before"] = {"x": before[0], "y": before[1], "w": before[2], "h": before[3]}
        retained_ops.append(payload)

    def note_frame_state(self, *, stage: str, payload: dict[str, object]) -> None:
        if self._current is None:
            return
        frame_state = self._current.get("frame_state")
        if not isinstance(frame_state, list):
            return
        frame_state.append({"stage": stage, **payload})

    @contextmanager
    def scoped(self, name: str) -> Iterator[None]:
        """Collect timing for a named diagnostics scope in the current frame."""
        start = perf_counter()
        try:
            yield
        finally:
            current = self._current
            if current is not None:
                scopes = current.get("scopes")
                if isinstance(scopes, list):
                    scopes.append({"name": name, "duration_ms": (perf_counter() - start) * 1000.0})

    def scope_decorator(
        self, name: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Decorator helper for selectively tracing specific render/draw functions."""

        def _decorator(func: Callable[..., object]) -> Callable[..., object]:
            @wraps(func)
            def _wrapped(*args: object, **kwargs: object) -> object:
                with self.scoped(name):
                    return func(*args, **kwargs)

            return _wrapped

        return _decorator

    def end_frame(self) -> None:
        frame = self._current
        self._current = None
        if frame is None:
            return
        frame["anomalies"] = []
        revision = 0
        if isinstance(frame.get("viewport"), dict):
            revision = int(frame["viewport"].get("revision", 0))
        self._latest_summary = {
            "revision": revision,
            "resize_seq": self._resize_seq,
            "anomaly_count": 0,
            "jitter_count": 0,
        }
        frame["render_packet"] = self._build_render_packet(frame)
        self._frames.append(frame)
        frame_seq = int(frame.get("frame_seq", 0))
        if self._cfg.ui_trace_enabled and (
            self._cfg.log_every_frame or frame_seq % max(1, self._cfg.sampling_n) == 0
        ):
            _LOG.debug("ui_diag frame=%d", frame_seq)
        if self._cfg.auto_dump_on_anomaly:
            self._append_frame_to_dump(frame)

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

    def _append_frame_to_dump(self, frame: dict[str, object]) -> None:
        path = self._resolve_session_dump_path()
        if path is None:
            return
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(frame, separators=(",", ":")))
            out.write("\n")

    def _resolve_session_dump_path(self) -> Path | None:
        if self._session_dump_path is not None:
            return self._session_dump_path
        dump_root = Path(self._cfg.dump_dir)
        dump_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        self._dump_count += 1
        self._session_dump_path = dump_root / f"ui_diag_run_{stamp}_{self._dump_count:02d}.jsonl"
        return self._session_dump_path

    @staticmethod
    def _build_render_packet(frame: dict[str, object]) -> dict[str, object]:
        packet: dict[str, object] = {
            "frame_seq": frame.get("frame_seq"),
            "ts_utc": frame.get("ts_utc"),
            "viewport": frame.get("viewport"),
            "resize": frame.get("resize"),
            "reasons": frame.get("reasons"),
        }
        primitives = frame.get("primitives")
        keyed: dict[str, dict[str, object]] = {}
        min_x = math.inf
        min_y = math.inf
        max_x = -math.inf
        max_y = -math.inf
        count = 0
        if isinstance(primitives, list):
            for item in primitives:
                if not isinstance(item, dict):
                    continue
                transformed = item.get("transformed")
                if not isinstance(transformed, dict):
                    continue
                x = transformed.get("x")
                y = transformed.get("y")
                w = transformed.get("w")
                h = transformed.get("h")
                if not all(isinstance(v, (int, float)) for v in (x, y, w, h)):
                    continue
                xf = float(x)
                yf = float(y)
                wf = float(w)
                hf = float(h)
                if not all(math.isfinite(v) for v in (xf, yf, wf, hf)):
                    continue
                min_x = min(min_x, xf)
                min_y = min(min_y, yf)
                max_x = max(max_x, xf + wf)
                max_y = max(max_y, yf + hf)
                count += 1
                key = item.get("key")
                if isinstance(key, str) and key:
                    keyed[key] = {
                        "type": item.get("type"),
                        "x": xf,
                        "y": yf,
                        "w": wf,
                        "h": hf,
                        "z": item.get("z"),
                        "viewport_revision": item.get("viewport_revision"),
                    }

        packet["primitive_count"] = count
        packet["keyed_transforms"] = keyed
        if count > 0 and all(math.isfinite(v) for v in (min_x, min_y, max_x, max_y)):
            packet["scene_bounds"] = {
                "x": min_x,
                "y": min_y,
                "w": max(0.0, max_x - min_x),
                "h": max(0.0, max_y - min_y),
            }
        return packet
