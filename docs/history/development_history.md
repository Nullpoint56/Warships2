# Warships + Engine Development History

This document captures major progress milestones across engine and game development so we can archive old planning docs without losing context.

## 2026-02 - Architecture and Boundary Stabilization

- Engine-hosted runtime shape was established and documented.
- Engine and game responsibilities were separated with stricter boundaries.
- Import boundary rules and automated guard tests were introduced.
- Canonical docs:
  - `docs/architecture/system_overview.md`
  - `docs/architecture/import_boundaries.md`

## 2026-02 - Testing and Quality Enablement

- Engine and Warships test plans were created and executed.
- Coverage baselines and quality gates were defined and enforced.
- These plans are now historical because their initial rollout goals were met.
- Archived docs:
  - `docs/plans/archive/engine_test_plan.md`
  - `docs/plans/archive/warships_test_plan.md`
  - `docs/plans/archive/quality_ci_enablement_plan.md`

## 2026-02 - Rendering Resize and Scheduling Investigations

- Extensive investigation was done around resize artifacts, frame pacing, and scheduling behavior.
- Multiple experimental plans were produced and executed to isolate causes.
- These are now retained as historical references for future renderer work.
- Archived docs:
  - `docs/plans/archive/rendering_resize_resolution_plan.md`
  - `docs/plans/archive/rendering_mode_migration_plan.md`

## 2026-02 onward - Diagnostics and Observability Rebuild

- Diagnostics moved to a data-first, engine-owned model.
- A dedicated diagnostics documentation set now owns design, implementation phases, and user/dev guides.
- Canonical docs:
  - `docs/diagnostics/design/engine_observability_rebuild_design.md`
  - `docs/diagnostics/design/engine_debug_tools_design.md`
  - `docs/diagnostics/implementation/engine_debug_tools_implementation_plan.md`
  - `docs/diagnostics/guides/engine_debug_tools_user_guide.md`
  - `docs/diagnostics/guides/engine_debug_tools_dev_guide.md`

## Active Forward Work

- Config system evolution: `docs/plans/active/config_system_plan.md`
- Engine generalization evolution: `docs/plans/active/engine_generalization_plan.md`
- Diagnostics implementation phases: `docs/diagnostics/implementation/engine_debug_tools_implementation_plan.md`

## Curation Policy

1. This history file is the canonical summary ledger.
2. Root-level plan sprawl is intentionally avoided.
3. Obsolete docs are archived instead of deleted, with a history entry added here.
