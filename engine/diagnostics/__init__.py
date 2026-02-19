"""Engine diagnostics core package."""

from engine.diagnostics.adapters import emit_frame_metrics
from engine.diagnostics.config import (
    DiagnosticsConfig,
    load_diagnostics_config,
    resolve_crash_bundle_dir,
)
from engine.diagnostics.crash import CrashBundleWriter
from engine.diagnostics.event import DiagnosticEvent
from engine.diagnostics.hub import DiagnosticHub
from engine.diagnostics.metrics_store import DiagnosticsMetricsSnapshot, DiagnosticsMetricsStore
from engine.diagnostics.profiling import DiagnosticsProfiler, ProfilingSnapshot, ProfilingSpan
from engine.diagnostics.replay import (
    FixedStepReplayRunner,
    ReplayCommand,
    ReplayManifest,
    ReplayRecorder,
    ReplayValidationMismatch,
    ReplayValidationResult,
    compute_state_hash,
)
from engine.diagnostics.ring_buffer import RingBuffer
from engine.diagnostics.schema import (
    DIAG_EVENT_SCHEMA_VERSION,
    DIAG_METRICS_SCHEMA_VERSION,
    DIAG_PROFILING_SCHEMA_VERSION,
    DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
    DIAG_REPLAY_VALIDATION_SCHEMA_VERSION,
    DIAG_SNAPSHOT_SCHEMA_VERSION,
    ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
)
from engine.diagnostics.subscribers import JsonlAsyncExporter

__all__ = [
    "CrashBundleWriter",
    "DiagnosticEvent",
    "DiagnosticHub",
    "DiagnosticsProfiler",
    "DiagnosticsConfig",
    "DiagnosticsMetricsSnapshot",
    "DiagnosticsMetricsStore",
    "DIAG_EVENT_SCHEMA_VERSION",
    "DIAG_METRICS_SCHEMA_VERSION",
    "DIAG_PROFILING_SCHEMA_VERSION",
    "DIAG_REPLAY_MANIFEST_SCHEMA_VERSION",
    "DIAG_REPLAY_SESSION_SCHEMA_VERSION",
    "DIAG_REPLAY_VALIDATION_SCHEMA_VERSION",
    "DIAG_SNAPSHOT_SCHEMA_VERSION",
    "ENGINE_CRASH_BUNDLE_SCHEMA_VERSION",
    "FixedStepReplayRunner",
    "JsonlAsyncExporter",
    "ProfilingSnapshot",
    "ProfilingSpan",
    "ReplayCommand",
    "ReplayManifest",
    "ReplayRecorder",
    "ReplayValidationMismatch",
    "ReplayValidationResult",
    "RingBuffer",
    "compute_state_hash",
    "emit_frame_metrics",
    "load_diagnostics_config",
    "resolve_crash_bundle_dir",
]
