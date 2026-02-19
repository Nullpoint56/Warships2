# Documentation Hub

This folder is organized by intent so documentation stays coherent as the engine and game evolve.

## Structure

- `docs/architecture/`: stable architecture and boundary contracts.
- `docs/operations/`: operational runbooks (build/package/release workflows).
- `docs/diagnostics/`: active diagnostics design, implementation plan, and guides.
- `docs/plans/active/`: plans that are still open or expected to continue.
- `docs/plans/archive/`: superseded or completed plans preserved for history.
- `docs/history/`: project-level progress history and major decisions.
- `docs/archive/`: legacy archives kept for traceability.

## Canonical Start Points

1. System architecture: `docs/architecture/system_overview.md`
2. Import boundaries: `docs/architecture/import_boundaries.md`
3. Runtime configuration: `docs/operations/runtime_configuration.md`
4. Current diagnostics direction: `docs/diagnostics/README.md`
5. Current active plans: `docs/plans/README.md`
6. Project progress history: `docs/history/development_history.md`

## Curation Rules

1. Keep docs in one canonical location; do not duplicate equivalent docs under multiple folders.
2. When a plan completes or is replaced, move it to `docs/plans/archive/` and add a summary entry to `docs/history/development_history.md`.
3. Keep generated site artifacts (`docs/site/build/`) out of manual curation.
4. Prefer additive updates to history over keeping many stale draft docs at the root.
