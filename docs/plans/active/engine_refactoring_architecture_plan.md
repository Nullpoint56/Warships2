# Architecture refactoring template

This document is a template for doing architectural refactors of the engine. It contains two main sections
- Static Check Findings: Signals collected from static checkers
- LLM Check Findings: LLM executed check signals

Each Check finding part contains these fields:
- Evaluations: Raw output interpretations (very verbose to not miss details)
- Investigation: Raw output signals are rarely the ones we need to react on. They usually hide deeper issues. Because of that, investigation section is an investigation of why the Raw check signals appeared.
- Proposed fixes: Investigation reveals root causes, proposed fixes are higher level decisions and documented approaches on how the identified root causes will be fixed.
- Refactoring Phase-Plan: Proposed fixes will be broken down from high level plans into low level actionable, phase by phase fix executions. Phase plans are specific to Static and LLM check execution, and they contain a list of phases with actionable items derived from the specific check type's proposed fixes section.

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

### Proposed fixes

### Refactoring Phase-Plan


## LLM Check Findings

### Evaluations

### Investigation

### Proposed fixes

### Refactoring Phase-Plan
