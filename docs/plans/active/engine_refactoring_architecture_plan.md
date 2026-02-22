## Static Check Findings

Date: 2026-02-22

### Execution Readiness Fixes Applied

To make the policy checks executable end-to-end, the following setup blockers were fixed:

1. Added missing policy layer packages:
   - `engine/domain/__init__.py`
   - `engine/bootstrap/__init__.py`
   - `engine/platform/__init__.py`
2. Synced dev dependencies:
   - `uv sync --group dev`

### Scope

Policy-driven deterministic checks executed against `engine.*`:

1. `uv run lint-imports`
2. `uv run python scripts/check_bootstrap_wiring_ownership.py`
3. `uv run python scripts/check_import_cycles.py`
4. `uv run mypy --strict`
5. `uv run xenon --max-absolute B --max-modules A --max-average A engine`
6. `uv run python scripts/check_engine_file_limits.py --soft 600 --hard 900`
7. `uv run ruff check engine --select E722,BLE001`
8. `uv run semgrep --config tools/quality/semgrep/broad_exception_policy.yml engine`
9. `uv run semgrep --config tools/quality/semgrep/domain_literal_leakage.yml engine`
10. `npx --yes jscpd --threshold 5 engine`

### Raw Outputs

All full command outputs are stored in:

`docs/architecture/audits/static_checks/2026-02-22/`

1. `00_policy_static_checks_full_run.txt`
2. `01_lint-imports.txt`
3. `02_bootstrap_wiring_ownership.txt`
4. `03_import_cycles.txt`
5. `04_mypy_strict.txt`
6. `05_xenon.txt`
7. `06_file_limits.txt`
8. `07_ruff_broad_exceptions.txt`
9. `08_semgrep_broad_exceptions.txt`
10. `09_semgrep_domain_leakage.txt`
11. `10_jscpd.txt`

### Per-File Findings (One-by-One)

1. `00_policy_static_checks_full_run.txt`
   - The consolidated runner now executes all configured static gates in one pass, does not short-circuit on first failure, and emits a final failed-check summary.
   - Final full-run failed checks: import-linter, bootstrap wiring ownership, import cycles, xenon, file limits, ruff broad exceptions, semgrep broad exceptions, semgrep domain leakage, jscpd duplication.
2. `01_lint-imports.txt`
   - Import graph analyzed: `99` files, `227` dependencies.
   - Contract verdicts: `1 kept`, `2 broken`.
   - Broken contracts:
     - `engine.api cannot import engine.runtime or engine.platform`
     - `no cross-layer shortcut imports`
   - Key pattern: API factory/wiring modules import runtime implementations; runtime imports API contracts extensively.
3. `02_bootstrap_wiring_ownership.txt`
   - Direct violation: `engine/api/hosted_runtime.py:29` imports `engine.runtime.bootstrap`.
   - Meaning: concrete composition still leaks into API layer.
4. `03_import_cycles.txt`
   - Major SCCs:
     - `SCC(size=63)` spanning API/runtime/rendering/window/ui-runtime/gameplay cluster.
     - `SCC(size=9)` in diagnostics cluster.
   - Additional self-cycles are reported for package roots (`engine.api`, `engine.runtime`, `engine.rendering`, etc.).
5. `04_mypy_strict.txt`
   - `Success: no issues found in 164 source files`.
   - This is the only fully passing static gate in this run.
6. `05_xenon.txt`
   - Complexity gate fails on multiple blocks and modules.
   - Highest-severity hotspot: `engine/rendering/wgpu_renderer.py:2015 draw_packets` rank `F`.
   - Other high-pressure nodes include `engine/runtime/host.py:311 frame` rank `D` and multiple renderer/runtime functions ranked `C`/`D`.
7. `06_file_limits.txt`
   - Soft limit (`600 LOC`) exceeded:
     - `engine/runtime/host.py` (`895`)
     - `engine/runtime/profiling.py` (`646`)
   - Hard limit (`900 LOC`) exceeded:
     - `engine/rendering/wgpu_renderer.py` (`5184`)
8. `07_ruff_broad_exceptions.txt`
   - `73` `BLE001` findings (`except Exception`) across diagnostics/gameplay/rendering/runtime/window.
   - Concentration is heavy in `engine/rendering/wgpu_renderer.py`, with additional clusters in `engine/runtime/profiling.py` and `engine/window/rendercanvas_glfw.py`.
9. `08_semgrep_broad_exceptions.txt`
   - Semgrep scan found `9` blocking findings for silent `except Exception: pass`.
   - Findings are concentrated in:
     - `engine/window/rendercanvas_glfw.py`
     - `engine/rendering/wgpu_renderer.py`
   - Note in output: include-pattern compatibility warning for future Semgrep path anchoring behavior.
10. `09_semgrep_domain_leakage.txt`
   - `1` blocking finding for title-specific literal leakage:
     - `engine/rendering/wgpu_renderer.py:4402` includes `"WARSHIPS 2"`.
   - Same Semgrep include-pattern warning appears.
11. `10_jscpd.txt`
   - Duplication threshold breach:
     - `526` duplicated lines (`5.01%`) vs threshold `5%`.
     - `29` clone groups.
   - Dominant clone families:
     - `engine/api/ui_primitives.py` mirrored in `engine/ui_runtime/*`.
     - runtime overlap between `engine/runtime/bootstrap.py`, `engine/runtime/host.py`, `engine/runtime/ui_space.py`.

### Results Summary

1. `import-linter`: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/01_lint-imports.txt`
   - Summary:
     - `engine.api cannot import engine.runtime or engine.platform`: `BROKEN`
     - `engine.domain cannot import engine.api`: `KEPT`
     - `no cross-layer shortcut imports`: `BROKEN`
   - Meaningful finding: dependency direction violations are broad and include API->runtime wiring plus cross-layer chains through runtime/rendering/window paths.
2. Bootstrap ownership check: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/02_bootstrap_wiring_ownership.txt`
   - Violation: `engine/api/hosted_runtime.py:29` imports `engine.runtime.bootstrap`.
   - Meaningful finding: API layer still performs concrete composition wiring.
3. Import cycle check: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/03_import_cycles.txt`
   - Detected SCCs:
     - one SCC of size `63` spanning `engine.api`, `engine.runtime`, `engine.rendering`, `engine.ui_runtime`, `engine.window`, `engine.gameplay`, etc.
     - one SCC of size `9` in diagnostics package cluster.
   - Meaningful finding: cycle pressure is systemic, not isolated.
4. `mypy --strict`: **Pass**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/04_mypy_strict.txt`
   - Output: `Success: no issues found in 164 source files`.
   - Meaningful finding: type strictness is currently the strongest gate.
5. `xenon` complexity budgets: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/05_xenon.txt`
   - Notable blocks:
     - `engine/rendering/wgpu_renderer.py:2015 draw_packets` rank `F`
     - `engine/runtime/host.py:311 frame` rank `D`
     - `engine/input/input_controller.py:126 build_input_snapshot` rank `D`
   - Notable modules:
     - `engine/runtime/framework_engine.py` rank `B`
     - `engine/runtime/profiling.py` rank `B`
   - Meaningful finding: complexity hotspots align with known god-module areas.
6. LOC limits: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/06_file_limits.txt`
   - Soft limit exceed:
     - `engine/runtime/host.py` `895 LOC`
     - `engine/runtime/profiling.py` `646 LOC`
   - Hard limit exceed:
     - `engine/rendering/wgpu_renderer.py` `5184 LOC`
   - Meaningful finding: decomposition phases are mandatory, not optional.
7. Ruff broad exception policy: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/07_ruff_broad_exceptions.txt`
   - `73` findings (`BLE001`) across renderer/runtime/window/gameplay/diagnostics.
   - Meaningful finding: broad exception handling is pervasive and requires staged replacement with typed handling + telemetry.
8. Semgrep broad exception policy: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/08_semgrep_broad_exceptions.txt`
   - `9` blocking findings (silent `except Exception: pass` patterns), concentrated in:
     - `engine/window/rendercanvas_glfw.py`
     - `engine/rendering/wgpu_renderer.py`
   - Meaningful finding: policy-violating silent fallback behavior remains in runtime-critical paths.
9. Semgrep domain literal leakage: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/09_semgrep_domain_leakage.txt`
   - `1` blocking finding:
     - `engine/rendering/wgpu_renderer.py:4402` contains `"WARSHIPS 2"`.
   - Meaningful finding: explicit title literal leakage still exists in `engine.*`.
10. jscpd duplication threshold: **Fail**
   - Raw output: `docs/architecture/audits/static_checks/2026-02-22/10_jscpd.txt`
   - Result: `5.01%` duplicated lines over threshold `5%` (`29` clone groups).
   - High-value clone clusters:
     - `engine/api/ui_primitives.py` duplicated against `engine/ui_runtime/*` modules.
     - duplication between `engine/runtime/bootstrap.py`, `engine/runtime/host.py`, `engine/runtime/ui_space.py`.
   - Meaningful finding: duplication gate quantitatively confirms UI/runtime dual-ownership drift.

### Static Findings to Feed Refactor Phases

1. Phase 2 (API contract hardening):
   - remove API wiring imports (`engine/api/hosted_runtime.py` bootstrap dependency).
   - resolve import-linter broken contracts for API->runtime and layer shortcuts.
2. Phase 3 (UI runtime consolidation):
   - eliminate `engine/api/ui_primitives.py` runtime implementation duplication.
3. Phase 4 (EngineHost decomposition):
   - split `engine/runtime/host.py` (LOC/complexity violations).
4. Phase 5 (Renderer decomposition):
   - split `engine/rendering/wgpu_renderer.py` (hard LOC + complexity + broad exception concentration + domain literal leakage).
5. Phase 6 (sustainability hygiene):
   - reduce SCC count aggressively.
   - remove silent/broad exception fallbacks where policy disallows them.
   - reduce duplication below `5%`.

## LLM Findings

Date: 2026-02-22  
Policy source: `docs/architecture/codebase_discipline_and_quality_policy.md` section `# 2. LLM Semantic Governance Layer`.

### 2.1 API Ergonomics Review

Observation:
Policy questions answered:
1. Typical workflow in real usage (`warships/game/app/engine_hosted_runtime.py`):
   - construct controller and app adapter,
   - construct `HostedRuntimeConfig` from env-derived values,
   - call `run_hosted_runtime(...)`,
   - inside module factory, call `create_app_render_api(...)` and `create_ui_framework(...)`.
2. Verbosity:
   - top-level hosted boot API is concise for app callers,
   - but composition is split between API facade and runtime internals, creating hidden multi-step behavior.
3. Common operations multi-step vs single-step:
   - simple call at surface, but API wrappers internally proxy to runtime constructors (`engine/api/hosted_runtime.py:29`, `engine/api/hosted_runtime.py:30`, `engine/api/ui_framework.py:40`, `engine/api/ui_framework.py:47`).
4. Parameter consistency:
   - mostly consistent naming (`app`, `renderer`, `layout`), but runtime configuration naming overlaps with app domain naming (`runtime_name`, game/title name env variables in app layer).
5. Config leakage:
   - app call sites still prepare runtime-env-derived values; API facade does not isolate config ownership cleanly.

Risk Level: High

Concrete Recommendation:
1. Preserve one-call ergonomics (`run_hosted_runtime`) but move all concrete runtime imports out of `engine.api.*`.
2. Make API constructors return protocols only; runtime object graph assembly must be bootstrap-owned.
3. Add an explicit hosted composition entrypoint in bootstrap to keep app workflow simple without API/runtime coupling.

Confidence Estimate: High

### 2.2 Domain Leakage by Meaning

Observation:
Policy questions answered:
1. Specific gameplay assumptions present:
   - `engine/api/ui_primitives.py` encodes dual-grid semantics (`primary`/`secondary`) and default 10x10 board-like layout values.
2. Defaults biased toward one profile:
   - fixed origins and cell sizing are pre-tuned to a two-surface board UI profile.
3. Abstractions tuned for naval/grid/2D assumptions:
   - grid targeting and cell helper paths are not neutral primitives.
4. Literal domain leakage:
   - renderer still contains title-specific literal (`engine/rendering/wgpu_renderer.py:4402`, `"WARSHIPS 2"`).

Risk Level: High

Concrete Recommendation:
1. Move grid-target defaults and board-oriented constants from `engine/api/ui_primitives.py` into app/preset layer.
2. Rename/reshape primitives to neutral coordinate/region vocabulary.
3. Remove title-specific literals from renderer seed/prewarm labels and make them data-driven from app layer.

Confidence Estimate: High

### 2.3 Misleading Abstractions

Observation:
Policy questions answered:
1. Class/protocol names vs responsibilities:
   - `EngineHost` name suggests host orchestration but implementation includes diagnostics server, replay/crash export, profiling and snapshot pipeline.
2. Too generic or too specific:
   - `SurfaceHandle.provider: object | None` is too generic for required behavior.
   - UI primitive helpers are too specific to one interaction model.
3. Protocol minimal/correct:
   - `RenderAPI` and `WindowPort` are not minimal-correct for real runtime usage; runtime relies on dynamic optional methods.
4. Internal detail leakage through public API:
   - runtime-specific behavior leaks through API wrappers and duck-typed extensions.

Risk Level: High

Concrete Recommendation:
1. Split protocols into required and optional capability interfaces (style-render, resize-aware window, typed surface provider).
2. Remove required-path `getattr`/`hasattr` checks by making capability contracts explicit.
3. Decompose `EngineHost` responsibilities into explicit services with narrow contracts.

Confidence Estimate: High

### 2.4 Performance Risk Heuristics

Observation:
Policy questions answered:
1. Objects rebuilt per call:
   - shortcut resolution reconstructs command map in `_resolve_shortcut_button_command` (`engine/runtime/framework_engine.py:189`).
   - render snapshot transformations/sanitization are repeatedly handled in host/ui-space paths.
2. Containers reconstructed in hot paths:
   - per-frame event routing and snapshot-path transformations use repeated per-frame object creation.
3. Unnecessary deep copying:
   - snapshot freezing/scaling pipelines in host/ui-space indicate repeated immutable reshaping under frequent frames.
4. N^2 risk:
   - renderer packet processing and repeated dispatch chains in `wgpu_renderer` show high branch/loop density (`draw_packets` complexity rank `F`).

Risk Level: High

Concrete Recommendation:
1. Replace per-event command-map reconstruction with precompiled shortcut lookup.
2. Consolidate snapshot transform/sanitize/freeze into single reusable runtime service with identity-based fast-paths.
3. Split renderer packet path into typed dispatch units and benchmark each split manually per policy.

Confidence Estimate: High

### 2.5 Inconsistent Error Semantics

Observation:
Policy questions answered:
1. Exception model consistency:
   - inconsistent; mix of rethrow-with-metrics (`engine/gameplay/update_loop.py`) and silent/pass fallback (`engine/window/rendercanvas_glfw.py` and renderer paths).
2. Retry logic centralized:
   - not centralized; retry/fallback behavior appears ad-hoc in renderer/window paths.
3. Errors silently transformed:
   - yes; semgrep reports silent `except Exception: pass` blocks (9 findings).
4. Internal exceptions leaking outside boundary:
   - yes in selected paths (gameplay step rethrows raw caught exceptions after metrics increments).

Risk Level: High

Concrete Recommendation:
1. Establish per-layer error contract: typed exceptions, allowed fallback categories, mandatory telemetry fields.
2. Remove silent catch-pass first in window/backend bridge and renderer backend integration.
3. Normalize update-loop and host error propagation to explicit boundary exception envelopes.

Confidence Estimate: High

### 2.6 Abstraction Depth Assessment

Observation:
Policy questions answered:
1. Too many thin wrappers:
   - yes; `engine/api/ui_framework.py` and `engine/api/hosted_runtime.py` primarily proxy to runtime constructors.
2. Indirection excessive vs feature size:
   - yes in API->runtime factory wrappers and broad barrel re-export surfaces.
3. Boilerplate dominating core logic:
   - high in public export barrels and compatibility proxy helpers.
4. Wrapper chains without value:
   - present where wrappers only forward arguments and introduce coupling.

Risk Level: Medium-High

Concrete Recommendation:
1. Convert proxy wrappers to either true adapters (adding value) or delete them.
2. Reduce barrel surfaces to stable curated exports; move secondary symbols to explicit submodules.
3. Use bootstrap composition as primary integration point instead of API wrapper chains.

Confidence Estimate: High

### 2.7 Config Ownership Drift (Semantic)

Observation:
Policy questions answered:
1. Config values creeping into runtime logic:
   - yes; direct env reads are embedded in runtime/renderer/window behavior paths.
2. Feature flag proliferation:
   - high; `engine.*` currently contains `88` unique `ENGINE_*`/`WARSHIPS_*` tokens.
3. Environment-dependent defaults:
   - yes; same key parsed in multiple modules with potentially divergent fallback behavior (`ENGINE_UI_RESOLUTION` in runtime and renderer).
4. Hidden ambient-state dependency:
   - yes; import-time/env-captured toggles and ad-hoc `os.getenv` calls affect runtime behavior.

Risk Level: High

Concrete Recommendation:
1. Introduce typed central config registry and resolve env exactly once at bootstrap.
2. Inject immutable config snapshots into host, renderer, window, and profiling subsystems.
3. Remove duplicated resolution/env parsers and enforce shared helper implementation.

Confidence Estimate: High

### 2.8 Refactor Opportunity Identification

Observation:
Modules to split:
1. `engine/rendering/wgpu_renderer.py` (size, complexity, error handling density).
2. `engine/runtime/host.py` (multi-domain responsibility concentration).
3. `engine/runtime/profiling.py` (complexity + config/env handling).

Extractable shared behaviors:
1. Snapshot scaling/sanitization/freeze pipeline shared across host/ui-space/bootstrap paths.
2. Env/config parser helpers (`_env_*`, `_flag`, `_int`) across runtime/rendering/window.
3. UI primitive behavior duplicated between `engine/api/ui_primitives.py` and `engine/ui_runtime/*`.

Redundant layers:
1. API factory wrappers that directly instantiate runtime objects.
2. Oversized barrel exports in `engine/api/__init__.py` and `engine/runtime/__init__.py`.

Collapsible boilerplate:
1. Repeated command-map construction for shortcut routing.
2. Repeated exception/fallback scaffolding in backend boundary code.
3. Repeated transformation helpers in render snapshot handling.

Risk Level: High

Concrete Recommendation:
1. Phase-aligned executable order:
   - move API runtime wiring from `engine/api/hosted_runtime.py` and `engine/api/ui_framework.py` to bootstrap composition.
   - migrate `engine/api/ui_primitives.py` to contracts/shims only, canonicalize runtime logic in `engine/ui_runtime/*`.
   - split `engine/runtime/host.py` into frame service, diagnostics service, and snapshot pipeline service.
   - split `engine/rendering/wgpu_renderer.py` into packet dispatcher, backend lifecycle, text subsystem, and compatibility adapters.
2. Mandatory per-step guardrails:
   - import-linter broken contract count trends downward,
   - SCC count and max SCC size decrease monotonically,
   - duplication drops below `5%`,
   - broad/silent exception violations trend down with no regressions.

Confidence Estimate: High

