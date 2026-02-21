# WGPU Renderer Quality + Performance Upgrade Plan

Date: 2026-02-20  
Status: Active  
Scope: Improve visual quality and runtime efficiency after functional rendering parity was restored.

## Why This Plan Exists

Current renderer is functionally correct but has two major gaps:

1. Visual quality regression
- Pixel-like text
- Flat-looking UI (limited shading/AA)

2. Performance regression
- High CPU usage in complex UI scenes (e.g. New Game list view)
- FPS drops under dense UI composition

This plan targets both with data-driven investigation + implementation.

## Principles

1. Performance and quality changes are measured, not assumed.
2. Engine-level fixes first; avoid Warships-only hacks unless explicitly scoped.
3. Repo-wide review is required per target before implementation.
4. Review workflow must be comprehensive but tooling-safe (no IDE freeze).

## Review Workflow (Repo-Wide, Non-Blocking)

For each target:

1. Fast index sweep (CLI only)
- Use `rg` queries scoped by subsystem and keyword clusters.
- Avoid opening huge files blindly.

2. Batch file reading
- Read files in focused chunks (module-by-module).
- Prioritize hot paths: `engine/rendering`, `engine/runtime`, `warships/game/ui`.

3. Evidence log
- Record bottlenecks/weaknesses with:
  - file
  - function
  - mechanism
  - expected impact

4. Implementation proposal
- Convert findings into ranked fixes:
  - high impact / low risk
  - high impact / medium risk
  - later improvements

5. Validation
- Add/adjust tests + targeted runtime checks.
- Keep benchmarks/comparison snapshots for before/after.

## Target A: CPU + Frame Throughput

Goal:
- Reduce CPU load and recover FPS in dense UI scenes.

Initial ideas:

1. Draw-call and pass reduction
- Minimize render-pass churn.
- Merge compatible draw operations.

2. Geometry batching
- Stop rebuilding tiny per-primitive payloads each frame where unnecessary.
- Introduce retained/static batch paths for stable UI.

3. Text cost reduction
- Replace expensive per-glyph CPU expansion with atlas/batched glyph draws.
- Cache text layout results for unchanged labels.

4. Dirty-region/dirty-node rendering
- Skip rebuild/re-encode for unchanged UI regions.

Repo-wide review checklist:

1. Identify per-frame allocations and repeated transforms.
2. Identify code paths that re-emit static primitives every frame.
3. Identify avoidable buffer reuploads and state binds.
4. Confirm event-loop/invalidation behavior is not over-drawing.

Expected outputs:

1. Hotspot table (top CPU contributors).
2. Ranked optimization backlog with effort/risk estimates.

## Target B: Text Quality

Goal:
- Replace blocky text with readable, scalable text rendering.

Initial ideas:

1. Proper glyph atlas path
- Rasterize glyphs once, sample in shader.
- Render text as textured quads.

2. Better text metrics/layout
- Baseline-aware positioning.
- Consistent anchor behavior with measured bounds.

3. Blend correctness
- Ensure alpha/blend state is correct for text on all UI surfaces.

Repo-wide review checklist:

1. Find all text emission paths (`add_text`, overlays, widgets, debug overlay).
2. Trace text primitive conversion -> backend draw path.
3. Locate scaling/quantization points causing jagged output.
4. Verify fallback font behavior and diagnostics completeness.

Expected outputs:

1. Text pipeline gap map.
2. Implementation steps from current bitmap fallback to atlas-backed text.

## Target C: UI Visual Fidelity (Panels/Buttons/Overlays)

Goal:
- Improve visual polish without breaking deterministic behavior.

Initial ideas:

1. Add style primitives/policies
- Subtle gradients, outlines, shadows (bounded, deterministic).

2. Improve color/material consistency
- Ensure intended contrast and hierarchy across screens.

3. Preserve performance budget
- Visual improvements must stay within frame-time target.

Repo-wide review checklist:

1. Identify all UI primitive color/style definitions.
2. Detect hardcoded values that flatten depth/contrast.
3. Map where lightweight shader support can replace CPU-side effects.

Expected outputs:

1. Style system proposal (minimal, engine-owned).
2. Migration path for Warships screens to upgraded styles.

## Target D: Resize + Present Stability Under Load

Goal:
- Keep visual correctness and responsiveness under rapid resize and UI churn.

Initial ideas:

1. Reconfigure path stress validation.
2. Present/acquire retry telemetry review.
3. Ensure no fallback path degrades into blank/stale frames.

Repo-wide review checklist:

1. Trace resize event flow window -> frontend -> renderer.
2. Verify retry/recovery paths and telemetry fields are complete.
3. Validate behavior in on-demand vs continuous modes.

Expected outputs:

1. Reliability matrix by mode and scenario.
2. Any missing guards + mitigation patches.

## Repo-Wide Findings (2026-02-20)

Scope reviewed:
1. `engine/rendering/wgpu_renderer.py`
2. `engine/runtime/host.py`
3. `engine/runtime/window_frontend.py`
4. `engine/window/rendercanvas_glfw.py`
5. `engine/input/input_controller.py`
6. `warships/game/app/engine_game_module.py`
7. `warships/game/ui/game_view.py`
8. `warships/game/ui/views/*.py`
9. `engine/api/ui_primitives.py`
10. `engine/api/ui_projection.py`

### Target A Findings: CPU + Frame Throughput

High-confidence bottlenecks:
1. Full snapshot rebuild each frame: `engine/runtime/host.py:321`, `warships/game/app/engine_game_module.py:166`, `warships/game/ui/game_view.py:132`, `warships/game/ui/game_view.py:147`.
2. Snapshot sanitization clones all commands every publish: `engine/runtime/host.py:116`, `engine/runtime/host.py:710`.
3. Per-frame sort of all commands and passes: `engine/rendering/wgpu_renderer.py:377`, `engine/rendering/wgpu_renderer.py:392`.
4. Per-packet CPU expansion into many rects (especially text/grid): `engine/rendering/wgpu_renderer.py:1367`, `engine/rendering/wgpu_renderer.py:615`, `engine/rendering/wgpu_renderer.py:653`.
5. Per-rect viewport/scissor/draw calls (very high command encoding churn): `engine/rendering/wgpu_renderer.py:1427`.
6. Dynamic pipeline creation by color and shader-source churn risk: `engine/rendering/wgpu_renderer.py:783`, `engine/rendering/wgpu_renderer.py:1351`.
7. Design->viewport transform recomputed per primitive: `engine/rendering/wgpu_renderer.py:1411`.
8. Upload path creates buffers by packet count each frame, no persistent geometry buffers: `engine/rendering/wgpu_renderer.py:1221`, `engine/rendering/wgpu_renderer.py:1236`, `engine/rendering/wgpu_renderer.py:1247`.

Possible but less-likely contributors:
1. Diagnostics event emission volume in hot path if enabled: `engine/diagnostics/hub.py:34`, `engine/runtime/host.py:280`.
2. Continuous loop mode or high FPS cap forcing unnecessary redraw cadence: `engine/rendering/scene_runtime.py:33`, `engine/runtime/bootstrap.py:41`.
3. Redundant redraw requests per raw input event: `engine/window/rendercanvas_glfw.py:208`, `engine/window/rendercanvas_glfw.py:261`, `engine/window/rendercanvas_glfw.py:298`.

### Target B Findings: Text Quality

High-confidence gaps:
1. Text rendering is still CPU bitmap 5x7 rectangles, not glyph atlas quads: `engine/rendering/wgpu_renderer.py:653`.
2. Font discovery exists but resolved font is not used by draw path: `engine/rendering/wgpu_renderer.py:842`, `engine/rendering/wgpu_renderer.py:1509`.
3. Text pipeline is placeholder full-screen triangle shader, not glyph sampling: `engine/rendering/wgpu_renderer.py:1618`.
4. Fit logic quantizes to coarse 8px steps and truncates aggressively, causing inconsistent label quality: `engine/api/ui_primitives.py:194`.

Possible but less-likely contributors:
1. Pixel snapping in text origin can amplify jitter at non-integer scaling: `engine/rendering/wgpu_renderer.py:674`.
2. Alpha/blend configuration is currently trivial and may not match final atlas blending needs: `engine/rendering/wgpu_renderer.py:1109`.

### Target C Findings: UI Visual Fidelity

High-confidence gaps:
1. Flat fill-only primitives, no gradient/outline/shadow primitives in engine renderer path: `engine/rendering/wgpu_renderer.py:1367`.
2. Warships view layer hardcodes color values ad hoc per screen, no shared material tokens: `warships/game/ui/views/new_game_screen.py:12`, `warships/game/ui/views/preset_manage_screen.py:11`, `warships/game/ui/views/placement_battle_screen.py:102`, `warships/game/ui/views/status_overlay.py:11`.
3. Grid and shots are minimal rect overlays with no antialias/stroke control, reducing board readability: `warships/game/ui/views/placement_battle_screen.py:102`, `warships/game/ui/views/placement_battle_screen.py:157`.
4. Layout-fitting is string truncation based and not style-aware (no ellipsis policy variants, no min-height typography scale system): `engine/api/ui_primitives.py:170`, `engine/api/ui_primitives.py:194`.

Possible but less-likely contributors:
1. UI projection clamp is available but not consistently used for button containers, so some screens can still drift toward edge collisions during future layout changes: `engine/api/ui_projection.py:23`.
2. Modal/background layering currently relies only on z ordering and opaque fills; no opacity tokens/material standards exist yet: `warships/game/ui/framework/widgets.py:42`.

### Target D Findings: Resize + Present Stability Under Load

High-confidence gaps:
1. Resize events trigger immediate redraw requests, and frontend also applies resize then draws in same cycle; can cause bursty redundant frames during drag-resize: `engine/window/rendercanvas_glfw.py:208`, `engine/runtime/window_frontend.py:65`.
2. Renderer maps design rects using target size every primitive; during rapid resize this multiplies CPU overhead and increases frame misses: `engine/rendering/wgpu_renderer.py:1411`.
3. Present/acquire recovery exists but telemetry is not yet tied to adaptive frame-throttle policy during repeated failures: `engine/rendering/wgpu_renderer.py:952`, `engine/rendering/wgpu_renderer.py:1278`.

Possible but less-likely contributors:
1. `request_draw(self._draw_frame)` plus immediate `request_draw()` startup behavior may enqueue extra first frames depending on backend semantics: `engine/runtime/window_frontend.py:48`.
2. Aspect-mode stretch/contain transitions can expose apparent clipping artifacts if UI assumes fixed coordinates without per-scene containment policy: `engine/rendering/scene_runtime.py:51`.

## Execution Phases (Extended)

### Phase 1: Snapshot + Draw-Work Reduction Core

Implementation:
1. Introduce frame-level snapshot diffing in `WarshipsGameModule` so unchanged UI trees reuse previous `RenderSnapshot`.
2. Remove per-frame deep sanitize for unchanged payloads and reuse immutable command payload blocks.
3. Precompute viewport transform once per frame and apply in batch map pass, not per primitive.
4. Replace per-rect viewport/scissor path with instance-buffer quad batching per pass/layer/material.

User-visible result:
1. Immediate FPS uplift in menu/new-game/preset screens.
2. CPU usage drop without visual change.

Exit:
1. Target: 2.0x to 3.0x FPS improvement versus current baseline in New Game and Preset Manage scenes.

### Phase 2: Static UI Caching + Upload Stability

Implementation:
1. Add retained static geometry buckets (background panels, static board frames, static labels).
2. Keep persistent GPU buffers for static and dynamic streams; remove per-frame buffer re-creation in upload path.
3. Split draw submission into static-first + dynamic-delta second pass.

User-visible result:
1. Idle scenes remain responsive with very low CPU.
2. Scene switches no longer stutter on first few frames.

Exit:
1. Target: additional 1.5x to 2.0x FPS improvement on top of Phase 1 in static-heavy screens.

### Phase 3: Real Text Pipeline (Atlas + Quads)

Implementation:
1. Replace `_text_draw_rects` bitmap rectangles with glyph atlas rasterization and textured quads.
2. Implement glyph run cache keyed by font/size/text.
3. Keep deterministic fallback behavior when system font resolution fails.

User-visible result:
1. Text appears smooth and consistent across sizes.
2. Long labels stop looking pixelated while preserving readability.

Exit:
1. No bitmap-style text in standard runtime paths.
2. No net FPS regression versus post-Phase-2 baseline.

### Phase 4: UI Style Primitive Upgrade

Implementation:
1. Add engine-owned style primitives: rounded rect, stroke rect, gradient fill, optional shadow.
2. Introduce style tokens (surface/base/elevated/accent/text) with deterministic defaults.
3. Migrate Warships screens from hardcoded colors to tokens.

User-visible result:
1. Noticeably richer panel/button depth and board readability.
2. More consistent visual hierarchy across screens.

Exit:
1. Warships main menu, new game, preset manager, and battle HUD all use tokenized styles.

Phase 4 execution note (2026-02-21):
1. Tokenization and style API migration were completed in code.
2. Initial style primitive implementation used CPU-side rect strip composition (many extra packets per visual element).
3. Result: visible artifacts (partial white overlays/unstable composite look) and major FPS regression (~40 FPS class drop in user validation).
4. Emergency mitigation: style effects were gated behind `ENGINE_UI_STYLE_EFFECTS` and defaulted off, restoring stable visuals/performance.
5. Conclusion: architectural migration is present, but Phase 4 visual acceptance is not satisfied in production runtime path yet.
6. Status: Phase 4 marked failed by acceptance gate (performance regression and visual artifact regressions in user validation).

### Phase 4b: Style Primitive Recovery (GPU-Native)

Why this phase is needed:
1. Phase 4 CPU-composed effects are too expensive and visually fragile under current renderer packet model.
2. Rich style effects must be implemented as GPU-native primitives, not expanded into many CPU-side rects.

Implementation:
1. Add native style command kinds in renderer path (single-command primitives):
- `rounded_rect`
- `stroke_rect`
- `gradient_rect`
- `shadow_rect` (or equivalent cheap blurless shadow primitive)
2. Implement shader-backed decode for these primitives in `wgpu_renderer` with bounded parameter payloads.
3. Keep fallback behavior:
- if native style path is unavailable, fallback to plain rect (not multi-strip expansion).
4. Re-enable style effects by default only after perf gate passes.
5. Keep token model unchanged (no Warships-specific rendering rules).

Validation gates:
1. Scene-level packet count delta vs pre-Phase-4 baseline remains within agreed budget.
2. No visual artifacts in main menu/new game/preset manager/battle HUD.
3. No meaningful FPS regression versus pre-Phase-4 baseline in user-tested scenes.

Exit:
1. Rich visual style is enabled by default on GPU-native path.
2. `ENGINE_UI_STYLE_EFFECTS` remains as explicit override/debug control, not as required production safety-off switch.

### Phase 5: Layout and Typography Rules Lock-In

Implementation:
1. Add engine-level text overflow policies (`clip`, `ellipsis`, `wrap-none`) and per-widget selection.
2. Enforce parent-content constraints for child widgets centrally in projection/layout utilities.
3. Remove duplicated ad hoc truncate logic in view modules.

User-visible result:
1. Labels do not overflow controls unexpectedly.
2. Consistent text sizing behavior across all button families.

Exit:
1. All button/text widgets use shared layout policy APIs.

Phase 5 execution note (2026-02-21):
1. Added engine-level text overflow policy surface in `engine.api.ui_primitives.fit_text_to_rect`:
- `ellipsis`
- `clip`
- `wrap-none`
2. Added shared projection helper `project_text_fit(...)` + `TextFitSpec` in `engine.api.ui_projection`.
3. Removed Warships ad hoc `truncate(...)` view helper and migrated affected call sites to shared engine policies/helpers.
4. Parent-content constraint enforcement is now applied centrally in text projection through optional parent clamp in `project_text_fit`.
5. Completed migration of remaining direct text widgets (new-game, preset-manage, status overlay, placement panel, prompt widget) to shared text fit/projection policies.

### Phase 6: Resize/Present Burst Hardening

Implementation:
1. Debounce redraw requests during resize bursts while preserving latest size correctness.
2. Add adaptive recovery policy after repeated acquire/present failures.
3. Record resize/present burst telemetry and expose it in diagnostics summary.

User-visible result:
1. Rapid resize remains visually stable with no white/blank frames.
2. Better responsiveness while dragging window edges.

Exit:
1. No stale/blank rendering in rapid resize stress runs.

Phase 6 execution note (2026-02-21):
1. Added resize burst hardening in `RenderCanvasWindow`:
- coalesces multiple queued resize events into the latest event per poll
- debounces redraw requests during rapid resize bursts (`ENGINE_WINDOW_RESIZE_REDRAW_MIN_INTERVAL_MS`)
- exposes per-burst telemetry via `consume_resize_telemetry()`
2. Added window diagnostics event `window.resize_burst` in `HostedWindowFrontend`, including coalesced/skipped/redraw counters.
3. Added adaptive surface recovery policy in `_WgpuBackend`:
- dynamic retry limit escalation based on failure streak
- temporary recovery backoff window after repeated failures
- adaptive present mode stabilization fallback to `fifo` when repeated failures persist
4. Exposed recovery/burst data in diagnostics summary path:
- `render.profile_frame` now includes acquire/present/reconfigure failure counters plus recovery/backoff/switch counters
- `DiagnosticsMetricsStore` aggregates resize burst + recovery counters into snapshot metrics.

### Phase 7: Runtime Mode and Diagnostics Budget Control

Implementation:
1. Make performance profile presets explicit (dev-debug, dev-fast, release-like).
2. Gate high-volume diagnostics in hot loops by sampling and category filters.
3. Validate loop mode and vsync defaults for release runtime profile.

User-visible result:
1. Predictable FPS behavior between runs/environments.
2. Less accidental perf regression from debug flags.

Exit:
1. Documented, reproducible runtime profile that meets performance target.

Phase 7 execution note (2026-02-21):
1. Added explicit runtime profile presets via `ENGINE_RUNTIME_PROFILE`:
- `dev-debug`
- `dev-fast`
- `release-like`
2. Wired profile defaults into engine config loaders:
- `engine.runtime.debug_config` (metrics/overlay/profiling/log-level defaults)
- `engine.rendering.scene_runtime` (render loop mode/fps cap + vsync defaults)
- `engine.diagnostics.config` (diagnostics buffer/profile/sampling defaults)
3. Added diagnostics budget controls in `DiagnosticHub`:
- category allowlist filter
- per-category sampling rates
- default sampling rate fallback
4. Connected diagnostics budget config from `EngineHost` into `DiagnosticHub` so hot-loop categories are gated centrally.
5. Kept env overrides authoritative: explicit env vars still override profile defaults.

### Phase 8: Final Tuning and Acceptance Sweep

Implementation:
1. Run scene-by-scene profiling and eliminate remaining top offenders.
2. Tune batching/material grouping heuristics.
3. Lock final acceptance checklist and thresholds.

User-visible result:
1. Target-quality visuals plus sustained high FPS in complex scenes.

Exit:
1. Success target: at least 5x FPS improvement versus current reported low (80 FPS scenes -> 400+ class on same machine profile) and materially improved UI fidelity.

### Phase 9: Native-Backed Acceleration and Platform Hardening (Must-Have Final Pass)

Implementation:
1. Text stack migration to native-backed path:
- use `freetype-py` for glyph rasterization and atlas population,
- use `uharfbuzz` for shaping/metrics where applicable,
- keep deterministic fallback/error diagnostics.
2. Render prep data path migration:
- replace Python object-heavy dynamic draw packing with contiguous typed buffers (`numpy` arrays and/or `memoryview`-compatible packed arrays),
- pre-pack instance/vertex payloads in native-friendly formats before GPU upload.
3. Window backend hardening:
- execute direct GLFW path evaluation and, if benchmark confirms, migrate from `rendercanvas` wrapper to direct GLFW ownership while preserving `window_and_panel_policies.md` boundaries.
4. Diagnostics performance hardening:
- replace slow-path diagnostics JSON serialization/export with faster native implementation (e.g. `orjson`) in diagnostics/export paths,
- enforce diagnostics sampling/budget defaults for release-like profile.

User-visible result:
1. Final performance headroom after algorithmic fixes, especially in dense UI/text scenes.
2. More stable frame pacing in long sessions and under diagnostics-enabled workflows.
3. Cleaner window/event-loop control with fewer abstraction-layer surprises.

Exit:
1. Native-backed text and render-prep path are active in production runtime.
2. GLFW/direct backend decision is completed and implemented (or explicitly rejected with benchmark evidence).
3. Faster diagnostics path is active by default for profiling/export tooling.
4. End-state performance and fidelity targets remain met after these platform-level changes.

## Acceptance Criteria

1. Performance:
- Significant CPU reduction in dense UI scenes.
- FPS recovery target met for New Game/List-heavy scenes.

2. Text:
- No blocky fallback appearance in normal runtime.
- Consistent placement/anchor behavior.

3. Visual quality:
- Improved depth/contrast and readability in primary screens.

4. Stability:
- No stale/blank rendering under rapid resize.

5. Process:
- Every implemented improvement is linked to a documented review finding.
