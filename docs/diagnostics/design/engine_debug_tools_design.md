# Engine Debug Tool Suite Design

## 1. Purpose
This document specifies the concrete debug tools to build on top of the diagnostics framework.
It is implementation-facing: pages, interactions, required data, APIs, and acceptance criteria.

Related architecture overview:
- `docs/diagnostics/design/engine_observability_rebuild_design.md`

## 2. Tool Suite (Mandatory)
The suite consists of 3 mandatory tools sharing one common core library.

1. `engine_monitor` (live triage)
2. `engine_session_inspector` (offline deep analysis)
3. `engine_repro_lab` (deterministic replay and validation)

Shared core:
- `tools/engine_obs_core/`

## 3. Shared Core Contract

## 3.1 Core modules
- `contracts.py`: typed models and schema guards.
- `datasource/base.py`: abstract data source interface.
- `datasource/file_source.py`: json/jsonl session/replay/profile/crash loading.
- `datasource/live_source.py`: live engine source adapter.
- `query.py`: filtering/search DSL and predicate composition.
- `timeline.py`: windowing, resampling, correlation windows.
- `aggregations.py`: percentiles, hitches, top offenders, deltas.
- `export.py`: bundle/report export.

## 3.2 Canonical models
- `EventRecord`: `{ts_utc, tick, category, name, level, value, metadata}`
- `FramePoint`: `{tick, frame_ms, render_ms, fps_rolling}`
- `SpanRecord`: `{tick, category, name, start_s, end_s, duration_ms, metadata}`
- `ReplayCommandRecord`: `{tick, type, payload}`
- `ReplayCheckpointRecord`: `{tick, hash}`
- `CrashBundleRecord`: normalized `engine.crash_bundle.v1`

## 3.3 Source interface (must be shared by all tools)
```python
class ObsSource:
    def list_sessions(self) -> list[SessionRef]: ...
    def load_events(self, session: SessionRef, window: TimeWindow | None = None) -> list[EventRecord]: ...
    def load_metrics(self, session: SessionRef) -> MetricsSnapshot: ...
    def load_spans(self, session: SessionRef, limit: int) -> list[SpanRecord]: ...
    def load_replay(self, session: SessionRef) -> ReplaySession: ...
    def load_crash(self, session: SessionRef) -> CrashBundleRecord | None: ...
    def export_report(self, report: AnalysisReport, path: Path) -> Path: ...
```

## 4. Tool A: `engine_monitor` (Live)

## 4.1 Primary use
Fast triage during active runtime. Operator answers: "What is wrong right now?"

## 4.2 Pages
1. Health
- KPI cards: FPS, frame ms p50/p95/p99, render ms rolling, queue depth.
- Live spark lines (60s rolling).
- Alert strip (threshold breaches).

2. Timeline
- Multi-lane graph:
  - frame ms
  - render ms
  - scheduler queue depth
  - publish count
- Cursor + brush selection.

3. Hitch Analyzer
- Hitch table sorted by severity.
- On select: correlation panel (+/- 500 ms around hitch):
  - top spans
  - event burst categories
  - render resize/present state

4. Render/Resize
- Dedicated trace view for:
  - `render.resize_event`
  - `render.viewport_applied`
  - `render.camera_projection`
  - `render.pixel_ratio`
  - `render.surface_dims`
  - `render.present_interval`
- Visual state diff between consecutive resize windows.

## 4.3 Controls
- Window size: 5s, 30s, 60s, 120s.
- Hitch threshold (ms).
- Category toggles.
- Global text search.
- One-click capture: export crash-style snapshot and perf slice.

## 4.4 Required data
- Live `get_diagnostics_snapshot`, `get_metrics_snapshot`, `get_profiling_snapshot`.
- Optional live replay stats for command density.

## 4.5 Acceptance
- In < 2 clicks, engineer can isolate top hitch and see correlated contributors.
- UI remains responsive at 10k recent events.

## 5. Tool B: `engine_session_inspector` (Offline)

## 5.1 Primary use
Post-run deep investigation and issue report generation.

## 5.2 Pages
1. Session Summary
- Run metadata, schema versions, config fingerprint.
- KPI summary and anomaly counts.

2. Events Explorer
- Virtualized table with filters:
  - category, name, level, tick range, text query.
- Payload panel:
  - pretty JSON tree
  - copy path/value actions.

3. Profiling
- Span timeline chart (zoom + pan).
- Aggregates:
  - total and p95 by `category:name`
  - trend across run windows.
- "Explain hitch" action maps selected hitch to span/event context.

4. Replay
- Continuous playback and frame scrubber.
- Command density histogram.
- Checkpoint/hash track.

5. Crashes
- Crash bundle viewer (`engine.crash_bundle.v1`).
- Exception context + recent-event corridor.
- Export selected corridor to report package.

## 5.3 Controls
- Preset filters: render issue, perf regression, crash triage.
- Saved queries and bookmarks.

## 5.4 Required data
- `discover_debug_sessions`, `load_debug_session`.
- Optional imported exports:
  - profiling (`diag.profiling.v1`)
  - replay (`diag.replay_session.v1`)
  - crash bundle (`engine.crash_bundle.v1`)

## 5.5 Acceptance
- A new engineer can reconstruct a bug timeline from session files in < 10 minutes.
- Payload readability: no flattened long-line blobs.

## 6. Tool C: `engine_repro_lab` (Mandatory)

## 6.1 Primary use
Deterministic reproduction and replay validation for bug fixing and regression detection.

## 6.2 Modes
1. Single Replay Validate
- Load replay session.
- Run fixed-step simulation.
- Compare expected vs actual checkpoints.
- Output mismatch report (tick, expected hash, actual hash, nearby commands).

2. Batch Validate
- Run N replay sessions.
- Emit pass/fail matrix and mismatch statistics.

3. Differential Validate
- Compare baseline run vs candidate branch/build on same replay inputs.
- Show first divergence tick and confidence info.

## 6.3 Screens
1. Input
- Replay file chooser (single/batch).
- Fixed-step config.
- Determinism settings.

2. Run
- Progress and current tick.
- Early divergence notifications.

3. Results
- Pass/fail summary.
- Mismatch table.
- Command/context inspector around divergence.
- Export report JSON.

## 6.4 Required engine/API data
- `get_replay_snapshot`, `validate_replay_snapshot`.
- Replay manifest and checkpoint/hash stream.

## 6.5 Acceptance
- Repro Lab can deterministically validate known stable sessions.
- Reports are machine-readable and attachable to CI artifacts.

## 7. UX and Interaction Rules (All tools)
1. One primary task per page.
2. Advanced options hidden by default.
3. Every table supports search.
4. All payloads shown as formatted tree/JSON.
5. Graph-first for performance views; table-second.
6. Cross-navigation links must exist:
- hitch -> spans
- hitch -> events
- replay tick -> events
- crash -> replay corridor

## 8. Data and Storage Rules
- Default paths:
  - logs: `tools/data/logs`
  - profiles: `tools/data/profiles`
  - replay: `tools/data/replay`
  - crash: `tools/data/crash`
- Never force project-root temp paths.
- All export writes are explicit user actions.

## 9. Implementation Roadmap (Tool-focused)

## Phase T0: Shared core bootstrap
- Define contracts + source interface + file source.

## Phase T1: Session Inspector MVP
- Session Summary + Events Explorer + Crash viewer.

## Phase T2: Profiling visual module
- Timeline + top offenders + hitch correlation.

## Phase T3: Replay visual module
- Scrub + continuous playback + command/checkpoint tracks.

## Phase T4: Repro Lab MVP
- Single replay validation + mismatch report export.

## Phase T5: Live Monitor MVP
- Health + Timeline + Hitch Analyzer.

## Phase T6: Batch and differential repro
- Batch validate + differential compare mode.

## Phase T7: Polish
- Presets/bookmarks, keyboard actions, performance tuning, CI checks.

## 10. Out of Scope (for first implementation wave)
- Remote multi-user collaborative debugging.
- Full ECS graph visual editor.
- AI runtime auto-remediation.

## 11. Definition of Done (Suite)
The suite is "done" when:
- All 3 tools are available and documented.
- Shared core is the only parsing/normalization layer.
- Repro Lab is used in regression validation workflow.
- Engineers can complete triage -> deep inspect -> deterministic reproduce without switching to raw logs.
