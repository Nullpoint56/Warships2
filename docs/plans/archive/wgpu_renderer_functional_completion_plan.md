# WGPU Renderer Functional Completion Plan

Date: 2026-02-20
Status: Active remediation plan
Scope: Close the gap between structural migration completion and actually working runtime rendering.

## Why This Plan Exists

The wgpu migration removed `pygfx` and satisfied architecture/policy checks, but the backend is still functionally incomplete for real runtime rendering.

Observed symptom:
- Runtime shows mostly black/white placeholder output instead of full Warships UI.

Root cause class:
- Rendering scaffolding exists, but real primitive/text rasterization and robust surface present behavior are incomplete.

## Fact-Checked Current Gaps

1. Geometry path is placeholder, not command-driven:
- Commands are sorted/translated, but draw encoding is still effectively placeholder output.

2. Surface/present path needs production hardening:
- Acquire/present/reconfigure behavior is not yet fully robust under live runtime conditions.

3. Text path is incomplete:
- Font discovery exists, but complete glyph layout/atlas/render behavior is not yet sufficient for reliable UI text.

4. Validation leaned too heavily on structure:
- Contract/policy checks passed while true visual/runtime behavior remained broken.

## Warships-Specific vs Engine-General

Engine-general (must be solved once, reusable):
- Command-to-geometry emission for `fill_window`, `rect`, `grid`, `text`
- Buffer uploads, bind state, and draw encoding
- Surface acquire/present/reconfigure robustness
- Text rendering pipeline

Warships-specific (acceptance surface only):
- Menu/board/ship marker/hit-miss/overlay/resize parity confirmation

Conclusion:
- This is primarily an engine renderer completion problem, not a Warships-only problem.

## Non-Negotiable Done Criteria

1. Warships launches with readable, interactive UI in non-headless mode.
2. Snapshot commands visibly map to runtime primitives.
3. Resize and present behavior are stable.
4. Text is readable across core UI surfaces.
5. Headless/non-headless startup policy remains correct.

## Execution Phases (Implementation-First, User-Visible)

## Phase 1: Geometry Comes Back

Sub-phase 1.1 (background + panel quads):
1. Implement real quad rendering for `fill_window` and `rect`.
2. Remove effective placeholder-only draw behavior for these commands.
3. Manual checkpoint:
- Launch app and confirm non-black background plus visible UI panels/buttons.

Sub-phase 1.2 (board grid lines):
1. Implement real grid geometry (`grid`) with deterministic thickness.
2. Keep deterministic layer/pass ordering.
3. Manual checkpoint:
- Start a game and confirm board grid lines render and align correctly.

Sub-phase 1.3 (stability and transitions):
1. Harden geometry uploads (hybrid path).
2. Preserve one-frame-in-flight and ordering policies.
3. Manual checkpoint:
- Navigate menu -> placement -> battle and verify geometry remains correct.

Phase 1 exit:
1. `fill_window`/`rect`/`grid` visibly render in runtime.
2. You can confirm geometry is no longer placeholder output.

## Phase 2: Text Becomes Readable

Sub-phase 2.1 (minimum text path):
1. Implement usable text layout for current `RenderCommand` payload.
2. Render menu/button/status text in expected positions.
3. Manual checkpoint:
- Main menu labels are readable and centered as expected.

Sub-phase 2.2 (atlas + blending correctness):
1. Implement glyph atlas upload/sampling for runtime text.
2. Fix text alpha/blend behavior in linear/sRGB flow.
3. Manual checkpoint:
- Overlay and button text render cleanly (no white blocks/alpha artifacts).

Sub-phase 2.3 (fallback behavior):
1. Make fallback font behavior deterministic.
2. Preserve clear hard-fail behavior when no usable system font is available.
3. Manual checkpoint:
- Normal local run has readable text; forced bad font config fails with explicit diagnostics.

Phase 2 exit:
1. Core Warships text is readable in runtime.
2. Text remains stable across screen transitions.

## Phase 3: Present/Resize Reliability

Sub-phase 3.1 (real present path):
1. Finalize acquire/draw/present flow on window-provided surface.
2. Remove residual offscreen-only assumptions.
3. Manual checkpoint:
- Frame presentation consistently updates without stale/blank frames.

Sub-phase 3.2 (resize hardening):
1. Harden reconfigure behavior for rapid resize.
2. Preserve required reuse/fallback policies.
3. Manual checkpoint:
- Rapid resize keeps UI intact without white/blank corruption.

Sub-phase 3.3 (vsync/present modes):
1. Validate present mode fallback with vsync on/off.
2. Keep diagnostics payload complete for failures/reconfigure.
3. Manual checkpoint:
- Runtime remains stable under both `ENGINE_RENDER_VSYNC=1` and `ENGINE_RENDER_VSYNC=0`.

Phase 3 exit:
1. Resize/present behavior is stable and visually correct.

## Phase 4: Final Parity and Lock-In

Sub-phase 4.1 (manual parity sweep):
1. Manually verify:
- Menu screens
- Board grid
- Ship markers
- Hit/miss states
- Overlay/debug UI
- Resize behavior
2. Record and fix remaining deltas.

Sub-phase 4.2 (regression lock):
1. Add/keep minimal automated locks for placeholder-regression prevention.
2. Keep CI/runtime checks aligned with real behavior.
3. Manual checkpoint:
- Final full gameplay walkthrough confirms parity.

Phase 4 exit:
1. Manual parity checklist fully passes.
2. Regression locks prevent a return to placeholder rendering.

## Manual Verification Script (Run After Every Sub-phase)

Run:
- `uv run python -m warships.main`

Verify:
1. Main menu visible with readable text labels.
2. Buttons/panels have expected colors and positions.
3. Placement board shows visible grid and ships.
4. Battle board shows hit/miss updates.
5. Window resize does not produce blank/white-only frame.

Stop rule:
- If any checkpoint fails, do not proceed to next sub-phase.

## Implementation Boundaries

1. Do not reintroduce `pygfx`.
2. Do not leak `wgpu` types into `engine/api/*`.
3. Keep renderer main-thread model for this remediation.
4. Preserve headless mode behavior.
