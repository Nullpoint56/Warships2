# Engine Observability Rebuild Design (Zero-Base)

## 1. Objective
Design a clean observability toolset that is workflow-first:
- Fast issue triage
- Root-cause debugging
- Performance/profiling analysis
- Repro/replay validation

This design intentionally avoids a single overcrowded mega-panel. It uses multiple focused tools with one shared core.

## 2. What The Engine Exposes Today

### 2.1 Tool-facing debug API (`engine/api/debug.py`)
- Session/log file helpers:
  - `discover_debug_sessions(log_dir, recursive)`
  - `load_debug_session(bundle)`
- Live host snapshots/exports:
  - `get_diagnostics_snapshot(host, limit, category, name)`
  - `get_metrics_snapshot(host)`
  - `get_profiling_snapshot(host, limit)`
  - `export_profiling_snapshot(host, path)`
  - `export_crash_bundle(host, path)`
  - `get_replay_manifest(host)`
  - `get_replay_snapshot(host, limit)`
  - `export_replay_session(host, path)`
  - `validate_replay_snapshot(replay_snapshot, fixed_step_seconds, apply_command, step)`

### 2.2 Diagnostics event stream (`DiagnosticHub`)
Current emitted event families/names:
- Frame/scheduler/system/input:
  - `frame.start`, `frame.time_ms`, `frame.end`
  - `scheduler.queue_depth`
  - `system.update_ms`
  - `events.publish_count`
- Render:
  - `render.resize_event`
  - `render.viewport_applied`
  - `render.camera_projection`
  - `render.pixel_ratio`
  - `render.surface_dims`
  - `render.frame_ms`
  - `render.present`
  - `render.present_interval`
  - `render.unhandled_exception`
- Perf/replay:
  - `perf.span`, `perf.frame_profile`
  - `replay.command`, `replay.state_hash`

### 2.3 Aggregates (`DiagnosticsMetricsStore`)
- `frame_count`
- `rolling_frame_ms`
- `rolling_fps`
- `max_frame_ms`
- `resize_count`
- `resize_event_to_apply_p95_ms`
- `resize_apply_to_frame_p95_ms`
- `rolling_render_ms`

### 2.4 Exports available
- Crash bundle JSON (`engine.crash_bundle.v1`)
- Profiling export JSON (`diag.profiling.v1`)
- Replay export JSON (`diag.replay_session.v1`)

## 3. Concern Matrix (Engineer Workflows)

### 3.1 Common concerns that must be first-class
1. "Why did frame time spike/stutter?"
2. "Is this render-bound, simulation-bound, scheduler-bound, or event-storm-bound?"
3. "Resize/input caused visual bug or latency glitch."
4. "Crash happened, what was the last stable context?"
5. "Can we reproduce this deterministically?"
6. "Which systems are consistently slow (not one-frame outliers)?"
7. "Did config/backend changes (vsync/pixel ratio/loop mode) alter behavior?"

### 3.2 Coverage status
- Strong coverage now:
  - frame/render timings, resize pipeline timing, replay command/state hash, perf spans, crash context.
- Partial coverage:
  - long-window trends, per-subsystem memory attribution, event topology visualization.
- Missing/weak:
  - explicit correlation helpers (hitch -> top contributors -> event burst), percentile/baseline comparisons, structured dependency graph views.

## 4. Proposed Toolset (Not One Giga Tool)

## 4.1 Tool A: `engine_monitor` (Live)
Purpose: in-session triage while engine is running.
Primary questions:
- Are we healthy now?
- What changed in the last N seconds?

Views:
- Health HUD: FPS/frame ms, p95, current bottleneck class.
- Timeline strip (last 30/60/120s): frame ms + render ms + queue depth + publish count.
- Hitch inspector: auto-select largest hitch and show correlated events/spans in +/- 500ms window.
- Resize/input watch: specialized stream for `render.resize_event`, `render.viewport_applied`, input bursts.

Controls (minimal):
- Time window, hitch threshold, category toggles, search.
- Capture button: export crash-style snapshot now.

## 4.2 Tool B: `engine_session_inspector` (Offline)
Purpose: deep analysis of logs/exports and issue report preparation.
Primary questions:
- What exactly happened over a whole run?
- How do we explain cause/effect?

Views:
- Session index + metadata summary.
- Event explorer (structured tree payload, query/search/filter).
- Profiling analysis:
  - span timeline chart
  - top span stacks by total and by p95
  - trend chart per subsystem
- Replay analysis:
  - command density timeline
  - checkpoint/hash mismatch diagnostics
  - frame scrubber + continuous playback
- Crash bundle explorer:
  - exception context
  - recent-event corridor
  - runtime/config fingerprint

Controls:
- global query bar (logger/category/name/text)
- saved filters/presets
- export selected slice to JSON for sharing

## 4.3 Tool C (optional later): `engine_repro_lab`
Purpose: deterministic reproduction harness.
- Load replay export + optional baseline hashes.
- Run validation repeatedly across commits/config variants.
- Generate mismatch report bundles.

This can start as CLI and become a small GUI later.

## 5. Shared Core (No Duplication)
Create one shared library package used by all tools:

```text
tools/engine_obs_core/
  contracts.py        # typed schemas for events/metrics/profiling/replay/crash
  datasource/
    base.py           # abstract source interface
    file_source.py    # jsonl/json loaders
    live_source.py    # future live transport adapter
  query.py            # filter language + predicates
  timeline.py         # resampling/windowing/correlation
  aggregations.py     # p50/p95/top contributors/hitch detection
  rendering_models.py # chart-ready immutable view models
  export.py           # save slices/reports
```

Key rule:
- UI packages never parse raw engine files directly.
- All parsing + normalization happens in `engine_obs_core`.

## 6. UI Design Rules (to avoid previous failure)
1. One intent per page.
2. One primary chart + one primary table per page.
3. Advanced knobs go in an "Advanced" drawer, closed by default.
4. Structured payloads always shown in pretty tree/JSON, never flattened line dumps.
5. Every list/table supports search and at least one meaningful grouping.
6. Correlation links are explicit (click hitch -> jump event window -> jump profiling window).

## 7. Engine-side Additions Needed (small, targeted)

## 7.1 Immediate (high value)
- Add optional event IDs and parent IDs for causal linking in `DiagnosticEvent` metadata.
- Emit `system.exception` events with system id + traceback fingerprint.
- Emit stable run/session id in host startup diagnostics.

## 7.2 Profiling enrichment
- Add subsystem tags to spans (`phase`, `module`, `thread`).
- Add periodic memory snapshots behind opt-in flag:
  - process RSS
  - Python heap estimate
  - renderer memory estimate if available

## 7.3 Replay enrichment
- Add explicit replay timeline markers for frame boundaries and command batch counts.

## 8. Precise Phase Plan

## Phase 0: Core contracts and source abstraction
- Implement `engine_obs_core.contracts`, `datasource.base`, `datasource.file_source`.
- Define canonical normalized models for event, span, replay command, crash bundle.
Exit: both tools can load same session through shared core API.

## Phase 1: Session Inspector MVP (offline first)
- Build `engine_session_inspector` shell + session loader + summary page.
- Add Event Explorer with structured payload tree + search/filter.
Exit: can load sessions and investigate crashes/events without chaos.

## Phase 2: Profiling page (graph-first)
- Add span timeline chart, top contributors, subsystem trend.
- Add hitch-to-span correlation.
Exit: engineer can answer "what blocked frame time" in <2 minutes.

## Phase 3: Replay page
- Continuous playback + frame scrub.
- Command density + checkpoint mismatch explorer.
Exit: deterministic bug investigations are practical.

## Phase 4: Live Monitor MVP
- Introduce `live_source` (initially local adapter/IPC stub).
- Build live health/timeline/hitch triage pages.
Exit: active run triage without reading raw logs.

## Phase 5: Capture/report workflow
- One-click capture bundle from live monitor.
- Export selected analysis corridor to report JSON.
Exit: reproducible handoff artifact generated in one flow.

## Phase 6: Polish + guardrails
- Performance budget checks for tool rendering and parsing.
- Presets, keyboard navigation, chart interaction polish.
Exit: tool is stable for daily engineering use.

## 9. Decision
Recommended approach: two tools + one shared core.
- Build offline inspector first (highest reliability, immediate value).
- Add live monitor second.
- Keep reproduction lab as CLI-first extension.

This gives clarity, avoids overcrowding, and keeps implementation incremental while preserving a single reusable data core.
