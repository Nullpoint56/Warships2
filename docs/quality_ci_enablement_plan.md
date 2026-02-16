# Quality + CI Enablement Plan

Date: 2026-02-16  
Scope: repository-wide (`engine/*`, `warships/*`, tests, packaging)

## What This Step Is Called

This is both:
1. **Repository hygiene**: defining local quality standards and developer checks.
2. **CI enablement**: enforcing those checks automatically on pull requests and main.

Practical name for this project: **Quality Gates + CI Rollout**.

## Goals

1. Make code quality checks easy to run locally.
2. Enforce the same checks in GitHub Actions.
3. Keep build and test reliability high while avoiding heavy process overhead.

## Non-Goals (for now)

1. Full release/deployment automation.
2. Strict typing in every module from day one.
3. Blocking PRs on optional diagnostics dashboards.

## Baseline Gates To Introduce

1. Ruff linting (`ruff check`).
2. Type checking (initially: mypy with scoped modules).
3. Existing pytest + coverage gates:
   - Engine coverage policy from `docs/engine_test_plan.md`.
   - Warships coverage policy from `docs/warships_test_plan.md`.

## Phased Rollout

## Phase Q1: Local Tooling and Config

1. Add dev dependencies:
   - `ruff`
   - `mypy`
2. Add tool config in `pyproject.toml`:
   - Ruff baseline rule set.
   - Type checker include/exclude and initial scope profile.
3. Add a local quality script:
   - `scripts/check.ps1`
   - Runs lint -> type check -> tests with coverage.

Exit criteria:
1. `uv run` can execute all quality checks locally with one command.
2. No IDE-only dependency for running checks.

## Phase Q2: GitHub Actions CI

1. Add workflow for PR/push quality gates.
2. Jobs (initial):
   - `lint` (ruff)
   - `typecheck` (mypy)
   - `test_engine` (coverage gate)
   - `test_warships` (coverage gate)
3. Cache `uv` dependencies to keep CI fast.
4. Fail PR when required gates fail.

Exit criteria:
1. Every PR runs all required quality jobs.
2. Branch protection can require these checks.

## Phase Q3: Packaging CI

1. Add Windows build workflow using existing packaging approach from `docs/build_windows_exe.md`.
2. Run on:
   - `main` pushes
   - tags (release candidates/finals)
3. Upload `dist/` artifact.
4. Keep this job non-blocking for PRs initially (or main-only) until stable.

Exit criteria:
1. Reproducible CI-built executable artifact is available from workflow runs.

## Phase Q4: Quality Hardening

1. Tighten type-checking scope incrementally:
   - Start with `engine/*` core boundaries.
   - Expand to `warships/game/app/services/*`, then broader modules.
2. Raise Ruff strictness in controlled steps.
3. Optionally add SonarQube as dashboard/reporting:
   - Track maintainability and smells.
   - Keep hard pass/fail logic in Ruff/type/tests.

Exit criteria:
1. Stable CI signal with low false positives.
2. Clear documented thresholds and ownership of failures.

## Proposed CI Commands (Initial)

1. `uv run ruff check .`
2. `uv run mypy`
3. `uv run pytest tests/engine --cov=engine --cov-report=term-missing`
4. `uv run pytest tests/warships --cov=warships.game --cov-report=term-missing`

## Risks and Mitigations

1. Risk: too many failures during first rollout.  
   Mitigation: introduce baseline with focused include paths and temporary targeted ignores.
2. Risk: CI time becomes slow.  
   Mitigation: cache dependencies, split jobs, run packaging only on main/tags.
3. Risk: typing noise from untyped third-party APIs.  
   Mitigation: configure stubs/ignores at boundaries; tighten gradually.

## Ownership and Operating Model

1. Quality gate failures are blocking for merges (except non-blocking packaging phase).
2. Any rule relaxation requires explicit commit with rationale in PR description.
3. Keep local and CI commands identical to avoid "works locally but fails in CI".

## Next Implementation Steps

1. Add Ruff + mypy config and dev dependencies in `pyproject.toml`.
2. Add `scripts/check.ps1`.
3. Add `.github/workflows/quality.yml` and `.github/workflows/build_windows.yml`.
4. Enable branch protection using required checks once stable.

## Implementation Status (Current)

Implemented now:
1. Dev dependencies added in `pyproject.toml`: `ruff`, `mypy`.
2. Initial Ruff gate enabled with low-noise baseline (`F` family first).
3. Initial mypy gate enabled with scoped paths:
   - `engine/api`
   - `engine/ui_runtime`
   - `warships/game/core`
   - `warships/game/presets`
4. Local check entrypoint added:
   - `scripts/check.ps1`
5. GitHub Actions workflows added:
   - `.github/workflows/quality.yml`
   - `.github/workflows/build_windows.yml`

Deferred intentionally:
1. Broader mypy scope and stricter Ruff rule sets will be raised incrementally.

## Next Branch: CI + Code Check Hardening

Recommended branch name:
1. `chore/ci-quality-hardening`

Objective:
1. Move from baseline quality gates to stricter, low-noise enforcement without disrupting delivery flow.

### H1: Formatter Rollout

1. Run repository-wide `ruff format` in a dedicated formatting-only PR.
2. Keep that PR free of behavior changes.
3. After merge, enable formatter checks:
   - local: add `uv run ruff format --check .` back to `scripts/check.ps1`
   - CI: add formatter check step back to `.github/workflows/quality.yml`

Exit criteria:
1. Formatter check passes in CI on new PRs.
2. No recurring style-drift diffs.

Status:
1. Implemented.
2. Repo-wide `ruff format` applied.
3. `ruff format --check` re-enabled in:
   - `scripts/check.ps1`
   - `.github/workflows/quality.yml`

### H2: Ruff Rule Expansion (Incremental)

1. Expand Ruff from `F` baseline to `I` (import/order hygiene).
2. Fix resulting issues in one focused pass.
3. Expand next to `E`, then `B`, then `UP` in small batches.
4. Keep each rule-family expansion in separate commits/PR sections for easy rollback.

Exit criteria:
1. Expanded rule set runs green in CI.
2. No high-noise false-positive patterns in active rule families.

Status:
1. In progress.
2. `I` (import/order hygiene) has been enabled in addition to `F`.
3. Import-order findings were auto-fixed (`ruff check --fix`) and baseline checks are green.
4. `E` has been enabled with temporary `E501` ignore to avoid noisy line-length churn.
5. `B` has been enabled; one assertion-pattern issue was fixed.
6. `UP` has been enabled with temporary ignores:
   - `UP042` (`StrEnum` migration)
   - `UP047` (PEP 695 type-parameter syntax migration)
7. Next Ruff hardening step: revisit `E501`, `UP042`, and `UP047` in focused cleanup PR(s).

### H3: Mypy Scope Expansion (Incremental)

1. Expand mypy scope in this order:
   - `engine/runtime`
   - `engine/input`
   - stable `warships/game/app/services/*`
2. Keep boundary pragmatism (`ignore_missing_imports = true`) while expanding.
3. Resolve type issues module-by-module before widening scope again.

Exit criteria:
1. Expanded mypy scope passes in CI.
2. No frequent type-gate churn for unchanged modules.

Status:
1. In progress.
2. Added to mypy scope:
   - `engine/runtime`
   - `engine/input`
   - `warships/game/app/services`
3. Type issues found during expansion were resolved:
   - runtime route/event variable typing in `engine/runtime/framework_engine.py` and `engine/runtime/pygfx_frontend.py`
   - generalized ship-order parameter typing (`Sequence[ShipType]`) in `warships/game/app/services/placement_editor.py`
4. Expanded mypy baseline currently passes on `48` source files.

### H4: CI Gate Tightening

1. Keep `Build Windows EXE` non-required initially.
2. Evaluate stability over multiple PRs/main runs.
3. Decide whether to make build required once flakiness is near-zero.

Exit criteria:
1. Required checks remain fast and reliable.
2. Build job policy is explicitly documented (required vs informational).

### H5: Docs and Developer UX

1. Update this document after each hardening milestone.
2. Add a short `README` section for standard quality commands:
   - `scripts/check.ps1`
   - build script usage
3. Keep local and CI commands aligned.

Exit criteria:
1. New contributors can run the same checks locally as CI with minimal setup.

### Hardening Done Criteria

1. `ruff check` + `ruff format --check` enforced in CI.
2. Mypy scope expanded beyond baseline modules with stable signal.
3. Existing test/coverage gates continue passing.
4. Branch protection rules map cleanly to maintained CI jobs.
