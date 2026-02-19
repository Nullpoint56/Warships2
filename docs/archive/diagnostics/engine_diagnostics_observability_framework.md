# Engine Diagnostics & Observability Framework

## 1) Scope and goals

This document translates the vision into an implementation-ready plan based on the current Warships2 codebase. It is additive and keeps diagnostics engine-owned, low-overhead, backend-agnostic, and optional.

Primary goals:

- Structured runtime observability (events + metrics).
- Profiling with light and opt-in heavy modes.
- Crash-context capture and export.
- Deterministic replay foundations.
- Tooling that consumes engine data via stable debug APIs.

## 2) Current codebase findings

### 2.1 Existing useful pieces

- `engine/runtime/observability.py`
  - Has an observability sink (`ObservabilitySink`) and a concrete `JsonlObservabilitySink`.
  - Already close to an exporter model.
- `engine/runtime/events.py`
  - Defines runtime event payloads (`FrameEvent`, `LoopEvent`, etc.).
  - Good precursor for normalized diagnostics schema.
- `engine/runtime/metrics.py`
  - Has loop and frame timing collectors.
  - Good for always-on light metrics.
- `engine/runtime/profiling.py`
  - Already has sampling + timeline structures (`ProfilingSnapshot`, spans, counters).
- `engine/api/debug.py`
  - Has debug snapshots and diagnostics payload APIs.
  - Correct place for stable tool-facing contracts.
- `engine/runtime/host.py`
  - Runtime integration point where frame loop and profiling snapshots are emitted.

### 2.2 Current gaps

- Event model is spread across multiple types without one stable diagnostics schema.
- No single engine-owned diagnostics hub with bounded in-memory retention as the canonical source.
- Crash bundle format and trigger path are not yet a first-class subsystem.
- Replay data model is partial and not unified with diagnostics events.
- Tool relies on file-location expectations in places instead of robust source selection.
- Profiling tab still over-indexes on tabular views versus timeline/graph-first diagnostics.

## 3) Target architecture

Create a new engine package:

```text
engine/diagnostics/
  __init__.py
  event.py
  hub.py
  ring_buffer.py
  metrics_store.py
  profiling.py
  crash.py
  replay.py
  schema.py
  config.py
  adapters.py
  subscribers/
    __init__.py
    jsonl_exporter.py
```

### 3.1 `DiagnosticEvent` (stable additive schema)

```python
DiagnosticEvent:
    ts_utc: str
    tick: int
    category: str          # frame/system/scheduler/render/input/network/audio/error/replay/perf
    name: str              # frame.presented, system.update, resize.applied, etc.
    level: str             # debug/info/warn/error
    value: float | int | str | bool | dict | None
    metadata: dict[str, Any]
```

Rules:

- Additive evolution only.
- Category/name semantics documented and versioned.
- Keep `value` compact; heavy payloads go in metadata with optional truncation.

### 3.2 `DiagnosticHub`

Responsibilities:

- O(1) emit path.
- Subscriber fan-out.
- Bounded retention (ring buffer).
- Snapshot/export APIs.

Interface:

- `emit(event: DiagnosticEvent) -> None`
- `emit_fast(category, name, tick, value=None, metadata=None, level="info") -> None`
- `subscribe(subscriber) -> token`
- `unsubscribe(token) -> None`
- `snapshot(limit: int | None = None, category: str | None = None, name: str | None = None) -> list[DiagnosticEvent]`
- `export(path, format="jsonl", since_tick=None) -> ExportSummary`

### 3.3 Storage

- `RingBuffer[DiagnosticEvent]`, fixed capacity, overwrite oldest.
- Default capacity configurable (`ENGINE_DIAG_BUFFER_CAP`, e.g. 10k).
- No unbounded in-memory accumulation.

## 4) Runtime capability design

### 4.1 Always-on light observability

Emit per frame/tick:

- `frame.start`, `frame.end`, `frame.time_ms`
- `fps.rolling`
- `system.update` (per system duration ms)
- `scheduler.queue_depth`
- `render.present`, `render.draw_count`
- `input.event.count`

Light mode constraints:

- Low allocation.
- No disk write by default.
- On/off by global diagnostics enable.

### 4.2 Profiling mode (opt-in)

Add span instrumentation:

- `prof.span.begin/end` for major subsystems:
  - main loop
  - simulation update
  - render prep
  - command encode
  - present/swap
  - io tasks

Modes:

- `off`
- `light` (aggregates only)
- `timeline` (span capture)
- `timeline+sample` (optional sampling profiler integration)

Outputs:

- In-memory recent spans (bounded).
- JSON export for offline analysis.

### 4.3 Crash and error bundles

On unhandled exception (and optionally fatal asserts):

- capture stack trace
- capture last N diagnostics events
- capture last profiling window
- capture engine/runtime metadata (version, backend, adapter, config toggles)
- capture replay reproduction seed + command window if enabled
- write bundle to `tools/data/crash/<timestamp>_bundle.json`

### 4.4 Replay data path

Record:

- seed and build/version hash
- tick-indexed command stream
- nondeterministic inputs (time/random/network injections)

Replay runner:

- fixed-step update loop
- deterministic command reapplication
- validation hooks (state hash per interval)

### 4.5 Rendering diagnostics coverage

Emit normalized render events:

- `render.resize_event`
- `render.viewport_applied`
- `render.camera_projection`
- `render.pixel_ratio`
- `render.surface_dims` (logical/physical)
- `render.present_interval`

This directly targets current resize/cadence investigation needs.

## 5) Engine debug API contract

Extend `engine/api/debug.py` with stable tool-facing endpoints:

- `get_diagnostics_snapshot(filters, limit)`
- `get_metrics_snapshot(window_ms)`
- `get_profiling_snapshot(window_ms, top_n)`
- `get_replay_manifest(session_id)`
- `export_profiling_snapshot(path)`
- `export_replay_session(path)`
- `export_crash_bundle(path)`

Requirements:

- no tool importing runtime internals directly
- API returns versioned payloads (`schema_version`)
- API supports missing-feature graceful fallback

## 6) Tool architecture (unified tool)

Unify around engine debug API + diagnostics files:

```text
tools/engine_observability/
  data_source.py      # engine api + file source abstraction
  models.py           # normalized ui models
  panels/
    overview.py
    events.py
    replay.py
    logs.py
    profiling.py
```

### 6.1 Panel separation

- Overview: health, FPS, frame-time trend, active warnings.
- Events: searchable structured stream, grouped payload rendering (tree/json pretty view).
- Replay: timeline + continuous playback mode.
- Logs/Crash: session picker + crash bundle explorer.
- Profiling: graph-first (timeline, flame-ish bars, subsystem cost trends, percentile plots).

### 6.2 Data location behavior

- Default source folder: `tools/data/logs` and `tools/data/crash`.
- User can browse/select any folder/session file.
- Never hardcode project-root temp paths as mandatory.

### 6.3 Replay continuous mode

- Add play/pause + rate control (0.25x/0.5x/1x/2x).
- Render frame sequence like a video timeline.
- Keep deterministic frame stepping available.

## 7) Performance and safety constraints

- Diagnostics path must not block main loop.
- File export happens on background worker or deferred flush.
- Bounded memory everywhere.
- Global master toggle:
  - `ENGINE_DIAG_ENABLED=0` disables hub emit fast-path.
- Profiling heavy mode opt-in only.

## 8) Configuration model

Use engine capability-style config (not debug-only ad hoc flags):

- `ENGINE_DIAG_ENABLED=1`
- `ENGINE_DIAG_BUFFER_CAP=10000`
- `ENGINE_DIAG_EXPORT_JSONL=0`
- `ENGINE_DIAG_PROFILE_MODE=off|light|timeline|timeline_sample`
- `ENGINE_DIAG_CRASH_BUNDLE=1`
- `ENGINE_DIAG_REPLAY_CAPTURE=0|1`
- `ENGINE_DIAG_REPLAY_HASH_INTERVAL=60`

Keep backward-compat env mappings during transition.

## 9) Phase-by-phase implementation plan

## Phase 0: Foundation alignment

Deliverables:

- Create `engine/diagnostics/` package skeleton.
- Add `DiagnosticEvent`, `RingBuffer`, `DiagnosticHub`.
- Add compatibility adapter from existing runtime events.

Exit criteria:

- Host loop can emit into hub with negligible overhead.
- Unit tests for ring buffer overwrite and snapshot filtering.

## Phase 1: Light observability migration

Deliverables:

- Route frame/system/render/resize signals into hub.
- Add `metrics_store.py` rolling aggregates.
- Expose `get_diagnostics_snapshot` and `get_metrics_snapshot`.

Exit criteria:

- Existing metrics continue working.
- New API snapshots used by tool without regressions.

## Phase 2: Crash/error infrastructure

Deliverables:

- Implement `crash.py` bundle writer.
- Integrate unhandled exception hook in runtime host.
- Bundle includes last N events + runtime metadata.

Exit criteria:

- Forced crash produces valid bundle in `tools/data/crash`.
- Bundle schema versioned + documented.

## Phase 3: Profiling mode completion

Deliverables:

- Normalize profiling spans into diagnostics pipeline.
- Add profiler windows and top offenders.
- Export profiling snapshots to JSON.

Exit criteria:

- Profiling mode off has near-zero overhead.
- Timeline mode visualizable in tool.

## Phase 4: Replay determinism path

Deliverables:

- Command stream + seed capture module.
- Replay runner via fixed-step update.
- Optional state hash checkpoints.

Exit criteria:

- Recorded session can replay deterministically for test scenarios.
- Mismatch reports include tick + subsystem context.

## Phase 5: Unified tool refactor

Deliverables:

- Strict panel separation and scoped controls.
- File/session locator UX with sane defaults.
- Replay continuous playback mode.
- Events payload pretty renderer.
- Profiling tab with graph-first views.

Exit criteria:

- Tool does not assume root temp path.
- All critical workflows are discoverable in <=2 actions.

## Phase 6: Legacy cleanup

Deliverables:

- Remove/reduce old redundant diagnostic tools.
- Keep migration shims temporarily where needed.
- Update docs and runbooks.

Exit criteria:

- Single maintained observability tool path.
- Deprecated modules listed and sunset dates set.

## Phase 7: Hardening and performance budget

Deliverables:

- Overhead benchmarks for diag off/light/timeline.
- Stress tests for ring buffer and exporter backpressure.
- Schema compatibility tests.

Exit criteria:

- Budget met (agreed ms overhead bounds).
- CI checks prevent schema regressions.

## 10) Testing strategy

- Unit tests:
  - ring buffer behavior
  - event schema serialization
  - snapshot filtering
  - crash bundle creation
- Integration tests:
  - runtime host emits expected categories
  - profiling mode transitions
  - replay record/replay smoke
- Tool tests:
  - session discovery
  - panel data mapping
  - continuous replay transport controls

## 11) Immediate next execution slice

Recommended next work package (small, safe):

1. Implement Phase 0 skeleton and adapters.
2. Move current metrics emission through `DiagnosticHub`.
3. Add `engine/api/debug.py` snapshot endpoints with schema version.
4. Switch tool default path resolution to `tools/data/logs`.

This gives a stable base before any new UI complexity.

## 12) Implementation Status

Status timestamp: current workspace state.

Phase 0:

- Completed:
  - Added `engine/diagnostics/` core package.
  - Added `DiagnosticEvent` schema (`engine/diagnostics/event.py`).
  - Added fixed-capacity ring buffer (`engine/diagnostics/ring_buffer.py`).
  - Added `DiagnosticHub` with emit/subscriber/snapshot APIs (`engine/diagnostics/hub.py`).
  - Added adapter from runtime metrics to diagnostics events (`engine/diagnostics/adapters.py`).
  - Wired host frame lifecycle emission (`frame.start`, `frame.time_ms`, `frame.end`) and system/scheduler/input derived events.
- Verified:
  - Unit tests added and passing for ring buffer/hub and host integration.

Phase 1:

- Completed:
  - Added diagnostics rolling aggregate store (`engine/diagnostics/metrics_store.py`).
  - Host now maintains diagnostics aggregate snapshots.
  - Added debug API snapshot accessors:
    - `get_diagnostics_snapshot(...)`
    - `get_metrics_snapshot(...)`
  - Routed render and resize signals into `DiagnosticHub` from scene runtime.
  - Expanded metrics endpoint with render and resize latency aggregates.

Phase 2:

- Completed:
  - Added crash bundle writer (`engine/diagnostics/crash.py`).
  - Added diagnostics capability config (`engine/diagnostics/config.py`) with `ENGINE_DIAG_*` env support.
  - Integrated host exception capture in `engine/runtime/host.py`:
    - writes structured crash bundle on unhandled frame exceptions
    - includes recent diagnostics events, runtime metadata, and latest profiling snapshot.
  - Added renderer draw-loop failure diagnostics event (`error/render.unhandled_exception`).
- Verified:
  - Unit tests added and passing for crash bundle writing and host crash integration.

Phase 3:

- Completed:
  - Added diagnostics profiling spans module (`engine/diagnostics/profiling.py`).
  - Added diagnostics profile capability config (`ENGINE_DIAG_PROFILE_MODE`, sampling, span cap, export dir).
  - Integrated host span timing (`perf.span`) and normalized frame profiling events (`perf.frame_profile`) into `DiagnosticHub`.
  - Added API support:
    - `get_profiling_snapshot(...)`
    - `export_profiling_snapshot(...)`
  - Added profiling export JSON schema `diag.profiling.v1`.
- Verified:
  - Unit tests added for profiling span collection, export, host perf event emission, and API profiling snapshots/exports.

Phase 4:

- Completed:
  - Added replay recorder core (`engine/diagnostics/replay.py`) with:
    - tick-indexed command stream capture
    - seed/build manifest
    - periodic state-hash slots
    - JSON export schema `diag.replay_session.v1`
    - fixed-step replay runner (`FixedStepReplayRunner`) with checkpoint validation
  - Integrated replay capture in `engine/runtime/host.py` for input events and frame ticks.
  - Integrated optional module state-hash capture via `debug_state_hash()` hook for deterministic checkpoints.
  - Added API support:
    - `get_replay_manifest(...)`
    - `get_replay_snapshot(...)`
    - `export_replay_session(...)`
    - `validate_replay_snapshot(...)`
  - Added diagnostics replay capability config:
    - `ENGINE_DIAG_REPLAY_CAPTURE`
    - `ENGINE_DIAG_REPLAY_EXPORT_DIR`
    - `ENGINE_DIAG_REPLAY_HASH_INTERVAL`
- Verified:
  - Unit tests added and passing for replay recorder manifest/export, fixed-step validation, host replay capture, and replay debug API surfaces.

Phase 5:

- Completed:
  - Unified tool (`tools/engine_observability.py`) now supports direct loading of:
    - profiling export JSON (`diag.profiling.v1`)
    - replay export JSON (`diag.replay_session.v1`)
    - crash bundle JSON (`engine.crash_bundle.v1`)
  - Replay tab now surfaces nearby replay commands from loaded replay sessions.
  - Crash panel prefers structured crash bundle context when provided (exception/trace/runtime/recent-event summary).
  - Profiling tab can render synthetic per-frame profiling samples from exported span timelines when run-log frame-profile records are unavailable.
- Verified:
  - Compile checks for updated tool and diagnostics/api modules.
  - Targeted diagnostics/runtime/api unit tests passing after tool integration.

Phase 6:

- Completed:
  - Removed legacy CLI delegation from unified tool to runtime observability shim.
  - Unified tool now performs list/session summary operations directly via `engine.api.debug` discover/load APIs.
  - Removed public API exposure and unused implementation for `run_debug_cli`.
  - Migrated observability core tests to `engine.api.debug` surface (no direct `engine.runtime.observability` dependency).
- Deprecated modules and sunset:
  - `tools/ui_diag_replay.py`: removed (sunset effective immediately).
  - `tools/ui_diag_viewer.py`: removed (sunset effective immediately).
  - `tools/engine_observability_core.py`: removed (sunset effective immediately).
  - `engine.api.debug.run_debug_cli`: removed (sunset effective immediately).
- Verified:
  - Unified tool compiles and targeted diagnostics/runtime/api tests pass post-cleanup.

Phase 7:

- Completed:
  - Added diagnostics schema compatibility guard constants (`engine/diagnostics/schema.py`) and wired schema identifiers through debug/crash/replay/profiling outputs.
  - Added stress tests:
    - ring buffer high-volume append/snapshot ordering
    - async exporter bounded-queue backpressure behavior
  - Added async JSONL exporter subscriber (`engine/diagnostics/subscribers/jsonl_exporter.py`) for non-blocking export paths.
  - Added diagnostics overhead benchmark script (`scripts/diagnostics_benchmark.py`) for `off`, `light`, and `timeline` emit cost baselining.
  - Added schema compatibility tests for API/debug payload views and crash bundle schema.
- Verified:
  - Compile checks and targeted diagnostics/runtime/api tests pass with new hardening coverage.
