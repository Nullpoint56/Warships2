# Engine Debug Tools Implementation Plan

## 1. Purpose
This plan turns the design docs into actionable engineering phases with concrete tasks, files, tests, and exit criteria.

Inputs:
- Architecture/strategy: `docs/diagnostics/design/engine_observability_rebuild_design.md`
- Tool product spec: `docs/diagnostics/design/engine_debug_tools_design.md`

## 2. Delivery Rules
1. No duplicated parsing/normalization logic in tool UIs.
2. All tools consume shared core (`tools/engine_obs_core`).
3. Every phase has tests and explicit "done" gates.
4. Keep tools usable at each phase boundary.

## 3. Phase Map

## Phase P0: Foundation and Repo Layout
Goal: establish shared core and tool skeletons.

Deliverables:
- Create packages:
  - `tools/engine_obs_core/`
  - `tools/engine_session_inspector/`
  - `tools/engine_monitor/`
  - `tools/engine_repro_lab/`
- Add `README.md` in each package with scope and non-goals.

File tasks:
- `tools/engine_obs_core/__init__.py`
- `tools/engine_obs_core/contracts.py`
- `tools/engine_obs_core/datasource/__init__.py`
- `tools/engine_obs_core/datasource/base.py`
- `tools/engine_obs_core/datasource/file_source.py` (stub)
- `tools/engine_obs_core/datasource/live_source.py` (stub)
- `tools/engine_obs_core/query.py` (stub)
- `tools/engine_obs_core/timeline.py` (stub)
- `tools/engine_obs_core/aggregations.py` (stub)
- `tools/engine_obs_core/export.py` (stub)
- `tools/engine_session_inspector/main.py` (shell)
- `tools/engine_monitor/main.py` (shell)
- `tools/engine_repro_lab/main.py` (shell)

Tests:
- `tests/tools/engine_obs_core/test_imports.py`

Exit criteria:
- all packages import successfully
- all tool entrypoints run and show scaffold window/CLI output

## Phase P1: Shared Contracts + File Source (Real)
Goal: real normalized ingestion from existing diagnostics artifacts.

Deliverables:
- Canonical typed models in `contracts.py`.
- File source implementation for:
  - run/ui session logs
  - profiling export
  - replay export
  - crash bundle
- Schema/version guards.

File tasks:
- implement models and adapters in:
  - `tools/engine_obs_core/contracts.py`
  - `tools/engine_obs_core/datasource/file_source.py`
- support helpers:
  - `tools/engine_obs_core/query.py` (basic predicates)
  - `tools/engine_obs_core/aggregations.py` (basic fps/hitch stats)

Tests:
- `tests/tools/engine_obs_core/test_file_source_sessions.py`
- `tests/tools/engine_obs_core/test_file_source_exports.py`
- `tests/tools/engine_obs_core/test_schema_guard.py`

Exit criteria:
- a single API can load all existing artifact types without UI code parsing raw JSON

## Phase P2: Session Inspector MVP
Goal: usable offline analysis baseline.

Deliverables:
- Session selector + summary page.
- Events Explorer with:
  - table view
  - search/filter
  - pretty payload panel
- Crash page:
  - crash bundle view
  - fallback crash/error stream summary

File tasks:
- `tools/engine_session_inspector/app.py`
- `tools/engine_session_inspector/views/summary.py`
- `tools/engine_session_inspector/views/events.py`
- `tools/engine_session_inspector/views/crash.py`
- `tools/engine_session_inspector/state.py`

Tests:
- `tests/tools/engine_session_inspector/test_events_filtering.py`
- `tests/tools/engine_session_inspector/test_crash_view_model.py`

Exit criteria:
- engineer can open a session and inspect crash/event context without raw log reading

## Phase P3: Profiling Visual Module (Inspector)
Goal: graph-first profiling investigation.

Deliverables:
- profiling timeline chart
- top contributors (total + p95)
- subsystem trend view
- hitch-to-span correlation jump

File tasks:
- `tools/engine_session_inspector/views/profiling.py`
- `tools/engine_obs_core/timeline.py` (windowed series)
- `tools/engine_obs_core/aggregations.py` (percentiles/top offenders)

Tests:
- `tests/tools/engine_obs_core/test_aggregations_profile.py`
- `tests/tools/engine_session_inspector/test_profiling_view_model.py`

Exit criteria:
- selected hitch explains likely blockers in <= 2 UI hops

## Phase P4: Replay Visual Module (Inspector)
Goal: replay as an investigative timeline tool.

Deliverables:
- frame scrubber
- continuous playback mode
- command density timeline
- checkpoint/hash track and mismatch highlighting

File tasks:
- `tools/engine_session_inspector/views/replay.py`
- `tools/engine_obs_core/timeline.py` (playback cursor + rate support)

Tests:
- `tests/tools/engine_session_inspector/test_replay_playback.py`
- `tests/tools/engine_session_inspector/test_replay_timeline_model.py`

Exit criteria:
- replay timeline usable for visual inconsistency analysis

## Phase P5: Repro Lab MVP (Mandatory)
Goal: deterministic validation workflow.

Deliverables:
- single replay validate flow
- result table with mismatches
- report export JSON

File tasks:
- `tools/engine_repro_lab/app.py`
- `tools/engine_repro_lab/runner.py`
- `tools/engine_repro_lab/reporting.py`
- use `engine.api.debug.validate_replay_snapshot` through adapter layer

Tests:
- `tests/tools/engine_repro_lab/test_validation_runner.py`
- `tests/tools/engine_repro_lab/test_report_schema.py`

Exit criteria:
- known stable replay validates deterministically
- mismatch report is actionable and shareable

## Phase P6: Monitor MVP (Live)
Goal: real-time triage during runtime.

Deliverables:
- Health page
- Timeline page
- Hitch Analyzer page
- Render/Resize diagnostics page

Dependencies:
- live source adapter in `tools/engine_obs_core/datasource/live_source.py`
- transport decision (local process bridge/IPC)

File tasks:
- `tools/engine_monitor/app.py`
- `tools/engine_monitor/views/health.py`
- `tools/engine_monitor/views/timeline.py`
- `tools/engine_monitor/views/hitches.py`
- `tools/engine_monitor/views/render_resize.py`

Tests:
- `tests/tools/engine_monitor/test_live_view_models.py`
- `tests/tools/engine_obs_core/test_live_source_contract.py`

Exit criteria:
- live hitch triage works without log file exports

## Phase P7: Repro Lab Batch + Differential
Goal: regression-grade reproducibility.

Deliverables:
- batch replay validation
- differential baseline-vs-candidate comparison
- first divergence finder

File tasks:
- `tools/engine_repro_lab/batch.py`
- `tools/engine_repro_lab/diff.py`

Tests:
- `tests/tools/engine_repro_lab/test_batch_validation.py`
- `tests/tools/engine_repro_lab/test_differential_validation.py`

Exit criteria:
- reproducibility checks usable in CI workflow

## Phase P8: Polish, Hardening, CI
Goal: production-ready internal tooling.

Deliverables:
- saved filters/presets
- keyboard navigation shortcuts
- performance budget checks
- docs/runbooks

File tasks:
- `docs/diagnostics/guides/engine_debug_tools_user_guide.md`
- `docs/diagnostics/guides/engine_debug_tools_dev_guide.md`
- CI test job entries for new tool tests

Tests:
- regression suite for core query/aggregation correctness
- UI smoke tests where feasible

Exit criteria:
- stable daily use by engine devs

## 4. Cross-Phase Risk Register
1. Live transport complexity for monitor.
- Mitigation: keep P6 after strong offline tools.

2. Replay determinism drift.
- Mitigation: enforce Repro Lab early (P5) and differential tests (P7).

3. UI bloat regression.
- Mitigation: each view must declare one primary question and max 5 visible controls by default.

## 5. Definition of Done (Program)
Done when:
- all 3 tools exist and are used in intended workflows
- shared core is single source of parsing/normalization truth
- replay validation is integrated into bug/regression process
- docs and tests are complete and green
