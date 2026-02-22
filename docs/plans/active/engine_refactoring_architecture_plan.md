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

1. Phase 1 (API contract hardening):
   - remove API wiring imports (`engine/api/hosted_runtime.py` bootstrap dependency).
   - resolve import-linter broken contracts for API->runtime and layer shortcuts.
2. Phase 2 (UI runtime consolidation):
   - eliminate `engine/api/ui_primitives.py` runtime implementation duplication.
3. Phase 3 (EngineHost decomposition):
   - split `engine/runtime/host.py` (LOC/complexity violations).
4. Phase 4 (Renderer decomposition):
   - split `engine/rendering/wgpu_renderer.py` (hard LOC + complexity + broad exception concentration + domain literal leakage).
5. Phase 5 (sustainability hygiene):
   - reduce SCC count aggressively.
   - remove silent/broad exception fallbacks where policy disallows them.
   - reduce duplication below `5%`.

### Expanded Static Pass (v2, Full Gate Set)

Date: 2026-02-22

#### Scope

Executed full policy gate set, including newly introduced static checks:

1. `uv run python scripts/policy_static_checks.py`
2. `uv run lint-imports`
3. `uv run python scripts/check_bootstrap_wiring_ownership.py`
4. `uv run python scripts/check_api_runtime_factories.py`
5. `uv run python scripts/check_boundary_dto_purity.py`
6. `uv run python scripts/check_public_api_surface.py`
7. `uv run python scripts/check_import_cycles.py`
8. `uv run python scripts/check_import_cycles.py --allow-cycles --baseline tools/quality/budgets/import_cycles_baseline.json --json-output docs/architecture/audits/static_checks/latest/import_cycles_metrics.json`
9. `uv run mypy --strict`
10. `uv run xenon --max-absolute B --max-modules A --max-average A engine`
11. `uv run python scripts/check_engine_file_limits.py --soft 600 --hard 900`
12. `uv run python scripts/check_barrel_exports.py`
13. `uv run python scripts/check_env_read_placement.py`
14. `uv run python scripts/check_feature_flag_registry.py`
15. `uv run python scripts/check_state_mutation_ownership.py`
16. `uv run ruff check engine --select E722,BLE001`
17. `uv run semgrep --error --config tools/quality/semgrep/broad_exception_policy.yml engine`
18. `uv run python scripts/check_exception_observability.py`
19. `uv run semgrep --error --config tools/quality/semgrep/domain_literal_leakage.yml engine`
20. `uv run semgrep --error --config tools/quality/semgrep/protocol_boundary_rules.yml engine`
21. `uv run python scripts/check_domain_semantic_leakage.py`
22. `npx --yes jscpd --threshold 5 engine`
23. `uv run python scripts/check_duplicate_cluster.py`

#### Raw Outputs

All raw outputs were serialized under:

`docs/architecture/audits/static_checks/2026-02-22/`

1. `00_policy_static_checks_full_run_v2.txt`
2. `01_lint-imports_v2.txt`
3. `02_bootstrap_wiring_ownership_v2.txt`
4. `03_api_runtime_factories_v2.txt`
5. `04_boundary_dto_purity_v2.txt`
6. `05_public_api_surface_v2.txt`
7. `06_import_cycles_strict_v2.txt`
8. `07_import_cycles_budget_v2.txt`
9. `08_mypy_strict_v2.txt`
10. `09_xenon_v2.txt`
11. `10_file_limits_v2.txt`
12. `11_barrel_exports_v2.txt`
13. `12_env_read_placement_v2.txt`
14. `13_feature_flag_registry_v2.txt`
15. `14_state_mutation_ownership_v2.txt`
16. `15_ruff_broad_exceptions_v2.txt`
17. `16_semgrep_broad_exceptions_v2.txt`
18. `17_exception_observability_v2.txt`
19. `18_semgrep_domain_leakage_v2.txt`
20. `19_semgrep_protocol_boundary_v2.txt`
21. `20_domain_semantic_hardening_v2.txt`
22. `21_jscpd_threshold_v2.txt`
23. `22_duplicate_cluster_v2.txt`

#### Evaluations

1. Consolidated run (`00_policy_static_checks_full_run_v2.txt`)
   - Passes: public API surface drift gate, import cycle budget gate, `mypy --strict`, feature/env flag registry gate.
   - Fails: import-linter, bootstrap ownership, API runtime factory gate, boundary DTO purity, strict import cycles, xenon, LOC limits, barrel budget, env read placement, state ownership, ruff broad exceptions, semgrep broad exceptions, exception observability, domain literal leakage, protocol boundary rules, domain semantic hardening, jscpd global threshold, duplicate cluster gate.
2. API runtime factory gate (`03_api_runtime_factories_v2.txt`)
   - 13 violations where `create_*` / `run_*` in `engine.api` import `engine.runtime.*`.
   - Core offenders: `engine/api/hosted_runtime.py`, `engine/api/ui_framework.py`, `engine/api/flow.py`.
3. Boundary DTO purity gate (`04_boundary_dto_purity_v2.txt`)
   - Fails on public API contracts still typed as `object`/`Any`.
   - Highest concentration: `engine/api/debug.py` and `engine/api/logging.py`.
4. Public API surface drift (`05_public_api_surface_v2.txt`)
   - Pass (no drift from `tools/quality/budgets/engine_api_surface_baseline.txt`).
5. Import cycle budget gate (`07_import_cycles_budget_v2.txt`)
   - Pass (no regression versus baseline), while large SCCs still exist (`63`, `9`).
6. Barrel export budget (`11_barrel_exports_v2.txt`)
   - `engine/api/__init__.py` exports `144` > budget `120`.
   - `engine/runtime/__init__.py` exports `31` > budget `30`.
   - Mixed-layer imports present in `engine/runtime/__init__.py` (`engine.api.*` + `engine.runtime.*`).
7. Env read placement (`12_env_read_placement_v2.txt`)
   - Widespread env access outside approved config/bootstrap modules.
   - Largest concentration remains in `engine/rendering/wgpu_renderer.py` and `engine/runtime/host.py`.
8. Feature/env flag registry (`13_feature_flag_registry_v2.txt`)
   - Pass (all discovered env/feature keys mapped in `tools/quality/budgets/feature_flags_registry.json` with required metadata).
9. State mutation ownership (`14_state_mutation_ownership_v2.txt`)
   - 11 violations after noise filtering (`__all__` ignored).
   - Concrete mutable-global/global-write hotspots:
     - cache globals in `engine/rendering/wgpu_renderer.py`
     - `global` writes in `engine/runtime/logging.py` and `engine/runtime/profiling.py`
     - cache globals in `engine/runtime/ui_space.py`
     - preset global in `engine/runtime_profile.py`
10. Exception observability semantics (`17_exception_observability_v2.txt`)
   - Broad exception handlers without required observability across diagnostics/gameplay/runtime/window.
   - Dominant concentration in `engine/rendering/wgpu_renderer.py`.
11. Protocol boundary semgrep (`19_semgrep_protocol_boundary_v2.txt`)
   - 11 blocking findings.
   - Opaque provider typing still present (`engine/api/window.py: provider: object | None`).
   - Reflection-based required capability checks persist in `engine/runtime/ui_space.py` and `engine/runtime/window_frontend.py`.
12. Domain semantic hardening (`20_domain_semantic_hardening_v2.txt`)
   - 3 explicit semantic leaks in `engine/api/ui_primitives.py`:
     - `primary`/`secondary` branch literals
     - `grid_size: int = 10`
13. jscpd global threshold (`21_jscpd_threshold_v2.txt`)
   - Fails at `5.01%` duplicated lines (`526`) vs threshold `5%`, with `29` clone groups.
14. jscpd duplicate cluster (`22_duplicate_cluster_v2.txt`)
   - Fails at `28.07%` duplication in targeted cluster (`engine/api/ui_primitives.py` vs `engine/ui_runtime/**`).

#### Phase-Plan Extensions from v2

1. Phase 1 (API boundary hardening)
   - eliminate API runtime factory imports (`03_api_runtime_factories_v2.txt`).
   - replace `object`/`Any` public boundary typing with explicit protocols/DTO types (`04_boundary_dto_purity_v2.txt`).
   - retain API surface baseline process for intentional contract changes (`05_public_api_surface_v2.txt`).
2. Phase 2 (Configuration ownership)
   - migrate env reads from runtime/rendering/window modules into approved config/bootstrap pathways (`12_env_read_placement_v2.txt`).
   - keep feature flag registry metadata authoritative and current as flags evolve (`13_feature_flag_registry_v2.txt`).
3. Phase 3 (State/exception semantics)
   - replace mutable module caches/global writes with owned services or scoped caches (`14_state_mutation_ownership_v2.txt`).
   - enforce logged/structured broad-exception handling where broad catches remain unavoidable (`17_exception_observability_v2.txt`).
4. Phase 4 (Boundary protocol correctness)
   - remove opaque provider handles and reflection-based required capability dispatch in runtime frontends (`19_semgrep_protocol_boundary_v2.txt`).
5. Phase 5 (Domain neutrality and duplication burn-down)
   - remove domain semantic defaults from engine APIs (`20_domain_semantic_hardening_v2.txt`).
   - reduce duplication under global threshold and collapse `ui_primitives`/`ui_runtime` clone cluster (`21_jscpd_threshold_v2.txt`, `22_duplicate_cluster_v2.txt`).

### Phase 1 Execution Model (Architecture-Correct, No Check Bypass)

Phase 1 objective remains API boundary hardening. Execution is split into explicit slices to avoid checker-gaming:

1. Slice 1A (Rollback anti-patterns)
   - remove adapter indirection used only to bypass API->runtime checks.
   - remove local type-silencing added only to suppress diagnostics.
   - keep unresolved architectural violations visible until genuinely refactored.
2. Slice 1B (Hosted/UI composition migration)
   - make `engine.api.hosted_runtime` contract-only (config DTO only).
   - make `engine.api.ui_framework` contract-only (`UIFramework` protocol only).
   - move hosted runtime launch and UI framework default composition usage to runtime/composition layer call sites.
   - update Warships hosted startup path to call runtime composition APIs directly.
3. Slice 1C (Core factory migration)
   - migrate API `create_*` helpers in action/commands/context/events/flow/module_graph/screen/gameplay modules to composition/runtime layer usage by callers.
   - remove API-layer concrete constructor helpers after call-site migration.
4. Slice 1D (Boundary typing hardening)
   - replace remaining public `object`/`Any` signatures in `engine.api.*` with explicit Protocol/DTO contracts.
   - do not use `type: ignore` for boundary contract gaps.
5. Slice 1E (Phase 1 gate verification)
   - required checks: `check_api_runtime_factories`, `check_bootstrap_wiring_ownership`, `check_boundary_dto_purity`, `lint-imports`, `mypy --strict`.
   - document residual import-linter failures not in Phase 1 scope as carry-over to later phases.

### Phase 1 Progress Log

1. Slice 1A: Completed
   - adapter bypass module removed (`engine/bootstrap/api_runtime_adapters.py` deleted).
   - type-silencing bypasses removed; unresolved issues remain visible in static checks.
2. Slice 1B: Completed
   - `engine.api.hosted_runtime` changed to contract-only.
   - `engine.api.ui_framework` changed to contract-only.
   - Warships hosted startup migrated to runtime composition entrypoints (`engine.runtime.bootstrap`, `engine.runtime.framework_engine`, `engine.runtime.ui_space`).
3. Slice 1C: Completed
   - API runtime factory helpers removed from contract modules:
     - `engine/api/action_dispatch.py`
     - `engine/api/commands.py`
     - `engine/api/context.py`
     - `engine/api/events.py`
     - `engine/api/flow.py`
     - `engine/api/interaction_modes.py`
     - `engine/api/module_graph.py`
     - `engine/api/screens.py`
   - corresponding call sites migrated to runtime implementations:
     - `engine/runtime/framework_engine.py` (`RuntimeCommandMap`)
     - `warships/game/app/engine_game_module.py` (`RuntimeContextImpl`, `RuntimeEventBus`, `RuntimeModuleGraph`)
     - `warships/game/app/controller.py` (`RuntimeInteractionModeMachine`)
     - `warships/game/app/controller_state.py` (`RuntimeScreenStack`)
     - `warships/game/app/services/session_flow.py` (`RuntimeFlowProgram`)
     - `warships/game/app/ports/runtime_services.py` (local factory wrapping `RuntimeActionDispatcher`)
   - API barrel updated to remove deleted factory re-exports (`engine/api/__init__.py`).
   - gate results:
     - `check_api_runtime_factories`: pass (`0` violations)
     - `check_bootstrap_wiring_ownership`: pass
     - `check_boundary_dto_purity`: pass
     - `mypy --strict`: pass
     - `lint-imports`: still failing, but API->runtime direct import pressure reduced to residual paths (`engine.api.debug`, `engine.api.logging`, and transitive path through `engine.api.gameplay`).
4. Slice 1D: Completed (for API->runtime boundary target)
   - `engine.api.logging` reduced to contracts/formatter only (runtime wiring removed).
   - `engine.api.gameplay` reduced to contracts only (runtime state/update constructors removed).
   - `engine.api.debug` session discovery/load switched from runtime observability module import to diagnostics observability module import.
   - boundary typing hardening pass (no `type: ignore`):
     - `engine/api/context.py`: replaced opaque `object` fields with explicit boundary protocols (`LayoutPort`, `InputControllerPort`, `FrameClockPort`, `SchedulerPort`, `ServiceLike`) and typed service registry.
     - `engine/runtime/context.py`: aligned implementation with the new context boundary protocols.
     - `engine/api/flow.py`: introduced `FlowPayload` protocol and replaced `payload: object | None` at API boundary.
     - `engine/runtime/flow.py`: aligned runtime flow machine/program signatures to `FlowPayload`.
     - `engine/api/screens.py`: introduced `ScreenData` protocol and replaced `data: object | None` at API boundary.
     - `engine/runtime/screen_stack.py`: aligned screen stack signatures to `ScreenData`.
     - `engine/api/window.py`: replaced `SurfaceHandle.provider: object | None` with explicit `SurfaceProvider | None`.
     - `engine/api/render_snapshot.py`: replaced `RenderCommand.data` opaque value type with explicit recursive `RenderDataValue`.
     - `engine/runtime/ui_space.py` and `engine/runtime/host.py`: aligned scaling/snapshot sanitization paths to `RenderDataValue`.
     - `engine/api/assets.py` and `engine/assets/registry.py`: replaced raw asset `object` boundaries with `AssetValue` protocol.
   - supporting migrations:
     - `warships/main.py` logger acquisition switched to `engine.runtime.logging.get_engine_logger`.
     - `warships/game/infra/logging.py` wiring switched to `engine.runtime.logging.configure_engine_logging`.
     - gameplay/runtime tests and Warships module wiring switched to runtime constructors (`RuntimeUpdateLoop`, `RuntimeStateStore`, etc.).
   - gate results after Slice 1D:
     - `mypy --strict`: pass
     - `check_api_runtime_factories`: pass
     - `check_bootstrap_wiring_ownership`: pass
     - `check_boundary_dto_purity`: pass
     - `lint-imports`: `engine.api cannot import engine.runtime or engine.platform` now **KEPT**
   - remaining import-linter failure is now isolated to `no cross-layer shortcut imports` on runtime->api coupling, which is outside Phase 1 API-boundary scope and carried into next phase.
5. Slice 1E: Completed (verification + carry-over registration)
   - required gate set executed:
     - `uv run python scripts/check_api_runtime_factories.py`
     - `uv run python scripts/check_bootstrap_wiring_ownership.py`
     - `uv run python scripts/check_boundary_dto_purity.py`
     - `uv run mypy --strict`
     - `uv run lint-imports`
   - raw outputs serialized to:
     - `docs/architecture/audits/static_checks/latest/phase1e_01_check_api_runtime_factories.txt`
     - `docs/architecture/audits/static_checks/latest/phase1e_02_check_bootstrap_wiring_ownership.txt`
     - `docs/architecture/audits/static_checks/latest/phase1e_03_check_boundary_dto_purity.txt`
     - `docs/architecture/audits/static_checks/latest/phase1e_04_mypy_strict.txt`
     - `docs/architecture/audits/static_checks/latest/phase1e_05_lint_imports.txt`
   - gate outcomes:
     - `check_api_runtime_factories`: pass
     - `check_bootstrap_wiring_ownership`: pass
     - `check_boundary_dto_purity`: pass
     - `mypy --strict`: pass (`Success: no issues found in 165 source files`)
     - `lint-imports`: fail only on `no cross-layer shortcut imports`
       - kept: `engine.api cannot import engine.runtime or engine.platform`
       - kept: `engine.domain cannot import engine.api`
       - carry-over scope: runtime/rendering/window/input coupling to `engine.api.*` (next phase decomposition item)
   - associated test execution (Phase 1 impacted slices):
     - `PYTHONPATH=. uv run pytest tests/engine/unit/api -q` -> pass (`38 passed`)
     - `PYTHONPATH=. uv run pytest tests/engine/unit/runtime -q` -> pass (`109 passed`)
     - `PYTHONPATH=. uv run pytest tests/engine/unit/gameplay -q` -> pass (`11 passed`)
     - `PYTHONPATH=. uv run pytest tests/warships/unit/app/test_engine_hosted_runtime.py tests/warships/unit/app/test_engine_game_module.py tests/warships/unit/app/test_controller.py tests/warships/unit/app/services tests/warships/integration/app_engine -q` -> pass (`62 passed`)
   - note:
     - `tests/engine/unit/api/test_import_boundaries.py` was aligned to current approved architecture model by allowing Warships composition-layer imports through `engine.runtime` / `engine.gameplay` in addition to `engine.api` (still blocking other engine-internal layer imports).

### Boundary Correction (Post-Phase 1E, strict model restoration)

1. Boundary policy correction applied:
   - reverted boundary test relaxation; Warships game layer is strict again:
     - `tests/engine/unit/api/test_import_boundaries.py` now enforces `warships/game` imports engine only via `engine.api`.
2. `warships/game` runtime import removal:
   - removed direct `engine.runtime` / `engine.gameplay` imports from:
     - `warships/game/app/controller.py`
     - `warships/game/app/controller_state.py`
     - `warships/game/app/services/session_flow.py`
     - `warships/game/app/ports/runtime_services.py`
     - `warships/game/app/engine_game_module.py`
   - introduced API-only default contract implementations for game-side wiring in:
     - `warships/game/app/ports/engine_api_defaults.py`
3. App-shell composition extraction:
   - moved hosted runtime composition entry out of game layer into app shell:
     - added `warships/engine_hosted_runtime.py` (runtime imports allowed in shell).
     - converted `warships/game/app/engine_hosted_runtime.py` to compatibility wrapper with no engine runtime imports.
   - logging composition moved to app shell:
     - `warships/game/infra/logging.py` now builds config only (`build_logging_config`).
     - `warships/main.py` applies `configure_engine_logging(...)`.
4. Stability fix during verification:
   - resolved `engine.runtime` package init cycle by removing eager heavy imports from `engine/runtime/__init__.py` (`EngineHost`, `EngineUIFramework`).
5. Verification status after correction:
   - strict boundary test: pass
     - `PYTHONPATH=. uv run pytest tests/engine/unit/api/test_import_boundaries.py -q`
   - mypy strict: pass (`167` source files)
   - Phase-1-associated suites rerun and passing (api/runtime/gameplay + warships app/integration slices).
   - Phase 1E gate state unchanged:
     - `check_api_runtime_factories`: pass
     - `check_bootstrap_wiring_ownership`: pass
     - `check_boundary_dto_purity`: pass
     - `mypy --strict`: pass
     - `lint-imports`: still failing only on `no cross-layer shortcut imports` (runtime->api coupling carry-over).

### Runtime-Owned Entrypoint Alignment

1. Removed workaround shell composition layer:
   - deleted `warships/engine_hosted_runtime.py`.
2. Added engine-owned runtime entrypoint:
   - `engine/runtime/entrypoint.py` with `run(module=EngineModule)`.
   - `engine/__init__.py` now exports `run`.
3. Added API composition contract for game declarations:
   - `engine/api/composition.py` (`EngineModule` protocol).
   - exported via `engine/api/__init__.py`.
4. Warships now supplies module declaration from game package:
   - `warships/game/app/engine_hosted_runtime.py` now defines `WarshipsModule` (API-only imports).
   - `warships/main.py` now calls `engine.run(module=WarshipsModule())` directly.
5. Boundary outcome:
   - no `engine.runtime`/`engine.gameplay` imports under `warships/game`.

### DI + SDK Migration (Composition Ownership Model)

1. Introduced API composition contracts for binder/resolver model:
   - `engine/api/composition.py` now defines:
     - `EngineModule.configure(binder)`
     - `ServiceBinder` / `ServiceResolver`
     - explicit opaque boundary types for controller/view/framework/binding values.
2. Introduced runtime-owned composition container:
   - `engine/runtime/composition_container.py` with lazy singleton factory resolution.
3. Introduced `engine.sdk` defaults (runtime-agnostic):
   - `engine/sdk/defaults.py`
   - `engine/sdk/__init__.py`
   - includes default implementations for dispatcher, flow program, screen stack, interaction modes, context, event bus, update loop, module graph.
4. Runtime entrypoint now composes via SDK defaults then applies game overrides:
   - `engine/runtime/entrypoint.py`
   - flow: bind SDK defaults -> `module.configure(container)` -> build controller/module via resolver.
5. Warships module declaration updated to DI model:
   - `warships/game/app/engine_hosted_runtime.py` (`WarshipsModule`) now:
     - uses resolver-provided SDK factories for controller wiring and module dependency injection.
     - configures session flow program and dispatcher factory from resolver-bound SDK defaults.
6. Game-side direct default-impl module removed:
   - deleted `warships/game/app/ports/engine_api_defaults.py`.
7. Game-controller/game-module now receive engine systems as injected dependencies:
   - `warships/game/app/controller.py` receives `screen_stack` + `interaction_modes`.
   - `warships/game/app/controller_state.py` requires `screen_stack`.
   - `warships/game/app/engine_game_module.py` receives `event_bus`, `runtime_context`, `update_loop`, `module_graph`.

Verification:
1. `mypy --strict`: pass (`170` files).
2. strict boundary test (`warships/game` engine imports via API only): pass.
3. impacted suites:
   - `tests/warships/unit/app/services`: pass
   - `tests/warships/unit/app/*`: pass
   - `tests/warships/integration/app_engine`: pass
   - `tests/engine/unit/api + runtime + gameplay`: pass
4. Phase 1E hard gates:
   - `check_api_runtime_factories`: pass
   - `check_bootstrap_wiring_ownership`: pass
   - `check_boundary_dto_purity`: pass
   - `lint-imports`: pass after architecture-contract alignment to runtime-owned composition (`engine.bootstrap -> engine.runtime -> engine.sdk -> engine.api -> engine.domain -> engine.platform`).

### Migration Completion Status

Status: **Complete (for the defined composition-ownership migration scope)**.

Completed outcomes:
1. `game` layer boundary is enforced:
   - no `engine.runtime`/`engine.gameplay` imports under `warships/game`.
2. Engine-owned composition is active:
   - `warships/main.py` calls `engine.run(module=WarshipsModule())`.
3. API contracts + DI surface exist:
   - `engine.api.composition` with `EngineModule`, `ServiceBinder`, `ServiceResolver`.
4. SDK layer exists and is runtime-agnostic:
   - `engine.sdk.defaults` provides default implementations for reusable engine contracts.
5. Runtime composes SDK defaults and game bindings:
   - `engine.runtime.entrypoint` + `engine.runtime.composition_container`.
6. All migration-critical verification checks are green:
   - `lint-imports`: pass
   - `check_api_runtime_factories`: pass
   - `check_bootstrap_wiring_ownership`: pass
   - `check_boundary_dto_purity`: pass
   - `mypy --strict`: pass
   - strict boundary tests and impacted unit/integration tests: pass.

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

## Migration Completion Checkpoint (Typed DI + Runtime-Owned Composition)

Date: 2026-02-22

### Raw outputs (post-migration)

All outputs captured under:
`docs/architecture/audits/static_checks/2026-02-22/`

1. `23_lint-imports_post_migration.txt`
2. `24_bootstrap_wiring_ownership_post_migration.txt`
3. `25_api_runtime_factories_post_migration.txt`
4. `26_boundary_dto_purity_post_migration.txt`
5. `27_mypy_strict_post_migration.txt`
6. `28_import_boundaries_pytest_post_migration.txt`
7. `29_policy_static_checks_post_migration.txt`

### Resolution status for previously open migration blockers

1. Import-linter cross-layer shortcuts and API->runtime coupling
   - Status: Resolved.
   - Evidence: `23_lint-imports_post_migration.txt` shows `3 kept, 0 broken`.

2. DI binder still string-key based
   - Status: Resolved.
   - Evidence:
     - Token contract: `engine/api/composition.py` (`bind_factory(token, ...)`, `resolve(token)`).
     - Runtime container: `engine/runtime/composition_container.py` (`resolve(TypeOrToken)` with runtime-owned singleton lifecycle).
     - SDK defaults register against API contract tokens in `engine/sdk/catalog.py`.
     - Verification scan: no remaining `resolver.resolve("...")` / `bind_*("...")` usages in `engine`, `warships`, `tests`.

3. Partial `engine.sdk` migration/no standardized service catalog
   - Status: Resolved for current runtime composition scope.
   - Evidence:
     - Canonical SDK default bindings and implementations exist in `engine/sdk/catalog.py` and `engine/sdk/defaults.py`.
     - Runtime entrypoint binds SDK defaults first (`engine/runtime/entrypoint.py`), then applies game module overrides.
     - Warships module resolves services via API contract tokens only (`warships/game/app/engine_hosted_runtime.py`).

4. Legacy runtime wiring paths outside binder model
   - Status: Resolved for the hosted runtime startup path.
   - Evidence:
     - `engine.run(module=...)` composition root in `engine/runtime/entrypoint.py`.
     - Hosted module creation path receives `ServiceResolver` and resolves dependencies via API contract tokens.
     - Ownership/factory boundary gates pass:
       - `24_bootstrap_wiring_ownership_post_migration.txt`
       - `25_api_runtime_factories_post_migration.txt`
       - `26_boundary_dto_purity_post_migration.txt`
       - `28_import_boundaries_pytest_post_migration.txt` (import boundary tests pass).

### Important remaining policy failures (outside this migration slice)

The unified static runner still fails due to existing non-composition debt, especially:
complexity, LOC budgets, exception policy, duplication, domain semantic leakage, cycle/registry/env gates.

Reference: `29_policy_static_checks_post_migration.txt`.

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

