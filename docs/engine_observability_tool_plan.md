# Engine Observability Tool Plan

## Goal
Build one tool that covers:
1. Replay
2. Event viewing
3. Logging and crash viewing
4. Profilable render and main update loop metrics

This tool replaces fragmented workflows from older diagnostics scripts while avoiding a large, filter-heavy control surface.

## Product Shape
Single desktop app (Tkinter, same stack as current tools) with four workflow tabs:
1. `Replay`
2. `Events`
3. `Runs/Crashes`
4. `Performance`

Use task-oriented presets instead of many independent knobs.

## Non-Goals
1. Do not replicate every `ui_diag_viewer` filter.
2. Do not add advanced time-series analysis in v1.
3. Do not support remote log streaming in v1.

## Core Design
### Unified Session Model
Each run is represented by one `SessionBundle`:
1. Run log (`warships_run_*.jsonl`)
2. UI diag log (`ui_diag_run_*.jsonl`) if available
3. Optional crash report
4. Derived metrics cache (computed once, reused by tabs)

### Data Pipeline
1. Discover candidate files.
2. Pair run/ui logs by timestamp heuristic.
3. Parse records to typed events.
4. Build timeline index (`ts -> records`) and frame index (`frame_seq -> ui frame`).
5. Precompute summary metrics (FPS distribution, frame hitch list, update/render cost percentiles, anomaly counts).

### Minimal Control Philosophy
Allowed controls:
1. Global time-range brush
2. Text search
3. Severity preset (`all`, `warnings+`, `errors+`)
4. Event-family preset (`input`, `resize`, `state`, `render`, `all`)
5. Hitch threshold preset (`16ms`, `25ms`, `33ms`, `50ms`)

No large matrix of individual toggles in v1.

## Tab Specs
### Replay
1. Timeline scrubber
2. Frame stepping
3. Snapshot panel:
   - Selected frame summary
   - Nearby run events
   - Retained ops summary
4. Jump helpers:
   - Next hitch
   - Next anomaly
   - Next resize burst

### Events
1. Virtualized event table
2. Columns: timestamp, source, category, key fields, message
3. Preset chips (event family, severity)
4. Expand row for full payload JSON

### Runs/Crashes
1. Session list
2. Session health summary:
   - Crash detected
   - Total warnings/errors
   - Max hitch
   - Mean FPS
3. Crash panel:
   - Exception type
   - Top stack frames
   - Last N events before crash

### Performance
1. FPS and frame-time histogram
2. Percentiles: p50/p95/p99/max
3. Hitch list with jump-to-frame
4. Render vs update cost split (when available)
5. Resize latency stats (event->apply, apply->frame)

## Implementation Phases
## Phase 1: Foundation
1. Create new tool entrypoint `tools/engine_observability.py`.
2. Keep shared parsing/indexing logic in engine runtime and expose it via engine debug API.
3. Define typed models:
   - `SessionBundle`
   - `TimelineEvent`
   - `FrameMetrics`
   - `HitchRecord`
4. Implement pairing/discovery for run + ui logs.
5. Add unit tests for discovery, pairing, parsing, and summary metrics.

Exit criteria:
1. CLI can load a session and print summary metrics.
2. Tests pass for parser/index layers.

## Phase 2: Minimal UI
1. Build four tabs with shared session state.
2. Implement global presets (time-range, severity, event family).
3. Implement jump-to-frame/jump-to-hitch actions.
4. Keep controls fixed and minimal.

Exit criteria:
1. End-to-end inspection of one session from load to hitch drilldown.
2. Existing replay workflow is functionally covered.

## Phase 3: Migration Cleanup
1. Remove `tools/ui_diag_replay.py`.
2. Remove `tools/ui_diag_viewer.py`.
3. Remove all docs references to legacy tools.
4. Keep only `tools/engine_observability.py` as supported entrypoint.

Exit criteria:
1. Legacy files are deleted.
2. Docs reference only unified tool.

## Phase 4: UX Refactor (Requested)
### Phase 4.1: Panel Separation
1. Add strong visual separation using panel containers (`LabelFrame`/`Panedwindow`).
2. Keep each tab self-contained with dedicated controls and content.
3. Reduce cross-tab coupling in refresh logic.

Exit criteria:
1. Each tab has a clear control area and content area.
2. Users can identify scope of controls without ambiguity.

### Phase 4.2: Control Scope Reduction
1. Remove global non-session knobs.
2. Move controls to relevant tabs only:
   - Replay: navigation + jumps.
   - Events: range/severity/family/search.
   - Runs/Crashes: run-log search.
   - Performance: hitch threshold and perf-specific controls.

Exit criteria:
1. No unrelated controls appear outside their owning tab.
2. Default view is uncluttered.

### Phase 4.3: Visual Replay Rendering
1. Add replay canvas renderer for frame primitives/transforms.
2. Keep textual frame details beside visual replay.
3. Support stepping + jump actions with canvas updates.

Exit criteria:
1. Replay tab shows actual frame geometry, not text-only output.
2. Frame navigation updates both canvas and diagnostics panel.

### Phase 4.4: Per-Tab Metrics, Filters, and Search Completeness
1. Events tab:
   - filtered count label
   - dedicated filter row
2. Runs/Crashes tab:
   - summary + searchable warning/error stream
3. Performance tab:
   - hitch list
   - runtime cost split (`render_ms`, `non_render_ms`) where available
   - top costly frame samples table

Exit criteria:
1. Each tab contains the metrics/search needed for its workflow.
2. No workflow depends on controls hidden in another tab.

### Phase 4.5: Validation and Hardening
1. Lint + compile checks only (non-interactive, IDE-safe).
2. Unit tests for observability core (including recursive discovery).
3. CLI `--list` verification against real logs location.

Exit criteria:
1. `ruff`, `py_compile`, and targeted tests pass.
2. Session discovery works for `warships/appdata/logs`.

## Current Status
1. Phase 1 complete.
2. Phase 2 complete.
3. Phase 3 complete (legacy tools removed; unified tool is the only entrypoint).
4. Phase 4.1-4.3 complete (panel separation, control scoping, visual replay canvas).
5. Phase 4.4 complete (tab-level counts, replay details with nearby events, crash-focus panel, expanded performance metrics).
6. Phase 4.5 complete (`ruff`, `py_compile`, targeted tests, `--list`).
7. Plan complete.

## API Boundary
1. Tools must consume observability through `engine.api.debug`, not `engine.runtime.*` imports.
2. Runtime observability implementation remains internal to engine runtime.
3. This keeps tooling decoupled from runtime internals and allows API-stable evolution.

## Risks and Mitigations
1. Large logs causing UI stalls.
   - Mitigation: lazy parsing, indexed offsets, virtualized table rows.
2. Run/ui log pairing mismatch.
   - Mitigation: confidence score + manual override picker.
3. Scope creep via extra controls.
   - Mitigation: fixed presets, phase gate for new controls.

## Defaults (Engine Capability, not Debug)
1. Keep runtime capture hooks in engine as capability-level metrics emitters.
2. Keep visualization complexity in tooling, not in runtime flags.
3. Keep debug-only switches separate from default observability signals.
