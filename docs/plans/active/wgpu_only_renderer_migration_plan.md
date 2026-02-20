# WGPU-Only Renderer Migration Plan

Date: 2026-02-20
Scope: Replace `pygfx` renderer implementation with pure `wgpu`, keep window/input policy boundaries intact, then remove `pygfx` from runtime and dependencies.

## Current State (Fact-Checked)

1. `pygfx` is still required in `pyproject.toml`.
2. Runtime boot path is still pygfx-named and wired:
- `engine/runtime/bootstrap.py` -> `run_pygfx_hosted_runtime(...)`
- `engine/runtime/pygfx_frontend.py` -> `create_pygfx_window(...)`
- `engine/api/hosted_runtime.py` + `engine/api/__init__.py` export `run_pygfx_hosted_runtime`.
3. Renderer is pygfx scene graph based:
- `engine/rendering/scene.py` imports and uses `pygfx`.
4. Window/input architecture is already mostly policy-aligned:
- `engine/window/rendercanvas_glfw.py` emits normalized window/input events.
- `engine/input/input_controller.py` builds immutable `InputSnapshot`.

## Target End State

1. No `pygfx` dependency and no `import pygfx` in active engine/warships runtime paths.
2. Renderer backend is pure `wgpu`, still consumed through `RenderAPI`.
3. Dependency direction remains:
- `WindowLayer -> Surface -> RenderBackend`.
4. Frame contract remains:
- `simulate()` -> `build_render_snapshot()` -> `renderer.render_snapshot(snapshot)`.

## Locked Technical Decisions

1. Text rendering strategy:
- `freetype` + engine-owned glyph atlas + quad batching (no `pygfx` text path).
- Rationale: strongest architecture fit and performance/complexity balance for this engine.

2. Surface attachment contract:
- opaque `SurfaceHandle` carrying backend-native surface provider needed by the renderer.
- Rationale: keeps `WindowLayer -> Surface -> RenderBackend` explicit while avoiding backend type leakage in engine APIs.

3. Runtime/API migration strategy:
- hard cut to backend-neutral names (`run_hosted_runtime`, neutral frontend module names) with no long-lived compatibility alias.
- Rationale: avoids transitional debt and aligns with allowed breaking-change policy.

## Locked Low-Level Decisions

1. Font scope:
- Option: primary + fallback stack (initial multi-font fallback, not full dynamic registry).
- Why: strong runtime coverage without the complexity of a full registry in first delivery.

2. Text shaping level:
- Option: hybrid path (basic default + optional advanced shaping path).
- Why: keeps default fast/simple while preserving architecture for complex script support.

3. Glyph atlas policy:
- Option: growable atlas with hard cap.
- Why: avoids brittle overflow failures while keeping allocator/eviction complexity controlled.

4. Pipeline layout:
- Option: two-pipeline split (geometry pipeline + text pipeline).
- Why: clean separation for text sampling/blending needs with low orchestration overhead.

5. Buffer upload strategy:
- Option: hybrid upload path (full rewrite for small payloads, ring-buffer/suballocation above threshold).
- Why: practical startup simplicity with scalable behavior under heavier frame load.

6. Present mode mapping:
- Option: explicit policy table with deterministic fallback chain per engine mode.
- Why: predictable cross-platform behavior aligned with deterministic architecture goals.

7. Surface/device loss policy:
- Option: auto-reconfigure/recover with bounded retries and diagnostics.
- Why: robust production behavior without excessive recovery-state complexity.

8. Rendering verification strategy:
- Option: hybrid verification (structural/diagnostic assertions as hard gate + normalized golden subset).
- Why: stable CI signal with targeted visual regression protection.

## Locked Program-Level Execution Decisions

1. Platform scope:
- Cross-platform support is required now (no Windows-only temporary cut).
- Migration work must keep runtime viable on supported desktop platforms.

2. Feature parity scope:
- Target parity is `pygfx` behavior required by Warships game context, not full generic `pygfx` reimplementation.
- Renderer migration should avoid scope creep into non-Warships capabilities unless policy-critical.

3. Performance objective:
- No fixed frame-time budget is imposed.
- All implementation phases must choose the highest-performance pure-Python approach available without custom C/Rust extensions, `numba`, or `cython`.

4. Diagnostics schema compatibility:
- Schema compatibility may be broken during migration.
- Tests should validate correctness and observability coverage, not old schema stability.

5. Git/commit workflow:
- One phase equals one commit on the same branch.
- Agent does not handle push orchestration.

6. WGPU init failure behavior and headless mode:
- Add/configure engine headless toggle.
- If headless is enabled: runtime can run without renderer initialization.
- If headless is disabled and wgpu init fails: raise detailed hard exception and stop engine.

## Final Pre-Execution Concretizations

1. Headless config surface:
- Use existing engine environment-variable configuration pattern and precedence model.
- Canonical flag: `ENGINE_HEADLESS`.
- Truthy values: `1`, `true`, `yes`, `on` (case-insensitive); otherwise false.
- Default: non-headless (`ENGINE_HEADLESS=0` behavior).

2. WGPU backend policy:
- Target backends: Vulkan, Metal, DX12.
- Backend preference order prioritizes Vulkan where available.

3. Font assets and asset pipeline scope:
- No new font assets are bundled in this migration.
- Text uses OS/system-installed default font fallback lists by platform.
- In non-headless mode, if no suitable system font is found, startup fails with a detailed hard exception.
- No dedicated asset pipeline/service pre-work is required for starting migration; text implementation remains renderer-internal for this scope.

4. Warships parity acceptance scope:
- Required parity surfaces include:
  - menu screens
  - board grid
  - ship markers
  - hit/miss states
  - overlays/debug UI
  - resize behavior.

5. Testing strategy during implementation:
- Do not freeze a single global test command up-front.
- Each phase must run the tests relevant to changed code and address regressions discovered during implementation.

6. Render command model scope:
- No new `RenderCommand.kind` values unless absolutely required to satisfy migration correctness.

7. Thread model during migration:
- Renderer remains main-thread only during this migration.
- Thread readiness is preserved architecturally, but no render-thread implementation is introduced in scope.

8. Non-headless init failure diagnostics minimum payload:
- Must include adapter information, selected backend, attempted surface/present format, platform/runtime context, and stack/exception details.

## Phase Plan

## Phase 0: Guardrails

### Work
1. Add test guard that fails on `import pygfx` in `engine/` and `warships/` runtime modules.
2. Lock current diagnostics event names used by runtime/render integration tests.
3. Freeze baseline test subset for rendering/window behavior.
4. Add boundary test that fails if `engine/api/*` imports `wgpu` directly.

### Exit Criteria
1. Guard test active and enforced in CI.
2. Baseline suite green before backend swap.
3. API/backend boundary guard active.

### Locked Constraints Applied
1. Cross-platform guard checks must run on supported OS targets.
2. Add headless/non-headless startup contract checks, including non-headless hard-fail diagnostics shape.
3. Allow diagnostics schema updates; validate coverage instead of backward schema compatibility.

---

## Phase 1: Introduce New WGPU Renderer Backend

### Work
1. Add `engine/rendering/wgpu_renderer.py` implementing `RenderAPI`.
2. Backend internals are private to rendering package:
- device/surface/pipeline setup
- pass encoder
- snapshot command translator.
3. Keep engine API unchanged:
- no `wgpu` types leaking into `engine/api/*`.

### Exit Criteria
1. New renderer can render empty frame and simple rect/text/grid snapshot path.
2. `RenderSnapshot` contract unchanged.

### Locked Constraints Applied
1. Text path must use system-font fallback (no bundled font assets).
2. Keep command model stable (`RenderCommand.kind` unchanged unless absolutely required).
3. Implement best-performance pure-Python approach; no C/Rust extensions, `numba`, or `cython`.
4. Renderer remains main-thread only.

---

## Phase 2: Surface Attachment and Window Contract Wiring

### Work
1. Wire renderer construction from window-provided surface handle/object only.
2. Update bootstrap composition in `engine/runtime/bootstrap.py`:
- create window layer
- create surface from window layer
- attach renderer to surface.
3. Ensure renderer does not own window lifecycle/event loop.

### Exit Criteria
1. Renderer no longer constructs window/canvas.
2. Runtime composition clearly follows window policy dependency direction.

### Locked Constraints Applied
1. Use opaque `SurfaceHandle` contract for renderer attachment.
2. Keep backend preference policy (Vulkan prioritized, then Metal/DX12 where applicable).
3. Apply `ENGINE_HEADLESS` behavior in runtime wiring:
   - headless enabled: allow no-renderer path
   - headless disabled: wgpu init failure is hard exception.

---

## Phase 3: Port Frame Lifecycle and Pass Pipeline

### Work
1. Keep explicit stage sequence in new renderer:
1. `begin_frame()`
2. build batches
3. execute passes
4. `present()`
5. `end_frame()`
2. Preserve retained + immediate mixed-mode behavior by merging into batch stage.
3. Preserve pass ordering model (`world`, `overlay/ui`, `post_*`).

### Exit Criteria
1. Stage diagnostics emitted and asserted by tests.
2. Deterministic pass execution tests pass.

### Locked Constraints Applied
1. Preserve Warships parity scope only (no generic pygfx feature expansion).
2. Two-pipeline layout (geometry + text) and hybrid buffer upload strategy must be followed.
3. Keep renderer main-thread only, while preserving snapshot thread-readiness architecture.

---

## Phase 4: Resize, DPI, and Surface Reconfigure

### Work
1. Handle normalized `WindowResizeEvent` in renderer with physical size + dpi.
2. Reconfigure surface on resize, update viewport/projection deterministically.
3. Preserve device reuse on resize (no device recreation workaround).

### Exit Criteria
1. Resize diagnostics tests pass.
2. Explicit DPI/logical/physical policy behavior verified in tests.

### Locked Constraints Applied
1. Surface/device recovery uses bounded retry with diagnostics.
2. Present mode mapping follows explicit policy table with deterministic fallback chain.
3. Non-headless failure diagnostics include adapter/backend/format/platform/stack fields.

---

## Phase 5: Rendering Policy Hardening on New Backend

### Work
1. Enforce color policy:
- linear internal math
- sRGB presentation/swapchain.
2. Enforce one-frame-in-flight baseline.
3. Enforce deterministic ordering:
- stable sort by layer + tie-break keys.
4. Ensure renderer performs no asset I/O in runtime path.

### Exit Criteria
1. Policy-guard tests pass for color, ordering, frames-in-flight, and no asset I/O.

### Locked Constraints Applied
1. Font/text exception remains scoped to system font discovery + glyph atlas only.
2. No general asset/material service responsibilities move into renderer.
3. Hybrid verification strategy applies (structural hard gate + normalized golden subset).

---

## Phase 6: Rename Runtime Entry Points to Backend-Neutral Names

### Work
1. Rename frontend module:
- `engine/runtime/pygfx_frontend.py` -> `engine/runtime/window_frontend.py`.
2. Rename bootstrap API:
- `run_pygfx_hosted_runtime(...)` -> `run_hosted_runtime(...)`.
3. Update call sites:
- `engine/api/hosted_runtime.py`
- `engine/api/__init__.py`
- `warships/game/app/engine_hosted_runtime.py`
- tests under `tests/engine/unit/runtime/` and `tests/warships/unit/app/`.

### Exit Criteria
1. No active runtime references to `pygfx_*` names.

### Locked Constraints Applied
1. Hard-cut rename strategy: no long-lived compatibility alias.
2. Keep one-phase one-commit discipline on same branch.
3. Continue phase-local testing based on changed code.

---

## Phase 7: Remove Legacy PYGFX Renderer Code

### Work
1. Remove or archive old pygfx renderer modules from active path:
- `engine/rendering/scene.py`
- related pygfx-specific retained helpers if no longer needed.
2. Replace tests tied to pygfx internals with backend-agnostic behavior tests.
3. Remove `pygfx` from runtime metadata collection in `engine/runtime/host.py`.

### Exit Criteria
1. No `import pygfx` in engine runtime path.
2. Rendering tests validate behavior, not pygfx implementation details.

### Locked Constraints Applied
1. Preserve Warships feature parity list as acceptance baseline.
2. Keep command kind set stable unless absolutely required.
3. Maintain cross-platform viability in replacement tests.

---

## Phase 8: Dependency and Documentation Cleanup

### Work
1. Remove `pygfx` from `pyproject.toml` dependencies and mypy overrides.
2. Update docs referencing pygfx runtime:
- `docs/architecture/system_overview.md`
- operations docs that mention pygfx packaging/runtime.
3. Add a CI guard (grep/import boundary test) blocking reintroduction.

### Exit Criteria
1. `pygfx` absent from dependencies, runtime code, and active docs.
2. Full quality suite green.

### Locked Constraints Applied
1. CI checks must enforce no `pygfx` reintroduction.
2. Updated docs must reflect `ENGINE_HEADLESS` behavior and non-headless hard-fail semantics.
3. Diagnostics schema changes are allowed, but observability coverage must remain policy-complete.

## Code Work Map

1. `engine/rendering/`:
- add `wgpu_renderer.py`
- shift public export in `engine/rendering/__init__.py`.
2. `engine/runtime/`:
- update `bootstrap.py` to new renderer and neutral frontend.
- replace `pygfx_frontend.py` with neutral module.
3. `engine/window/`:
- keep ownership of event loop + normalized events + surface provisioning.
4. `engine/api/`:
- rename hosted runtime public entry point.
5. `warships/game/app/`:
- switch to neutral hosted runtime call.
6. `tests/`:
- migrate runtime/rendering tests to new module names and backend-agnostic assertions.

## Policy Compliance Checklist (Must Be Green Before Declaring Done)

1. Rendering policy:
- immutable `RenderSnapshot` consumption only
- explicit frame lifecycle stages
- deterministic ordering
- resize reconfigure without device recreation
- linear internal/sRGB presentation
- one frame in flight
- no renderer asset I/O.

2. Window/panel policy:
- window layer owns loop/lifecycle
- renderer only attaches to provided surface
- normalized resize/dpi events flow window -> renderer
- window diagnostics coverage remains intact.
