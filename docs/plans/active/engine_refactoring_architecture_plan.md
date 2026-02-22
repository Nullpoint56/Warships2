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


## LLM Check Findings

### Evaluations

### Investigation

### Proposed fixes

### Refactoring Phase-Plan


## Global Refactor status
Execution status legend: `not_started`, `in_progress`, `blocked`, `completed`.

1. Static track
- `S1`: `not_started`
- `S2`: `not_started`
- `S3`: `not_started`
- `S4`: `not_started`
- `S5`: `not_started`
- `S6`: `not_started`
- `S7`: `not_started`
- `S8`: `not_started`

2. Active sub-phases
- None

3. Current focus
- None

4. Last completed step
- None
