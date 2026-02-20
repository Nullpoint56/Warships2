"""Engine-hosted runtime shell for game module execution."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import InputSnapshot
from engine.api.render import RenderAPI
from engine.diagnostics import (
    CrashBundleWriter,
    DiagnosticHub,
    DiagnosticsMetricsStore,
    DiagnosticsProfiler,
    ReplayRecorder,
    emit_frame_metrics,
    load_diagnostics_config,
    resolve_crash_bundle_dir,
)
from engine.runtime.debug_config import enabled_metrics, enabled_overlay, load_debug_config
from engine.runtime.diagnostics_http import DiagnosticsHttpServer
from engine.runtime.metrics import MetricsSnapshot, create_metrics_collector
from engine.runtime.profiling import FrameProfiler
from engine.runtime.scheduler import Scheduler
from engine.runtime.time import FrameClock
from engine.ui_runtime.debug_overlay import DebugOverlay

_LOG = logging.getLogger("engine.runtime")
_PROFILE_LOG = logging.getLogger("engine.profiling")
_OVERLAY_TOGGLE_KEY = "f3"


@dataclass(frozen=True, slots=True)
class EngineHostConfig:
    """Host runtime configuration."""

    window_mode: str = "windowed"
    width: int = 1280
    height: int = 800


class EngineHost(HostControl):
    """Lifecycle shell for engine-hosted runtime migration."""

    def __init__(
        self,
        module: GameModule,
        config: EngineHostConfig | None = None,
        render_api: RenderAPI | None = None,
    ) -> None:
        self._module = module
        self._config = config or EngineHostConfig()
        self._frame_index = 0
        self._closed = False
        self._started = False
        self._clock = FrameClock()
        self._scheduler = Scheduler()
        self._render_api = render_api
        cfg = load_debug_config()
        diag_cfg = load_diagnostics_config()
        self._diag_cfg = diag_cfg
        self._debug_overlay = DebugOverlay() if enabled_overlay() else None
        self._debug_overlay_visible = False
        self._metrics_collector = create_metrics_collector(
            enabled=enabled_metrics() or cfg.profiling_enabled
        )
        self._frame_profiler = FrameProfiler(
            enabled=cfg.profiling_enabled or diag_cfg.profile_mode in {"light", "timeline_sample"},
            sampling_n=(
                diag_cfg.profile_sampling_n
                if diag_cfg.profile_mode in {"light", "timeline_sample"}
                else cfg.profiling_sampling_n
            ),
        )
        self._diagnostics_hub = DiagnosticHub(
            capacity=diag_cfg.buffer_capacity,
            enabled=diag_cfg.enabled,
        )
        self._diagnostics_metrics = DiagnosticsMetricsStore()
        self._diagnostics_subscriber_token = self._diagnostics_hub.subscribe(
            self._diagnostics_metrics.ingest
        )
        if self._render_api is not None:
            bind_hub = getattr(self._render_api, "set_diagnostics_hub", None)
            if callable(bind_hub):
                bind_hub(self._diagnostics_hub)
        self._crash_bundle_writer = CrashBundleWriter(
            enabled=diag_cfg.crash_bundle_enabled,
            output_dir=resolve_crash_bundle_dir(diag_cfg),
            recent_events_limit=diag_cfg.crash_recent_events_limit,
        )
        self._diagnostics_profiler = DiagnosticsProfiler(
            mode=diag_cfg.profile_mode,
            sampling_n=diag_cfg.profile_sampling_n,
            span_capacity=diag_cfg.profile_span_capacity,
            hub=self._diagnostics_hub,
        )
        self._replay_recorder = ReplayRecorder(
            enabled=diag_cfg.replay_capture,
            seed=_resolve_replay_seed(),
            build=self._runtime_metadata(),
            hash_interval=diag_cfg.replay_hash_interval,
            hub=self._diagnostics_hub,
        )
        self._diagnostics_http: DiagnosticsHttpServer | None = None
        self._try_start_diagnostics_http()

    @property
    def config(self) -> EngineHostConfig:
        return self._config

    @property
    def metrics_collector(self) -> object:
        return self._metrics_collector

    @property
    def metrics_snapshot(self) -> MetricsSnapshot:
        return self._metrics_collector.snapshot()

    @property
    def diagnostics_hub(self) -> DiagnosticHub:
        return self._diagnostics_hub

    @property
    def diagnostics_metrics_snapshot(self) -> object:
        return self._diagnostics_metrics.snapshot()

    @property
    def diagnostics_profiling_snapshot(self) -> object:
        return self._diagnostics_profiler.snapshot()

    @property
    def diagnostics_replay_manifest(self) -> object:
        return self._replay_recorder.manifest()

    @property
    def diagnostics_replay_snapshot(self) -> object:
        return self._replay_recorder.snapshot()

    def current_frame_index(self) -> int:
        return self._frame_index

    def export_diagnostics_profiling(self, *, path: str) -> str:
        exported = self._diagnostics_profiler.export_json(path=Path(path))
        return str(exported)

    def export_diagnostics_replay(self, *, path: str) -> str:
        exported = self._replay_recorder.export_json(path=Path(path))
        return str(exported)

    def export_diagnostics_crash_bundle(self, *, path: str) -> str | None:
        manifest = self._replay_recorder.manifest()
        exported = self._crash_bundle_writer.capture_snapshot(
            tick=self._frame_index,
            diagnostics_hub=self._diagnostics_hub,
            reason="manual_debug_api_export",
            runtime_metadata=self._runtime_metadata(),
            profiling_snapshot={
                "frame_profile": self._frame_profiler.latest_payload or {},
                "spans": _profiling_snapshot_payload(self._diagnostics_profiler.snapshot()),
            },
            replay_metadata={
                "manifest": {
                    "schema_version": manifest.schema_version,
                    "replay_version": manifest.replay_version,
                    "seed": manifest.seed,
                    "build": dict(manifest.build),
                    "command_count": manifest.command_count,
                    "first_tick": manifest.first_tick,
                    "last_tick": manifest.last_tick,
                },
            },
            path=Path(path),
        )
        return str(exported) if exported is not None else None

    def start(self) -> None:
        """Start module lifecycle."""
        if self._started:
            return
        self._started = True
        self._module.on_start(self)

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        self._replay_recorder.record_command(
            tick=self._frame_index,
            command_type="input.pointer",
            payload={
                "event_type": str(getattr(event, "event_type", "")),
                "x": float(getattr(event, "x", 0.0)),
                "y": float(getattr(event, "y", 0.0)),
                "button": int(getattr(event, "button", 0)),
            },
        )
        return self._module.on_pointer_event(event)

    def handle_key_event(self, event: KeyEvent) -> bool:
        self._replay_recorder.record_command(
            tick=self._frame_index,
            command_type="input.key",
            payload={
                "event_type": str(getattr(event, "event_type", "")),
                "value": str(getattr(event, "value", "")),
            },
        )
        if self._debug_overlay is not None and self._is_overlay_toggle_event(event):
            self._debug_overlay_visible = not self._debug_overlay_visible
            if self._render_api is not None and hasattr(self._render_api, "invalidate"):
                self._render_api.invalidate()
            return True
        return self._module.on_key_event(event)

    def handle_wheel_event(self, event: WheelEvent) -> bool:
        self._replay_recorder.record_command(
            tick=self._frame_index,
            command_type="input.wheel",
            payload={
                "x": float(getattr(event, "x", 0.0)),
                "y": float(getattr(event, "y", 0.0)),
                "dy": float(getattr(event, "dy", 0.0)),
            },
        )
        return self._module.on_wheel_event(event)

    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        for pointer_event in snapshot.pointer_events:
            self._replay_recorder.record_command(
                tick=self._frame_index,
                command_type="input.pointer",
                payload={
                    "event_type": str(getattr(pointer_event, "event_type", "")),
                    "x": float(getattr(pointer_event, "x", 0.0)),
                    "y": float(getattr(pointer_event, "y", 0.0)),
                    "button": int(getattr(pointer_event, "button", 0)),
                },
            )
        filtered_key_events: list[KeyEvent] = []
        overlay_toggled = False
        for key_event in snapshot.key_events:
            self._replay_recorder.record_command(
                tick=self._frame_index,
                command_type="input.key",
                payload={
                    "event_type": str(getattr(key_event, "event_type", "")),
                    "value": str(getattr(key_event, "value", "")),
                },
            )
            if self._debug_overlay is not None and self._is_overlay_toggle_event(key_event):
                self._debug_overlay_visible = not self._debug_overlay_visible
                if self._render_api is not None and hasattr(self._render_api, "invalidate"):
                    self._render_api.invalidate()
                overlay_toggled = True
                continue
            filtered_key_events.append(key_event)
        for wheel_event in snapshot.wheel_events:
            self._replay_recorder.record_command(
                tick=self._frame_index,
                command_type="input.wheel",
                payload={
                    "x": float(getattr(wheel_event, "x", 0.0)),
                    "y": float(getattr(wheel_event, "y", 0.0)),
                    "dy": float(getattr(wheel_event, "dy", 0.0)),
                },
            )
        module_snapshot = snapshot
        if len(filtered_key_events) != len(snapshot.key_events):
            module_snapshot = replace(snapshot, key_events=tuple(filtered_key_events))
        return bool(self._module.on_input_snapshot(module_snapshot)) or overlay_toggled

    def frame(self) -> None:
        """Execute one frame callback."""
        if not self._started:
            self.start()
        if self._closed:
            return
        frame_span = self._diagnostics_profiler.begin_span(
            tick=self._frame_index,
            category="host",
            name="frame",
            metadata={"frame_index": self._frame_index},
        )
        self._diagnostics_hub.emit_fast(
            category="frame",
            name="frame.start",
            tick=self._frame_index,
            metadata={"closed": False},
        )
        time_context = self._clock.next(self._frame_index)
        self._metrics_collector.begin_frame(self._frame_index)
        self._scheduler.advance(time_context.delta_seconds)
        enqueued_count, dequeued_count = self._scheduler.consume_activity_counts()
        if hasattr(self._metrics_collector, "set_scheduler_activity"):
            self._metrics_collector.set_scheduler_activity(enqueued_count, dequeued_count)
        self._metrics_collector.set_scheduler_queue_size(self._scheduler.queued_task_count)
        if self._closed:
            self._metrics_collector.end_frame(time_context.delta_seconds * 1000.0)
            return
        module_span = self._diagnostics_profiler.begin_span(
            tick=self._frame_index,
            category="module",
            name="on_frame",
        )
        try:
            self._module.on_frame(
                HostFrameContext(
                    frame_index=self._frame_index,
                    delta_seconds=time_context.delta_seconds,
                    elapsed_seconds=time_context.elapsed_seconds,
                )
            )
        except Exception as exc:
            self._diagnostics_profiler.end_span(module_span)
            bundle_path = self._crash_bundle_writer.capture_exception(
                exc,
                tick=self._frame_index,
                diagnostics_hub=self._diagnostics_hub,
                runtime_metadata=self._runtime_metadata(),
                profiling_snapshot={
                    "frame_profile": self._frame_profiler.latest_payload or {},
                    "spans": _profiling_snapshot_payload(self._diagnostics_profiler.snapshot()),
                },
            )
            if bundle_path is not None:
                _LOG.error("crash_bundle_written path=%s", bundle_path)
            self._diagnostics_profiler.end_span(frame_span)
            raise
        self._diagnostics_profiler.end_span(module_span)
        self._metrics_collector.end_frame(time_context.delta_seconds * 1000.0)
        snapshot = self._metrics_collector.snapshot()
        emit_frame_metrics(self._diagnostics_hub, snapshot)
        self._diagnostics_hub.emit_fast(
            category="frame",
            name="frame.end",
            tick=self._frame_index,
            metadata={
                "delta_seconds": time_context.delta_seconds,
                "elapsed_seconds": time_context.elapsed_seconds,
            },
        )
        if (
            self._debug_overlay is not None
            and self._debug_overlay_visible
            and self._render_api is not None
        ):
            diagnostics_summary = None
            get_diag = getattr(self._render_api, "ui_diagnostics_summary", None)
            if callable(get_diag):
                diagnostics_summary = get_diag()
            self._debug_overlay.draw(
                self._render_api,
                self._metrics_collector.snapshot(),
                ui_diagnostics=diagnostics_summary,
            )
        if _LOG.isEnabledFor(logging.DEBUG):
            snapshot = self._metrics_collector.snapshot()
            if snapshot.last_frame is not None:
                _LOG.debug(
                    "frame_metrics frame=%d dt_ms=%.3f fps=%.2f sched_q=%d events=%d top=%s",
                    snapshot.last_frame.frame_index,
                    snapshot.last_frame.dt_ms,
                    snapshot.rolling_fps,
                    snapshot.last_frame.scheduler_queue_size,
                    snapshot.last_frame.event_publish_count,
                    snapshot.top_systems_last_frame,
                )
        profile = self._frame_profiler.make_profile_payload(snapshot)
        if profile is not None:
            self._diagnostics_hub.emit_fast(
                category="perf",
                name="perf.frame_profile",
                tick=self._frame_index,
                value=profile,
            )
            _PROFILE_LOG.info(
                "frame_profile frame=%d dt_ms=%.3f top=%s",
                profile["frame_index"],
                profile["dt_ms"],
                profile["systems"]["top_system"]["name"],
                extra={"profile": profile},
            )
        self._diagnostics_profiler.end_span(frame_span)
        state_hash = self._resolve_replay_state_hash()
        self._replay_recorder.mark_frame(tick=self._frame_index, state_hash=state_hash)
        self._frame_index += 1
        if self._module.should_close():
            self.close()

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a one-shot callback in host runtime time."""
        return self._scheduler.call_later(delay_seconds, callback)

    def call_every(self, interval_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a recurring callback in host runtime time."""
        return self._scheduler.call_every(interval_seconds, callback)

    def cancel_task(self, task_id: int) -> None:
        """Cancel a previously scheduled task."""
        self._scheduler.cancel(task_id)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._export_profiling_on_shutdown()
        self._export_replay_capture_on_shutdown()
        if self._diagnostics_http is not None:
            self._diagnostics_http.stop()
            self._diagnostics_http = None
        self._diagnostics_hub.unsubscribe(self._diagnostics_subscriber_token)
        self._frame_profiler.close()
        self._module.on_shutdown()

    def is_closed(self) -> bool:
        return self._closed

    @staticmethod
    def _is_overlay_toggle_event(event: KeyEvent) -> bool:
        return event.event_type == "key_down" and event.value.strip().lower() == _OVERLAY_TOGGLE_KEY

    def _resolve_replay_state_hash(self) -> str | None:
        try:
            return _try_state_hash_provider(self._module)
        except Exception:  # pylint: disable=broad-exception-caught
            _LOG.exception("replay_state_hash_provider_failed")
            return None

    @staticmethod
    def _runtime_metadata() -> dict[str, object]:
        versions: dict[str, str] = {}
        for pkg in ("pygfx", "wgpu", "rendercanvas"):
            try:
                versions[pkg] = version(pkg)
            except PackageNotFoundError:
                versions[pkg] = "unknown"
        game_name = os.getenv("ENGINE_GAME_NAME", "game").strip() or "game"
        return {"engine_versions": versions, "game_name": game_name}

    def _try_start_diagnostics_http(self) -> None:
        enabled_raw = os.getenv("ENGINE_DEBUG_OBS_HTTP", "1").strip().lower()
        if enabled_raw in {"0", "false", "off", "no"}:
            return
        bind_host = os.getenv("ENGINE_DEBUG_OBS_HTTP_HOST", "127.0.0.1").strip() or "127.0.0.1"
        try:
            bind_port = int(os.getenv("ENGINE_DEBUG_OBS_HTTP_PORT", "8765"))
        except ValueError:
            bind_port = 8765
        server = DiagnosticsHttpServer(host_obj=self, bind_host=bind_host, bind_port=bind_port)
        try:
            server.start()
        except OSError:
            _LOG.warning(
                "diagnostics_http_start_failed endpoint=http://%s:%d", bind_host, bind_port
            )
            return
        self._diagnostics_http = server
        _LOG.info("diagnostics_http_endpoint=%s", server.endpoint)

    def _export_replay_capture_on_shutdown(self) -> None:
        manifest = self._replay_recorder.manifest()
        if not self._diag_cfg.replay_capture:
            return
        if manifest.command_count <= 0:
            return
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        game_name = os.getenv("ENGINE_GAME_NAME", "game").strip() or "game"
        out_dir = Path(self._diag_cfg.replay_export_dir)
        out_path = out_dir / f"{game_name}_replay_session_{stamp}.json"
        try:
            exported = self._replay_recorder.export_json(path=out_path)
        except OSError:
            _LOG.warning("replay_export_failed path=%s", out_path)
            return
        _LOG.info("replay_export_written path=%s", exported)

    def _export_profiling_on_shutdown(self) -> None:
        snapshot = self._diagnostics_profiler.snapshot(limit=50_000)
        spans = list(getattr(snapshot, "spans", []))
        if not spans:
            return
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        game_name = os.getenv("ENGINE_GAME_NAME", "game").strip() or "game"
        out_dir = Path(self._diag_cfg.profile_export_dir)
        out_path = out_dir / f"{game_name}_profiling_data_{stamp}.jsonl"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            with out_path.open("w", encoding="utf-8") as out:
                for span in spans:
                    payload = {
                        "tick": int(getattr(span, "tick", 0)),
                        "category": str(getattr(span, "category", "")),
                        "name": str(getattr(span, "name", "")),
                        "start_s": float(getattr(span, "start_s", 0.0)),
                        "end_s": float(getattr(span, "end_s", 0.0)),
                        "duration_ms": float(getattr(span, "duration_ms", 0.0)),
                        "metadata": dict(getattr(span, "metadata", {}) or {}),
                    }
                    out.write(json.dumps(payload, ensure_ascii=True))
                    out.write("\n")
        except OSError:
            _LOG.warning("profiling_export_failed path=%s", out_path)
            return
        _LOG.info("profiling_export_written path=%s spans=%d", out_path, len(spans))


def _profiling_snapshot_payload(snapshot: object) -> dict[str, object]:
    spans_raw = getattr(snapshot, "spans", [])
    spans: list[dict[str, object]] = []
    for span in spans_raw:
        spans.append(
            {
                "tick": int(getattr(span, "tick", 0)),
                "category": str(getattr(span, "category", "")),
                "name": str(getattr(span, "name", "")),
                "duration_ms": float(getattr(span, "duration_ms", 0.0)),
                "metadata": dict(getattr(span, "metadata", {}) or {}),
            }
        )
    top = list(getattr(snapshot, "top_spans_ms", []))
    return {
        "mode": str(getattr(snapshot, "mode", "off")),
        "span_count": int(getattr(snapshot, "span_count", len(spans))),
        "top_spans_ms": top,
        "spans": spans,
    }


def _resolve_replay_seed() -> int | None:
    raw = os.getenv("WARSHIPS_RNG_SEED", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _try_state_hash_provider(module: object) -> str | None:
    provider = getattr(module, "debug_state_hash", None)
    if not callable(provider):
        return None
    state_hash = provider()
    if state_hash is None:
        return None
    if isinstance(state_hash, str):
        return state_hash
    return str(state_hash)
