# Architecture refactoring template

This document is a template for doing architectural refactors of the engine. It contains two main sections
- Static Check Findings: Signals collected from static checkers
- LLM Check Findings: LLM executed check signals

Each Check finding part contains these fields:
- Evaluations: Raw output interpretations (very verbose to not miss details)
- Investigation: Raw output signals are rarely the ones we need to react on. They usually hide deeper issues. Because of that, investigation section is an investigation of why the Raw check signals appeared.
- Proposed fixes: Investigation reveals root causes, proposed fixes are higher level decisions and documented approaches on how the identified root causes will be fixed.
- Refactoring Phase-Plan: Proposed fixes will be broken down from high level plans into low level actionable, phase by phase fix executions. Phase plans are specific to Static and LLM check execution, and they contain a list of phases with actionable items derived from the specific check type's proposed fixes section.

There is also a shared execution tracking chapter named Global Refactor status, where progress is tracked in a shared way.


## Static Check Findings

### Evaluations
Static check execution date: 2026-02-22  
Static check run id: `2026-02-22_175415_static_eval`  
Raw output root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_175415_static_eval/`

Executed checks and evaluation results:
1. `lint-imports` -> `01_lint-imports.txt` -> Pass
- Output reports `Contracts: 3 kept, 0 broken`.
- Kept contracts:
- `engine.api` does not import `engine.runtime` or `engine.platform`.
- `engine.domain` does not import `engine.api`.
- `no cross-layer shortcut imports` is kept.

2. `check_bootstrap_wiring_ownership.py` -> `02_bootstrap_wiring_ownership.txt` -> Pass
- No violations emitted in output.

3. `check_import_cycles.py` (strict) -> `03_import_cycles_strict.txt` -> Fail
- Reports a large strongly connected component `SCC(size=69)` spanning `engine.api`, `engine.runtime`, `engine.sdk`, `engine.rendering`, `engine.window`, `engine.diagnostics`, and related modules.
- Reports multiple self-cycles at package roots (`engine`, `engine.api`, `engine.runtime`, etc.).

4. `check_import_cycles.py --allow-cycles --baseline ...` -> `04_import_cycles_budget.txt` -> Fail
- Budget regression detected:
- `max_scc_size` regressed to `69`, baseline was `63`.

5. `check_api_runtime_factories.py` -> `05_api_runtime_factories.txt` -> Pass
- No violations emitted in output.

6. `mypy --strict` -> `06_mypy_strict.txt` -> Pass
- `Success: no issues found in 171 source files`.

7. `xenon --max-absolute B --max-modules A --max-average A engine` -> `07_xenon.txt` -> Fail
- Multiple block complexity violations remain (`C`/`D`/`F`).
- Notable hotspot still present: `engine/rendering/wgpu_renderer.py` with severe complexity entries (including rank `F` in earlier lines of output).
- Module-level budget violations remain (`B` rank modules listed in output).

8. `check_engine_file_limits.py --soft 600 --hard 900` -> `08_file_limits.txt` -> Fail
- Soft limit exceeded:
- `engine/runtime/profiling.py` at `646 LOC`.
- Hard limit exceeded:
- `engine/rendering/wgpu_renderer.py` at `5184 LOC`.
- `engine/runtime/host.py` at `901 LOC`.

9. `check_barrel_exports.py` -> `09_barrel_exports.txt` -> Fail
- `engine/api/__init__.py` export budget exceeded: `129 > 120`.
- `engine/runtime/__init__.py` flagged for mixed layer barrel imports (`engine.api.*` and `engine.runtime.*` together).

10. `check_env_read_placement.py` -> `10_env_read_placement.txt` -> Fail
- Many env reads outside allowed config/bootstrap ownership.
- Concentrated in:
- `engine/rendering/wgpu_renderer.py`
- `engine/runtime/host.py`
- `engine/runtime/profiling.py`
- `engine/runtime/ui_space.py`
- `engine/window/rendercanvas_glfw.py`
- Additional findings in `engine/runtime/entrypoint.py`, `engine/runtime/framework_engine.py`, `engine/runtime_profile.py`, `engine/window/factory.py`.

11. `ruff check engine --select E722,BLE001` -> `11_ruff_broad_exceptions.txt` -> Fail
- `73` broad exception findings (`BLE001`) reported.
- Findings include `engine/window/rendercanvas_glfw.py` and other runtime paths.

12. `semgrep --error --config broad_exception_policy.yml engine` -> `12_semgrep_broad_exceptions.txt` -> Fail
- Semgrep reports blocking silent broad exception patterns (`except Exception: pass`) in runtime/window paths.

13. `semgrep --error --config domain_literal_leakage.yml engine` -> `13_semgrep_domain_leakage.txt` -> Fail
- `1` blocking finding:
- `engine/rendering/wgpu_renderer.py:4402` literal `"WARSHIPS 2"`.

14. `semgrep --error --config protocol_boundary_rules.yml engine` -> `14_semgrep_protocol_boundary.txt` -> Fail
- Blocking boundary capability/reflection findings remain.
- Output highlights reflection-based boundary checks in runtime frontend paths and renderer capability probing.

15. `check_domain_semantic_leakage.py` -> `15_domain_semantic_hardening.txt` -> Fail
- Domain semantic literals in engine API still detected:
- `engine/api/ui_primitives.py` (`primary`, `secondary`, `grid_size = 10`).

16. `jscpd --threshold 5 engine` -> `16_jscpd_threshold.txt` -> Fail
- Duplicate ratio reported as `9.21%` over threshold `5%`.
- Clone groups remain broad across engine modules.

17. `check_duplicate_cluster.py` -> `17_duplicate_cluster.txt` -> Fail
- Cluster-specific duplicate gate violation remains:
- `28.07%` duplicate ratio over required `0%` threshold for targeted cluster.
- Repeated overlap between `engine/api/ui_primitives.py` and `engine/ui_runtime/*`.

18. `check_boundary_dto_purity.py` -> `18_boundary_dto_purity.txt` -> Pass
- No violations emitted in output.

19. `check_feature_flag_registry.py` -> `19_feature_flag_registry.txt` -> Fail
- Missing registry metadata reported for `WARSHIPS_DEBUG_UI` (referenced from `engine/runtime/entrypoint.py:43`).

20. `check_state_mutation_ownership.py` -> `20_state_mutation_ownership.txt` -> Fail
- Mutable module-level globals and explicit `global` writes still present.
- Key files:
- `engine/rendering/wgpu_renderer.py`
- `engine/runtime/logging.py`
- `engine/runtime/profiling.py`
- `engine/runtime/ui_space.py`
- `engine/runtime_profile.py`

21. `check_exception_observability.py` -> `21_exception_observability.txt` -> Fail
- Broad exception handlers lacking required observability calls remain in:
- `engine/runtime/host.py`
- `engine/runtime/profiling.py`
- `engine/runtime/ui_space.py`
- `engine/window/rendercanvas_glfw.py`

22. `check_public_api_surface.py` -> `22_public_api_surface.txt` -> Fail
- API surface drift detected.
- Added symbol:
- `EngineModule`
- Removed symbols include multiple legacy runtime factory/bootstrap exports:
- `configure_logging`, `run_hosted_runtime`, `create_*` factory functions (`create_event_bus`, `create_update_loop`, `create_ui_framework`, etc.).

23. `policy_static_checks.py` -> `23_policy_static_checks_full_run.txt` -> Fail
- Consolidated runner failed with the same failing gates found above.
- Final failed checks summary includes:
- public API drift
- import cycles (strict + budget)
- complexity budgets
- LOC limits
- barrel export budget
- env read placement
- feature flag registry
- state mutation ownership
- broad exception policy (ruff + semgrep)
- exception observability
- domain literal leakage
- protocol boundary semgrep
- domain semantic hardening
- duplication threshold
- duplicate cluster gate

S2 follow-up execution addendum (run id: `2026-02-22_194137_S2`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_194137_S2/`):
- `S2_01_env_read_placement.txt` -> Pass
- `S2_02_mypy_strict.txt` -> Pass
- `S2_03_lint_imports.txt` -> Pass
- `S2_04_feature_flag_registry.txt` -> Fail
- New failure signal details:
- `check_feature_flag_registry` was enhanced to detect centralized config helper calls (`_text/_int/_float/_csv/_raw`) and now reports missing registry metadata entries for actively used flags.
- Root artifact with full list remains: `S2_04_feature_flag_registry.txt`.
- Practical implication:
- config-ownership migration is structurally complete, but governance metadata must be reconciled before policy convergence.

S2.b execution addendum (run id: `2026-02-22_195124_S2b`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_195124_S2b/`):
- `S2b_01_feature_flag_registry.txt` -> Pass
- `S2b_02_policy_static_checks.txt` -> Fail (expected carry-over from later phases: cycles/complexity/LOC/state mutation/exception policy)
- Resolution result:
- feature flag registry reconciliation completed by adding missing metadata entries for all newly surfaced centralized-config flags in `tools/quality/budgets/feature_flags_registry.json`.
- Practical implication:
- S2 governance follow-up is closed; remaining policy failures are out-of-scope for S2 and remain tracked under S3+ phases.

S2.c exhaustive closure verification addendum (run id: `2026-02-22_195809_S2c`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_195809_S2c/`):
- `S2c_00_target_env_reads_scan.txt` -> Expected centralized env ownership only (`engine/runtime/config.py`)
- `S2c_01_target_env_helpers_scan.txt` -> Pass (`_env_*` helper layer removed from S2 target modules)
- `S2c_02_env_read_placement.txt` -> Pass
- `S2c_03_mypy_strict.txt` -> Pass
- `S2c_04_lint_imports.txt` -> Pass
- `S2c_05_feature_flag_registry.txt` -> Pass
- Resolution result:
- S2 now satisfies both gate-level completion and literal execution-step completion (including removal of local `_env_*` helper layer from targeted modules).

S3 execution addendum (run id: `2026-02-22_200456_S3`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_200456_S3/`):
- `S3_01_semgrep_protocol_boundary.txt` -> Pass (`0 findings`; semgrep output confirms no blocking hits)
- `S3_02_mypy_strict.txt` -> Pass
- `S3_03_lint_imports.txt` -> Pass
- `S3_04_window_frontend_reflection_scan.txt` -> Pass
- `S3_05_ui_space_reflection_scan.txt` -> Pass
- `S3_06_contract_surface_scan.txt` -> Pass (contract surfaces present in API modules)
- Resolution result:
- required-path reflection removed from `engine/runtime/window_frontend.py` and `engine/runtime/ui_space.py`.
- required capabilities promoted to explicit contracts in `engine/api/render.py`, `engine/api/window.py`, and `engine/api/debug.py`.
- runtime/frontend code now calls protocol-declared capabilities directly instead of reflected `getattr/hasattr` paths.

S3 closure verification (mandatory two-pass validation):
- Pass 1 run id: `2026-02-22_201300_S3_pass1`
- Artifacts:
- `S3P1_01_semgrep_protocol_boundary.txt`
- `S3P1_02_mypy_strict.txt`
- `S3P1_03_lint_imports.txt`
- `S3P1_04_reflection_scan_runtime_paths.txt`
- Result: all pass
- Pass 2 run id: `2026-02-22_201620_S3_pass2`
- Artifacts:
- `S3P2_01_semgrep_protocol_boundary.txt`
- `S3P2_02_mypy_strict.txt`
- `S3P2_03_lint_imports.txt`
- `S3P2_04_reflection_scan_runtime_paths.txt`
- `S3P2_05_contract_surface_scan.txt`
- Result: all pass
- Literal step closure note:
- optional app design-resolution capability is now handled via explicit optional protocol wrapper (`engine.api.app_port.UIDesignResolutionProvider`) in `engine/runtime/ui_space.py`, replacing ad-hoc reflection for this capability path.

S3 architecture correction addendum (runtime-checkable boundary policy + type-boundary correction):
- Concern addressed:
- removed object-widening workaround in `engine/runtime/ui_space.py`; no public S3 boundary function is typed as `object` for capability resolution.
- protocol-boundary solution now uses explicit optional protocol wrapper (`UIDesignResolutionProvider`) and typed provider flow.
- API contract strictness upgrade:
- `@runtime_checkable` is now restricted to runtime boundary protocols (service/subsystem interfaces, provider boundaries, adapter replacement points, plugin-style extension points).
- DTO/value/payload/data-shape protocols are explicitly not `@runtime_checkable`.
- Verification pass 1 run id: `2026-02-22_202030_S3_pass1b`
- Artifacts:
- `S3P1B_01_semgrep_protocol_boundary.txt`
- `S3P1B_02_mypy_strict.txt`
- `S3P1B_03_lint_imports.txt`
- `S3P1B_04_reflection_scan_runtime_paths.txt`
- `S3P1B_05_runtime_checkable_scan.txt`
- Result: all pass
- Verification pass 2 run id: `2026-02-22_202215_S3_pass2b`
- Artifacts:
- `S3P2B_01_semgrep_protocol_boundary.txt`
- `S3P2B_02_mypy_strict.txt`
- `S3P2B_03_lint_imports.txt`
- `S3P2B_04_reflection_scan_runtime_paths.txt`
- `S3P2B_05_runtime_checkable_scan.txt`
- Result: all pass

S6 closure execution addendum (run id: `2026-02-22_221900_S6_closure`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_221900_S6_closure/`):
- `S6C_01_state_mutation_ownership.txt` -> Pass
- `S6C_02_mypy_strict.txt` -> Pass
- `S6C_03_lint_imports.txt` -> Pass
- `S6C_04_removed_module_state_scan.txt` -> Pass
- `S6C_05_state_ownership_impl_scan.txt` -> Pass
- `S6C_06_state_mutation_ownership_second_pass.txt` -> Pass
- `S6C_07_lint_imports_second_pass.txt` -> Pass
- Resolution result:
- Renderer module-level mutable caches migrated to `WgpuRenderer` instance-owned state (`_command_color_cache`, `_command_linear_color_cache`, `_transform_values_cache`) and helper call graph updated to consume owned caches.
- UI-space mutable caches migrated from module globals into `_ScaleCacheState` owned by `_ScaledRenderAPI`; public stateless scaling path remains available without shared mutable globals.
- Runtime profile presets converted to immutable mapping (`MappingProxyType`) in `engine/runtime_profile.py`.
- Runtime profiling RSS provider globals replaced by `_ProcessRssProbe` service object with owned probe state (no `global` writes).
- Runtime logging singleton state remains object-owned via `_LoggingRuntimeState` (no `global` writes).
- Completion discipline note:
- S6 marked complete only after second-pass validation (`S6C_06`, `S6C_07`) and targeted symbol/global scans (`S6C_04`, `S6C_05`).

S6 strict re-evaluation addendum (run id: `2026-02-22_222600_S6_strict_reeval`, non-closure):
- Re-ran primary and closure sanity gates:
- `check_state_mutation_ownership`: pass
- `mypy --strict`: pass
- `lint-imports`: pass
- Carry-over finding:
- S6 objective requires removal of mutable module-level runtime state ownership, but mutable module-level singleton objects still exist in:
- `engine/runtime/logging.py` (`_LOGGING_RUNTIME`)
- `engine/runtime/profiling.py` (`_PROCESS_RSS_PROBE`)
- Decision:
- Open `S6.b` for strict state-ownership completion.
- Initial status at decision time: `S6.b` documented and pending execution (later executed; see S6.b closure addendum below).

S6.b closure execution addendum (run id: `2026-02-22_223500_S6b_closure`, raw root: `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_223500_S6b_closure/`):
- `S6b_01_state_mutation_ownership.txt` -> Pass
- `S6b_02_mypy_strict.txt` -> Pass
- `S6b_03_lint_imports.txt` -> Pass
- `S6b_04_singleton_scan.txt` -> Pass
- `S6b_05_state_mutation_ownership_second_pass.txt` -> Pass
- `S6b_06_lint_imports_second_pass.txt` -> Pass
- Resolution result:
- `engine/runtime/logging.py` no longer uses module-level mutable singleton state; runtime logging lifecycle is owned by `EngineLoggingRuntime` instances injected through composition path (`entrypoint -> bootstrap`).
- `engine/runtime/profiling.py` no longer uses module-level RSS probe singleton; `FrameProfiler` owns probe lifecycle via instance field (`_rss_probe`).
- `scripts/check_state_mutation_ownership.py` hardened to detect module-level singleton object constructor assignments and allowlisted immutable/safe constructor patterns (including `ContextVar`).
- Completion discipline:
- S6.b closure validated with second pass (`S6b_05`, `S6b_06`) before status update.

### Investigation
Investigation scope: code-verified investigation for every failing signal from run `2026-02-22_175415_static_eval`.

1. Import cycle strict fail (`03_import_cycles_strict.txt`) and budget regression (`04_import_cycles_budget.txt`)
- Confirmed root cause A: package-barrel coupling creates cross-package edges that collapse layering into a large SCC.
- Evidence: `engine/runtime/__init__.py:3-9` imports multiple `engine.api.*` symbols, while runtime modules also import each other and are imported via top-level barrels.
- Confirmed root cause B: runtime and diagnostics parallel implementations duplicate/re-export related capabilities across packages, adding graph edges.
- Evidence: `engine/runtime/observability.py:1+` and `engine/diagnostics/observability.py:1+` are near-identical modules with overlapping roles.
- Confirmed root cause C: gameplay references runtime implementation directly.
- Evidence: `engine/gameplay/update_loop.py:10` imports `engine.runtime.time.FixedStepAccumulator`, adding extra runtime<->gameplay edge.
- Investigation conclusion: cycles are structural (barrel + implementation intermixing), not isolated accidental imports.

2. Complexity fail (`07_xenon.txt`)
- Confirmed root cause A: operational boundary uncertainty drives reflection-heavy control flow.
- Evidence:
- `engine/runtime/window_frontend.py:47,73,76,118` uses `getattr`/`hasattr` in required runtime path.
- `engine/runtime/ui_space.py:89,109,196` does capability reflection and fallback logic.
- `engine/rendering/wgpu_renderer.py` contains extensive reflection/fallback probes across backend paths.
- Confirmed root cause B: high-responsibility concentration in single files.
- Evidence:
- `engine/rendering/wgpu_renderer.py` spans backend init, rendering, prewarm, font resolution, env parsing, telemetry.
- `engine/runtime/host.py` spans lifecycle, diagnostics, replay, profiling export, HTTP diagnostics, overlay composition.
- Investigation conclusion: complexity is driven by missing subsystem extraction boundaries and implicit capability contracts.

3. LOC fail (`08_file_limits.txt`)
- Confirmed root cause A: renderer god-module.
- Evidence: `engine/rendering/wgpu_renderer.py` is `5184 LOC` and contains multiple subsystems with separate change cadences.
- Confirmed root cause B: runtime host/profiling still aggregate unrelated responsibilities.
- Evidence:
- `engine/runtime/host.py` hard-limit breach (`901 LOC`) and includes host loop + diagnostics/export + runtime metadata logic.
- `engine/runtime/profiling.py` soft-limit breach (`646 LOC`) and mixes payload shaping, env parsing, RSS provider fallback, and state caching.
- Investigation conclusion: decomposition is mandatory before further policy recovery.

4. Barrel budget fail (`09_barrel_exports.txt`)
- Confirmed root cause A: API barrel is oversized and acts as convenience import hub rather than curated stable surface.
- Evidence: `engine/api/__init__.py` exports `129` symbols (`>120` budget) and includes broad symbol collection across domains.
- Confirmed root cause B: runtime barrel mixes API and runtime symbols.
- Evidence: `engine/runtime/__init__.py` imports `engine.api.*` and `engine.runtime.*` in one barrel.
- Investigation conclusion: barrel design currently reintroduces coupling pressure even when direct import rules pass.

5. Env placement fail (`10_env_read_placement.txt`)
- Confirmed root cause A: env/config parsing is still distributed into execution modules.
- Evidence:
- `engine/runtime/entrypoint.py:43` reads `WARSHIPS_DEBUG_UI`.
- `engine/runtime/host.py:49` and other lines read diagnostics/profile env flags.
- `engine/runtime/ui_space.py:128` reads `ENGINE_UI_RESOLUTION`.
- `engine/window/factory.py:43` reads `ENGINE_WINDOW_BACKEND`.
- `engine/rendering/wgpu_renderer.py:4237+`, `4827+`, `4863+` read rendering/font/prewarm env flags.
- Confirmed root cause B: module-local `_env_*` helpers exist in multiple runtime/rendering modules (`runtime/profiling.py`, `rendering/wgpu_renderer.py`, `window/rendercanvas_glfw.py`).
- Investigation conclusion: configuration ownership remains fragmented; bootstrap has not become the single source of resolved config.

6. Broad exception fails (`11_ruff_broad_exceptions.txt`, `12_semgrep_broad_exceptions.txt`)
- Confirmed root cause A: backend integration code uses broad `except Exception` as expected compatibility strategy.
- Evidence: `engine/window/rendercanvas_glfw.py` contains multiple `except Exception: pass` blocks in startup mode switching and GLFW guards (`24+`, `39+`, `43+`, `51+`, `57+`, `72+`, `79+`, `85+`, `88+`).
- Confirmed root cause B: renderer prewarm/fallback paths use broad catches to continue startup.
- Evidence: `engine/rendering/wgpu_renderer.py:4237+` and surrounding prewarm blocks catch broad exceptions and continue/return.
- Investigation conclusion: exception model is compatibility-first and permissive; policy requires typed handling or explicit observability.

7. Exception observability fail (`21_exception_observability.txt`)
- Confirmed root cause: many broad catches do not emit required observability signal.
- Evidence:
- `engine/runtime/profiling.py` broad catches in RSS/provider/env conversion paths.
- `engine/runtime/ui_space.py:94,113` broad catches in resolution providers without logging.
- `engine/window/rendercanvas_glfw.py` broad catches without `logger.exception`/`exc_info=True`.
- Investigation conclusion: broad catches and missing telemetry are coupled; fixing one without the other is insufficient.

8. Domain literal and semantic leakage fails (`13_semgrep_domain_leakage.txt`, `15_domain_semantic_hardening.txt`)
- Confirmed root cause A: renderer contains game-title literal in engine code.
- Evidence: `engine/rendering/wgpu_renderer.py:4402` includes `"WARSHIPS 2"`.
- Confirmed root cause B: engine API primitives embed domain-specific board assumptions.
- Evidence:
- `engine/api/ui_primitives.py:78-82` hardcoded dual-surface layout defaults.
- `engine/api/ui_primitives.py:87-89` special-case `"secondary"`/`"primary"`.
- Confirmed root cause C: these semantics are duplicated in runtime UI module.
- Evidence: `engine/ui_runtime/grid_layout.py:14-25` mirrors the same domain semantics.
- Investigation conclusion: domain-specific UI assumptions are currently in both API and runtime implementation layers.

9. Protocol boundary fail (`14_semgrep_protocol_boundary.txt`)
- Confirmed root cause: required capabilities are encoded as dynamic reflection instead of explicit boundary protocols.
- Evidence:
- `engine/runtime/window_frontend.py:47,73,76,118` uses reflection for required interactions (`canvas`, resize hook, diagnostics emits, telemetry consume).
- `engine/runtime/ui_space.py:89,109,196` uses reflected optional methods (`ui_design_resolution`, `design_space_size`, `add_style_rect`) in core UI transform/render path.
- Investigation conclusion: boundaries are behaviorally defined at runtime, not statically enforced by contract.

10. Duplication fails (`16_jscpd_threshold.txt`, `17_duplicate_cluster.txt`)
- Confirmed root cause A: direct duplicate implementation between API and runtime UI modules.
- Evidence:
- `engine/api/ui_primitives.GridLayout` mirrors `engine/ui_runtime/grid_layout.GridLayout`.
- `check_duplicate_cluster` output points repeated clones from `engine/api/ui_primitives.py` into `engine/ui_runtime/*`.
- Confirmed root cause B: duplicate diagnostics/session-analysis implementation.
- Evidence: `engine/runtime/observability.py` and `engine/diagnostics/observability.py` are effectively duplicated line-for-line in key functions (`_safe_json_line`, `_parse_iso_timestamp`, `_extract_stamp`, `discover_session_bundles`, `summarize_session`).
- Confirmed root cause C: API debug export/profiling serialization overlaps host implementation.
- Evidence: clone reported between `engine/api/debug.py` and `engine/runtime/host.py` payload serialization blocks.
- Investigation conclusion: duplication is architectural (split ownership) rather than incidental copy-paste in one file.

11. Feature flag registry fail (`19_feature_flag_registry.txt`)
- Confirmed root cause: engine runtime references game-specific flag not registered in engine flag registry.
- Evidence:
- Usage: `engine/runtime/entrypoint.py:43` reads `WARSHIPS_DEBUG_UI`.
- Registry: `tools/quality/budgets/feature_flags_registry.json` does not include `WARSHIPS_DEBUG_UI`.
- Investigation conclusion: runtime currently depends on game-named env contract, violating engine-level flag governance and domain-neutrality boundaries.

12. State mutation ownership fail (`20_state_mutation_ownership.txt`)
- Confirmed root cause A: mutable global caches retained in performance paths.
- Evidence:
- `engine/rendering/wgpu_renderer.py:41-45` mutable global caches.
- `engine/runtime/ui_space.py:18+` mutable scale caches.
- `engine/runtime_profile.py:34` mutable profile preset map.
- Confirmed root cause B: global singleton write pattern in runtime services.
- Evidence:
- `engine/runtime/logging.py:19` uses `global _QUEUE_LISTENER`.
- `engine/runtime/profiling.py:494` uses global `_RSS_PROVIDER`, `_RSS_PSUTIL_MOD`, `_RSS_RESOURCE_MOD`.
- Investigation conclusion: stateful module globals are used as runtime cache/singleton strategy and violate ownership policy.

13. Public API drift fail (`22_public_api_surface.txt`)
- Confirmed root cause: approved architecture migration changed API exports but baseline was not synchronized.
- Evidence:
- Added `EngineModule` in `engine/api/__init__.py`.
- Removed legacy factory/bootstrap exports listed in `22_public_api_surface.txt`.
- Baseline file `tools/quality/budgets/engine_api_surface_baseline.txt` still expects removed symbols (`configure_logging`, `run_hosted_runtime`, many `create_*`).
- Investigation conclusion: this failure is baseline-governance debt after intentional API evolution, not an accidental code regression.

14. Unified static runner fail (`23_policy_static_checks_full_run.txt`)
- Confirmed: unified runner failure is fully explained by the individual check failures above; no extra hidden gate failures were observed beyond per-tool outputs.
- Investigation conclusion: boundary hardening checks remain green, but recovery requires structural work in cycle breaking, decomposition, contract explicitness, config ownership centralization, duplication consolidation, and policy baseline alignment.

### Proposed fixes
1. Cycle and dependency graph hardening
- Remove mixed-layer barrel coupling from `engine/runtime/__init__.py` by keeping runtime-only exports.
- Reduce `engine/api/__init__.py` to a curated stable API surface and move secondary symbols to explicit submodules.
- Consolidate duplicated observability ownership by keeping a single canonical implementation and removing/delegating the duplicate runtime copy.

2. Runtime and renderer decomposition
- Split `engine/rendering/wgpu_renderer.py` into focused subsystems:
- backend/device/surface lifecycle
- packet translation and dispatch
- text/font subsystem
- prewarm/config hooks
- diagnostics integration adapters
- Split `engine/runtime/host.py` into:
- frame/lifecycle coordinator
- diagnostics/replay/profiling export service
- diagnostics HTTP wiring service
- Keep host as orchestrator, not implementation container.

3. Protocol boundary explicitness (remove required-path reflection)
- Define explicit capability protocols for required runtime interactions (window canvas/request_draw, resize hooks, telemetry emit contracts).
- Replace required-path `getattr`/`hasattr` in `engine/runtime/window_frontend.py` and `engine/runtime/ui_space.py` with typed capability contracts.
- Keep optional capabilities explicit and isolated behind optional protocol surfaces.

4. Config ownership centralization
- Resolve engine config/env exactly once in runtime startup/bootstrap.
- Inject typed config objects into renderer/host/window/profiling/ui-space services.
- Eliminate direct `os.getenv` access from execution/hot-path modules.
- Replace duplicated `_env_*` helpers with one shared config parser layer.

5. Exception and observability normalization
- Replace `except Exception: pass` patterns with typed handling or explicit observability.
- Introduce per-boundary exception rules:
- expected compatibility exceptions are typed and logged
- unexpected exceptions include `logger.exception(...)` or `exc_info=True` telemetry
- Apply first in `engine/window/rendercanvas_glfw.py`, `engine/runtime/ui_space.py`, `engine/runtime/profiling.py`, and renderer prewarm/fallback blocks.

6. Domain-neutral engine contracts
- Remove title literal leakage from renderer prewarm payloads.
- Refactor `engine/api/ui_primitives.py` to remove domain-specific grid semantics (`primary`/`secondary`, board-default constants) from engine API contracts.
- Keep game-specific layout semantics in game/app modules, not engine core contracts.

7. Duplication elimination
- Consolidate UI runtime logic ownership into one place (`engine/ui_runtime/*`) and minimize executable overlap in `engine/api/ui_primitives.py`.
- Remove duplicated observability/session-analysis code between `engine/runtime/observability.py` and `engine/diagnostics/observability.py`.
- Extract shared serialization/profiling payload helpers currently duplicated between API/debug and runtime host paths.

8. Mutable global/state ownership cleanup
- Move renderer and UI-space global caches to instance-scoped/cache-service state.
- Replace module-level global singleton writes in runtime logging/profiling with managed service objects owned by runtime composition.
- Convert runtime profile preset mapping to immutable read-only structure.

9. Feature flag governance alignment
- Remove game-specific flag usage from engine runtime (`WARSHIPS_DEBUG_UI` in `engine/runtime/entrypoint.py`) by passing debug controls via module/runtime config.
- Ensure every remaining engine-read flag has registry metadata and lifecycle ownership.

10. Public API baseline synchronization
- After confirming intended API surface from composition migration, update public API baseline to match approved contract.
- Document removed legacy factory/bootstrap exports and the replacement composition entrypoint in architecture/API notes.

### Refactoring Phase-Plan
Phase planning scope: static-check remediation only.  
Execution rule: each phase must serialize raw outputs under `docs/architecture/audits/static_checks/<date>/<run_id>/` and must not proceed until its completion gates are met or explicitly deferred with documented rationale.
Depth discipline: rewrite depth is not a reason to defer work. If a phase is too large, it must be split into explicit sub-phases and executed fully.

1. Phase S1: Governance and boundary quick alignment
- Objective:
- Fully resolve governance and boundary alignment failures, including deep rewrites if required.
- Targeted failing checks:
- `22_public_api_surface.txt`
- `19_feature_flag_registry.txt`
- `09_barrel_exports.txt` (runtime barrel mixed-layer issue first)
- Executable steps:
- Update `tools/quality/budgets/engine_api_surface_baseline.txt` to match approved post-migration API surface.
- Command: `uv run python scripts/check_public_api_surface.py --update-baseline`
- Re-run and serialize: `uv run python scripts/check_public_api_surface.py`
- Remove game-specific env dependency from engine runtime entrypoint.
- Replace `WARSHIPS_DEBUG_UI` read in `engine/runtime/entrypoint.py` with module-provided runtime config input.
- Add/adjust module contract field in `engine/api/composition.py` and game module implementation in `warships/game/app/engine_hosted_runtime.py`.
- Re-run and serialize:
- `uv run python scripts/check_feature_flag_registry.py`
- `uv run python scripts/check_env_read_placement.py`
- Fix mixed-layer runtime barrel:
- Edit `engine/runtime/__init__.py` to remove `engine.api.*` re-exports.
- Keep runtime-local exports only.
- Re-run and serialize:
- `uv run python scripts/check_barrel_exports.py`
- `uv run lint-imports`
- Completion gates:
- `check_public_api_surface`: pass
- `check_feature_flag_registry`: pass
- `check_barrel_exports`: no mixed-layer violation in `engine/runtime/__init__.py`
- `lint-imports`: still pass
- Artifacts:
- `S1_01_public_api_surface.txt`
- `S1_02_feature_flag_registry.txt`
- `S1_03_barrel_exports.txt`
- `S1_04_lint_imports.txt`

2. Phase S2: Config ownership centralization
- Objective:
- Eliminate distributed env reads from runtime/renderer/window execution paths by introducing centralized runtime config resolution.
- If cross-cutting rewiring is required, split into `S2.a`, `S2.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `10_env_read_placement.txt`
- Related: complexity and exception pressure reductions from removing scattered env fallback code.
- Executable steps:
- Create centralized config module:
- New module (example): `engine/runtime/config.py`
- Define immutable config dataclasses for:
- render loop and vsync
- UI resolution/design resolution
- diagnostics HTTP/profile flags
- window backend and startup mode
- renderer prewarm/font settings
- Resolve env once in startup path (`engine/runtime/entrypoint.py` and/or `engine/runtime/bootstrap.py`).
- Inject typed config into:
- `engine/runtime/host.py`
- `engine/runtime/profiling.py`
- `engine/runtime/ui_space.py`
- `engine/window/factory.py`
- `engine/window/rendercanvas_glfw.py`
- `engine/rendering/wgpu_renderer.py`
- Remove local `_env_*` helpers in these modules once config injection is complete.
- Re-run and serialize:
- `uv run python scripts/check_env_read_placement.py`
- `uv run mypy --strict`
- Completion gates:
- `check_env_read_placement`: pass or only explicitly approved bootstrap/config module findings remain.
- `mypy --strict`: pass.
- Artifacts:
- `S2_01_env_read_placement.txt`
- `S2_02_mypy_strict.txt`

- S2 follow-up sub-phase (`S2.b`): feature flag registry reconciliation after centralized config migration
- Objective:
- Fully align `tools/quality/budgets/feature_flags_registry.json` with all flags now surfaced by helper-aware registry scanning.
- Targeted failing checks:
- `S2_04_feature_flag_registry.txt`
- Executable steps:
- Parse current failing list from `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_194137_S2/S2_04_feature_flag_registry.txt`.
- For each missing flag, add metadata entry in `tools/quality/budgets/feature_flags_registry.json`:
- required fields: `owner`, `rationale`, `remove_by`, `status`.
- ensure `remove_by` uses `YYYY-MM-DD` and is not in the past.
- Keep names exactly as used in code (no alias entries).
- Re-run and serialize:
- `uv run python scripts/check_feature_flag_registry.py`
- `uv run python scripts/policy_static_checks.py` (optional in this sub-phase; mandatory before S8 closure)
- Completion gates:
- `check_feature_flag_registry`: pass.
- no newly introduced stale/unused entries in registry.
- Artifacts:
- `S2b_01_feature_flag_registry.txt`
- `S2b_02_policy_static_checks.txt`

3. Phase S3: Protocol boundary hardening and reflection removal
- Objective:
- Replace required-path reflection with explicit contracts to satisfy protocol boundary rules and reduce branching complexity.
- If contract migration spans many files, split into `S3.a`, `S3.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `14_semgrep_protocol_boundary.txt`
- Contributes to: `07_xenon.txt`, `11_ruff_broad_exceptions.txt`, `12_semgrep_broad_exceptions.txt`
- Executable steps:
- Introduce explicit capability protocols in API contracts (candidate locations):
- `engine/api/window.py`
- `engine/api/render.py`
- `engine/api/debug.py` (diagnostics emit contract)
- Replace required runtime-path reflection:
- `engine/runtime/window_frontend.py`
- remove required `getattr/hasattr` for `canvas`, `request_draw`, resize handling, diagnostics emit.
- use typed capability interfaces.
- `engine/runtime/ui_space.py`
- replace required reflection (`design_space_size`, `add_style_rect`) with typed adapters/protocols.
- Keep optional capabilities as explicit optional protocol wrappers, not ad-hoc reflection.
- Re-run and serialize:
- `uv run semgrep --error --config tools/quality/semgrep/protocol_boundary_rules.yml engine`
- `uv run mypy --strict`
- Completion gates:
- protocol boundary semgrep: pass
- `mypy --strict`: pass
- Artifacts:
- `S3_01_semgrep_protocol_boundary.txt`
- `S3_02_mypy_strict.txt`

3.a Phase S3.c: Subsystem-role contract model enforcement (ABC migration)
- Objective:
- Align `engine.api` subsystem-role contracts with `docs/architecture/engine_api_contract_model_policy.md` by migrating runtime-owned subsystem interfaces from `Protocol` to nominal `ABC` contracts.
- Targeted signals:
- Architectural mismatch discovered after policy upgrade: subsystem roles remained structural `Protocol` instead of nominal `ABC`.
- Executable steps:
- Reclassify subsystem roles and convert to `ABC`:
- `engine/api/render.py` (`RenderAPI`)
- `engine/api/window.py` (`WindowPort`)
- `engine/api/events.py` (`EventBus`)
- `engine/api/ui_framework.py` (`UIFramework`)
- `engine/api/gameplay.py` (`UpdateLoop`)
- `engine/api/context.py` (`RuntimeContext`)
- `engine/api/module_graph.py` (`ModuleGraph`)
- `engine/api/screens.py` (`ScreenStack`)
- `engine/api/action_dispatch.py` (`ActionDispatcher`)
- `engine/api/app_port.py` (`EngineAppPort`)
- Keep capability/data contracts structural per policy (`Protocol`, with `@runtime_checkable` only for capability boundaries).
- Update concrete implementations to nominally inherit migrated ABC contracts in runtime/sdk/game:
- `engine/runtime/framework_engine.py`
- `engine/runtime/module_graph.py`
- `engine/runtime/screen_stack.py`
- `engine/runtime/events.py`
- `engine/runtime/ui_space.py`
- `engine/runtime/host.py`
- `engine/gameplay/update_loop.py`
- `engine/rendering/wgpu_renderer.py`
- `warships/game/ui/game_view.py`
- Re-run and serialize:
- `uv run semgrep --error --config tools/quality/semgrep/protocol_boundary_rules.yml engine`
- `uv run mypy --strict engine/api engine/runtime engine/sdk engine/gameplay warships/game/app warships/game/ui`
- `uv run lint-imports`
- `rg -n "class\\s+\\w+\\((ABC|Protocol)\\)" engine/api`
- Completion gates:
- semgrep protocol-boundary rules: pass
- strict mypy: pass
- import-linter contracts: pass
- API contract model scan confirms subsystem roles migrated to `ABC` while data/capability slices remain structural by policy
- Artifacts:
- `S3c_01_semgrep_protocol_boundary.txt`
- `S3c_02_mypy_strict.txt`
- `S3c_03_lint_imports.txt`
- `S3c_04_api_contract_model_scan.txt`

3.b Phase S3.d: Final contract classification sweep
- Objective:
- Execute full `engine.api` contract classification against `docs/architecture/engine_api_contract_model_policy.md` and close remaining subsystem-role misclassifications.
- Targeted signals:
- residual subsystem-role protocols remained in AI/assets/commands/interaction/logging/composition boundary surfaces after S3.c.
- Executable steps:
- Convert remaining subsystem-role contracts to nominal `ABC`:
- `engine/api/ai.py` (`Blackboard`, `Agent`)
- `engine/api/assets.py` (`AssetRegistry`)
- `engine/api/commands.py` (`CommandMap`)
- `engine/api/interaction_modes.py` (`InteractionModeMachine`)
- `engine/api/logging.py` (`LoggerPort`)
- `engine/api/composition.py` (`ServiceResolver`, `ServiceBinder`)
- Remove unnecessary `@runtime_checkable` from non-capability opaque boundary placeholders (`ControllerPort`, `FrameworkPort`, `ViewPort`).
- Align concrete implementations to explicit ABC inheritance:
- `engine/ai/blackboard.py`
- `engine/ai/agent.py`
- `engine/assets/registry.py`
- `engine/runtime/commands.py`
- `engine/runtime/interaction_modes.py`
- `engine/runtime/__init__.py` (runtime command export alignment)
- Re-run and serialize:
- `uv run mypy --strict engine/api engine/runtime engine/sdk engine/gameplay engine/assets engine/ai warships/game`
- `uv run semgrep --error --config tools/quality/semgrep/protocol_boundary_rules.yml engine`
- `uv run lint-imports`
- `rg -n "class\\s+\\w+\\((ABC|Protocol)\\)" engine/api`
- `rg -n "@runtime_checkable" engine/api -A 1`
- Completion gates:
- strict mypy: pass
- protocol-boundary semgrep: pass
- import-linter contracts: pass
- contract map confirms subsystem roles are nominal (`ABC`) while plugin/capability/data contracts remain structural (`Protocol`) per policy
- Artifacts:
- `S3d_01_mypy_strict.txt`
- `S3d_02_semgrep_protocol_boundary.txt`
- `S3d_03_lint_imports.txt`
- `S3d_04_api_contract_kinds.txt`
- `S3d_05_runtime_checkable_map.txt`

4. Phase S4: Exception semantics and observability normalization
- Objective:
- Eliminate silent broad catches and enforce observability contracts for remaining broad handlers.
- If broad-catch cleanup is large, split into `S4.a`, `S4.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `11_ruff_broad_exceptions.txt`
- `12_semgrep_broad_exceptions.txt`
- `21_exception_observability.txt`
- Executable steps:
- Create exception handling policy helpers (example module):
- `engine/runtime/errors.py` with typed wrappers and logging helpers.
- First remediation focus:
- `engine/window/rendercanvas_glfw.py`
- remove `except Exception: pass`
- replace with typed fallback exceptions and explicit logging where fallback is retained.
- `engine/runtime/ui_space.py`
- add observability on failure paths or convert to typed errors.
- `engine/runtime/profiling.py`
- typed catches around provider selection and conversion paths; add telemetry logs.
- `engine/rendering/wgpu_renderer.py`
- prewarm/fallback blocks: convert silent catches to typed+observable handling.
- Re-run and serialize:
- `uv run ruff check engine --select E722,BLE001`
- `uv run semgrep --error --config tools/quality/semgrep/broad_exception_policy.yml engine`
- `uv run python scripts/check_exception_observability.py`
- Completion gates:
- ruff broad exception check: pass
- semgrep broad exception policy: pass
- exception observability checker: pass
- Artifacts:
- `S4_01_ruff_broad_exceptions.txt`
- `S4_02_semgrep_broad_exceptions.txt`
- `S4_03_exception_observability.txt`

5. Phase S5: Domain-neutralization and API/runtime duplication cleanup
- Objective:
- Remove game-domain leakage and collapse duplicated UI/observability logic ownership.
- If domain cleanup and deduplication are too broad for one slice, split into `S5.a`, `S5.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `13_semgrep_domain_leakage.txt`
- `15_domain_semantic_hardening.txt`
- `16_jscpd_threshold.txt`
- `17_duplicate_cluster.txt`
- Executable steps:
- Remove title literal from renderer prewarm payload:
- update `engine/rendering/wgpu_renderer.py` startup text seed to neutral value or runtime-provided label.
- De-domainize UI primitives contract surface:
- move board-specific `GridLayout` defaults/target semantics out of `engine/api/ui_primitives.py`.
- keep generic geometry contracts in API.
- relocate concrete board/grid implementation to game or runtime-specific module.
- Consolidate duplicate UI runtime logic:
- keep one executable implementation in `engine/ui_runtime/*`.
- turn `engine/api/ui_primitives.py` into contracts/minimal generic helpers only.
- Consolidate duplicated observability code:
- keep canonical implementation in one package (`engine/diagnostics/observability.py`).
- make `engine/runtime/observability.py` delegate or remove.
- Re-run and serialize:
- `uv run semgrep --error --config tools/quality/semgrep/domain_literal_leakage.yml engine`
- `uv run python scripts/check_domain_semantic_leakage.py`
- `npx --yes jscpd --threshold 5 engine`
- `uv run python scripts/check_duplicate_cluster.py`
- Completion gates:
- domain literal semgrep: pass
- domain semantic hardening: pass
- global jscpd threshold: <= 5%
- duplicate cluster gate: pass
- Artifacts:
- `S5_01_semgrep_domain_leakage.txt`
- `S5_02_domain_semantic_hardening.txt`
- `S5_03_jscpd_threshold.txt`
- `S5_04_duplicate_cluster.txt`

6. Phase S6: Mutable state ownership remediation
- Objective:
- Remove mutable module-level state and global writes from engine runtime paths.
- If cache/singleton replacement requires service extraction, split into `S6.a`, `S6.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `20_state_mutation_ownership.txt`
- Executable steps:
- Renderer cache migration:
- move `_COMMAND_COLOR_CACHE`, `_COMMAND_LINEAR_COLOR_CACHE`, `_TRANSFORM_VALUES_CACHE` into renderer instance state.
- UI space cache migration:
- replace module-level `_SCALED_*_CACHE` with instance/cache-object scoped storage.
- Runtime profile immutability:
- convert `_PROFILE_PRESETS` to immutable mapping (e.g., `MappingProxyType`) or accessor-managed immutable table.
- Runtime logging/profiling singleton cleanup:
- replace `global _QUEUE_LISTENER` and RSS provider globals with composition-owned service objects.
- Re-run and serialize:
- `uv run python scripts/check_state_mutation_ownership.py`
- `uv run mypy --strict`
- Completion gates:
- state mutation ownership check: pass
- `mypy --strict`: pass
- Artifacts:
- `S6_01_state_mutation_ownership.txt`
- `S6_02_mypy_strict.txt`

6.b Phase S6.b: Strict composition-owned runtime state finalization
- Objective:
- Eliminate remaining mutable module-level singleton ownership in runtime paths by moving state to composition-owned service instances.
- This sub-phase was opened from S6 strict re-evaluation carry-over and is now completed (see S6.b closure addendum).
- Targeted signals:
- S6 strict re-evaluation carry-over in:
- `engine/runtime/logging.py`
- `engine/runtime/profiling.py`
- Executable steps:
- Logging state ownership migration:
- remove module-level `_LOGGING_RUNTIME` singleton.
- introduce a composition-owned logging runtime service (listener lifecycle owner) created/wired from runtime composition.
- route `configure_engine_logging` through injected/owned runtime state object instead of module singleton.
- Profiling RSS probe ownership migration:
- remove module-level `_PROCESS_RSS_PROBE` singleton.
- move RSS provider/probe state behind composition-owned profiling service object or explicit runtime-owned probe instance lifecycle.
- Checker hardening:
- extend `scripts/check_state_mutation_ownership.py` to detect mutable module-level object singleton initialization patterns (not only list/dict/set/global statements).
- add explicit allowlist-only exceptions if absolutely required and documented.
- Re-run and serialize:
- `uv run python scripts/check_state_mutation_ownership.py`
- `uv run mypy --strict`
- `uv run lint-imports`
- Completion gates:
- state mutation ownership check: pass with hardened singleton detection enabled.
- `mypy --strict`: pass.
- `lint-imports`: pass.
- Artifacts:
- `S6b_01_state_mutation_ownership.txt`
- `S6b_02_mypy_strict.txt`
- `S6b_03_lint_imports.txt`
- `S6b_04_singleton_scan.txt`

7. Phase S7: Cycle graph reduction and decomposition completion
- Objective:
- Reduce SCC size and remove cycle budget regressions through concrete module separation.
- If decomposition is large, split into `S7.a`, `S7.b`, ... and execute all sub-phases.
- Targeted failing checks:
- `03_import_cycles_strict.txt`
- `04_import_cycles_budget.txt`
- `07_xenon.txt`
- `08_file_limits.txt`
- Executable steps:
- Break known cycle edges:
- decouple `engine/gameplay/update_loop.py` from `engine.runtime.time` by moving `FixedStepAccumulator` to neutral location (`engine/gameplay/time.py` or `engine/domain/time.py`).
- eliminate runtime barrel API imports from `engine/runtime/__init__.py`.
- unify observability module ownership to avoid duplicated package edges.
- Complete host decomposition:
- split `engine/runtime/host.py` into lifecycle, diagnostics/export, overlay/render-snapshot services.
- Complete renderer decomposition:
- split `engine/rendering/wgpu_renderer.py` into at least four modules (backend init, packet dispatch, text subsystem, config/prewarm).
- Keep public facade thin and orchestration-only.
- Re-run and serialize:
- `uv run python scripts/check_import_cycles.py`
- `uv run python scripts/check_import_cycles.py --allow-cycles --baseline tools/quality/budgets/import_cycles_baseline.json --json-output docs/architecture/audits/static_checks/latest/import_cycles_metrics.json`
- `uv run xenon --max-absolute B --max-modules A --max-average A engine`
- `uv run python scripts/check_engine_file_limits.py --soft 600 --hard 900`
- Completion gates:
- strict import cycles: pass.
- budget regression: no regression; target lower than baseline.
- xenon budgets: pass.
- LOC limits: pass.
- Artifacts:
- `S7_01_import_cycles_strict.txt`
- `S7_02_import_cycles_budget.txt`
- `S7_03_xenon.txt`
- `S7_04_file_limits.txt`

8. Phase S8: Final static gate convergence and lock-in
- Objective:
- Validate whole static policy set after all remediation phases and lock-in passing state.
- No residual policy failures allowed at phase completion.
- Executable steps:
- Run unified gate:
- `uv run python scripts/policy_static_checks.py`
- Run full per-tool suite in same run id and store outputs for traceability.
- Update documentation snapshots:
- append static findings summary with pass/fail table and delta from previous run.
- if API surface intentionally changed again, sync baseline in same phase.
- Completion gates:
- unified static runner passes fully.
- per-tool outputs match unified runner status.
- raw output archive exists for reproducibility.
- Artifacts:
- `S8_01_policy_static_checks_full_run.txt`
- `S8_02_static_suite_outputs_index.txt`

9. Phase execution protocol (applies to all phases)
- Before each phase:
- create run directory `docs/architecture/audits/static_checks/<date>/<phase_run_id>/`.
- After each phase:
- append concise delta summary in this document under static findings.
- capture unresolved failures explicitly as carry-over with direct file references.
- Do not bypass checks by baseline edits unless change is intentional and approved by policy intent.
- If a phase expands beyond practical single-slice size, create numbered sub-phases inside the same phase (`Sx.a`, `Sx.b`, ...) and keep executing until all phase gates pass.

10. Phase closure checklist (mandatory before marking any phase `completed`)
- Completion status discipline:
- A phase must remain `in_progress` until every checklist item below is satisfied and documented.
- Checklist A: required gates
- Re-run every gate listed under that phase's "Completion gates".
- Serialize raw outputs under the phase run directory.
- Record pass/fail per gate in this document.
- Checklist B: literal executable-step completion
- Verify each bullet under that phase's "Executable steps" was implemented (not inferred from gate pass).
- For code migration/refactor steps, run targeted code scans (for example symbol/callsite scans) and save outputs.
- Record explicit "implemented/not implemented" status for each executable step in this document.
- Checklist C: architecture/boundary sanity
- Re-run `lint-imports` and `mypy --strict` for every phase closure (even when not listed as primary gate) unless explicitly waived.
- If waived, document rationale and owner approval inline.
- Checklist D: closure artifacts
- Produce a dedicated closure artifact bundle (for example `Sx_closure_*` or `Sx.c_*`) containing:
- gate outputs,
- targeted verification scans,
- final phase summary.
- Reference the closure artifact paths in `## Global Refactor status` -> `Last completed step`.
- Checklist E: carry-over discipline
- Any unresolved signal automatically creates/updates a follow-up sub-phase (`Sx.b`, `Sx.c`, ...).
- Parent phase cannot be marked `completed` until follow-up sub-phases are completed or explicitly re-scoped with documented approval.


## LLM Check Findings

### Evaluations

### Investigation

### Proposed fixes

### Refactoring Phase-Plan


## Global Refactor status
Execution status legend: `not_started`, `in_progress`, `blocked`, `completed`.

1. Static track
- `S1`: `completed`
- `S2`: `completed`
- `S3`: `completed`
- `S4`: `completed`
- `S5`: `completed`
- `S6`: `completed`
- `S7`: `not_started`
- `S8`: `not_started`

2. Active sub-phases
- None

3. Current focus
- Execute `S7` cycle graph reduction and decomposition completion.

4. Last completed step
- `S6.b` completed (strict composition-owned runtime state finalization) with closure artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_223500_S6b_closure/`
- Gate outcomes:
- `S6b_01_state_mutation_ownership.txt`: pass
- `S6b_02_mypy_strict.txt`: pass
- `S6b_03_lint_imports.txt`: pass
- Second-pass outcomes:
- `S6b_05_state_mutation_ownership_second_pass.txt`: pass
- `S6b_06_lint_imports_second_pass.txt`: pass
- Executable-step verification:
- singleton/state scan confirms S6.b targets (`S6b_04_singleton_scan.txt`).
- S6 parent phase closure:
- `S6` is now complete (S6 + S6.b satisfied).

- `S5` completed (domain-neutralization and API/runtime duplication cleanup) with closure artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_210549_S5_closure/`
- Gate outcomes:
- `S5C_01_semgrep_domain_leakage.txt`: pass
- `S5C_02_domain_semantic_hardening.txt`: pass
- `S5C_03_jscpd_threshold.txt`: pass (`3.64%`, below `5%`)
- `S5C_04_duplicate_cluster.txt`: pass (0 cluster duplicates)
- Closure checklist C outcomes:
- `S5C_05_mypy_strict.txt`: pass
- `S5C_06_lint_imports.txt`: pass
- Executable-step verification:
- renderer title literal neutralized in prewarm payload (`engine/rendering/wgpu_renderer.py`) and verified by scan (`S5C_07_renderer_domain_literal_scan.txt`).
- `engine/api/ui_primitives.py` de-domainized and converted into a thin API facade over `engine/ui_runtime/*`; domain-semantic pattern scan is clean (`S5C_08_api_ui_primitives_domain_scan.txt`).
- duplicate UI runtime logic ownership consolidated to `engine/ui_runtime/*`; API layer retains contracts/minimal helpers only.
- duplicated observability ownership collapsed by delegating `engine/runtime/observability.py` to canonical diagnostics implementation.

- `S4` strict re-evaluation corrective pass completed with artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_205846_S4_reeval_fix/`
- Corrective outcomes:
- removed remaining silent typed-fallback handlers from targeted runtime/window paths (`rendercanvas_glfw.py`, `wgpu_renderer.py`) and replaced with explicit recoverable logging.
- integrated shared exception helper usage (`RECOVERABLE_RUNTIME_ERRORS`, `log_recoverable`) in targeted runtime/window paths.
- strict gates: pass (`S4RF_01`, `S4RF_02`, `S4RF_03`).
- closure checklist C sanity gates: pass (`S4RF_04`, `S4RF_05`).
- targeted scans:
- no silent typed fallback handlers remain in flagged files (`S4RF_06`).
- helper usage is present in runtime paths (`S4RF_07`).

- `S4` completed (exception semantics and observability normalization) with closure artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_205424_S4_closure/`
- Gate outcomes:
- `S4C_01_ruff_broad_exceptions.txt`: pass
- `S4C_02_semgrep_broad_exceptions.txt`: pass
- `S4C_03_exception_observability.txt`: pass
- Closure checklist C outcomes:
- `S4C_04_mypy_strict.txt`: pass
- `S4C_05_lint_imports.txt`: pass
- Executable-step verification (checklist B):
- exception helper module created: `engine/runtime/errors.py` (`S4C_08_runtime_errors_module_present.txt`)
- silent broad exception patterns removed from focused runtime/window/rendering paths and replaced with typed fallback handling (`S4C_06_no_broad_exception_scan.txt`, `S4C_07_typed_fallback_scan.txt`)
- `engine/runtime/profiling.py` provider/conversion fallback paths now use typed catches and explicit telemetry logging (`profiling_*` debug/warning logs)
- `engine/rendering/wgpu_renderer.py` prewarm/fallback paths now use typed catches with explicit debug observability (`text_prewarm_*`, `startup_render_prewarm_failed`)

- `S3.d` completed (final contract classification sweep) with artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_204659_S3d/`
- Key outcomes:
- remaining subsystem-role contracts were migrated to `ABC` in `engine/api` (`Blackboard`, `Agent`, `AssetRegistry`, `CommandMap`, `InteractionModeMachine`, `LoggerPort`, `ServiceResolver`, `ServiceBinder`).
- plugin/capability/data-shape contracts remain structural `Protocol`.
- unnecessary `@runtime_checkable` was removed from opaque non-capability placeholders (`ControllerPort`, `FrameworkPort`, `ViewPort`).
- strict mypy: pass (`S3d_01`).
- protocol-boundary semgrep: pass (`S3d_02`).
- import-linter contracts: pass (`S3d_03`).

- `S3.c` completed (subsystem-role contract model enforcement) with artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_204126_S3c/`
- Key outcomes:
- subsystem roles in `engine.api` migrated from structural `Protocol` to nominal `ABC` for runtime-owned services (render/window/events/ui/update/context/module-graph/screen-stack/action-dispatch/app-port).
- concrete runtime/sdk/game implementations were aligned to explicit inheritance of migrated ABC contracts.
- semgrep protocol-boundary rules: pass (`S3c_01`).
- strict mypy over migrated scope: pass (`S3c_02`).
- import-linter contracts: pass (`S3c_03`).

- `S3` completed after two-pass closure verification with artifacts under:
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_200456_S3/`
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_201300_S3_pass1/`
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_201620_S3_pass2/`
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_202030_S3_pass1b/`
- `docs/architecture/audits/static_checks/2026-02-22/2026-02-22_202215_S3_pass2b/`
- Key outcomes:
- protocol-boundary semgrep: pass in both verification passes (`S3P1_01`, `S3P2_01`).
- `mypy --strict`: pass in both verification passes (`S3P1_02`, `S3P2_02`).
- `lint-imports`: pass in both verification passes (`S3P1_03`, `S3P2_03`).
- reflection-removal scans and contract-surface scans: pass (`S3P1_04`, `S3P2_04`, `S3P2_05`).
- runtime-checkable policy is enforced at boundary level (not all protocols): boundary protocols remain `@runtime_checkable`, DTO/value/payload/data-shape protocols are excluded.
