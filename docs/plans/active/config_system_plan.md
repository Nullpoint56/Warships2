# Config System Plan (Engine Static + App Dynamic)

## Goal
Replace env-driven runtime behavior with a typed configuration system that is:

- Engine-safe: static, immutable, validated, predictable.
- App-flexible: dynamic hot-reload for selected game/app settings.
- Boundary-clean: engine does not assume Warships; app config uses engine APIs.

## Motivation
Current env usage is fragmented and hard to scale:

- Runtime behavior depends on process environment state.
- Validation is shallow and scattered.
- Hot iteration needs are mixed with startup-only settings.
- Engine/app boundaries are easy to blur via ad-hoc access.

We need a typed config architecture before more complexity (network/audio/game tuning) lands.

---

## Architecture

### 1) Engine Config (Static)
Engine config is loaded once at startup and treated as immutable.

Scope:
- Window mode and startup dimensions.
- Renderer/backend mode.
- Engine diagnostics capabilities and defaults.
- Engine logging defaults/fallback policy.
- Engine-level paths (where relevant and generic).

Properties:
- Strict schema validation.
- Fail-fast on invalid configuration.
- No hot-reload.
- No direct env access in runtime logic.

### 2) App/Game Config (Dynamic)
App config supports runtime hot-reload for safe fields only.

Scope:
- Debug UI/input toggles.
- Diagnostics verbosity/sampling.
- Gameplay tuning candidates (safe subset).
- App UX/dev options.

Properties:
- Versioned immutable snapshots.
- Atomic swap on successful validation.
- Safe field updates only.
- Invalid updates rejected without disrupting runtime.

---

## Ownership Rules

1. `engine/*` owns config mechanism contracts used by engine runtime.
2. `warships/*` owns app policy and dynamic value selection.
3. Engine must not import Warships.
4. App may consume engine config/logging APIs only (not runtime internals).

---

## File Layout (Planned)

Engine:
- `engine/api/config.py` (contracts/types)
- `engine/runtime/config.py` (loader/validator/normalizer)
- `engine/config/engine.toml`
- `engine/config/engine.local.toml` (optional, ignored)

App:
- `warships/game/config/model.py`
- `warships/game/config/loader.py`
- `warships/game/config/manager.py`
- `warships/config/app.toml`
- `warships/config/app.local.toml` (optional, ignored)

Docs:
- `docs/config_architecture.md`
- `docs/config_reference_engine.md`
- `docs/config_reference_app.md`
- `docs/config_hot_reload.md`

---

## Runtime Model

### Engine startup
1. Load and validate engine static config.
2. Initialize engine logging fallback from static config.
3. Start runtime with explicit typed config object injection.

### App startup
1. Load static + dynamic app config from file(s).
2. Initialize app logging policy via engine logging API.
3. Build `ConfigManager` with snapshot version `v1`.
4. Inject `ConfigManager` into app runtime/services.

### Hot reload path (app dynamic only)
1. File watcher/poller detects update.
2. Parse + validate config candidate.
3. Compute diff against current snapshot.
4. If valid:
   - atomically publish new snapshot/version
   - notify subscribers of changed sections.
5. If invalid:
   - reject candidate
   - log structured validation errors
   - keep current snapshot.

---

## Execution Plan

## Phase 1: Engine Static Typed Config
Tasks:
- Add typed engine config contracts/models.
- Implement file loader + strict validation.
- Wire bootstrap/host/diagnostics/logging defaults to config object.
- Remove direct `os.getenv` reads from engine runtime logic paths.

Deliverables:
- Engine boots from config files only.
- Engine fallback logging still works standalone.
- Unit tests for parsing/validation/path normalization.

Acceptance:
- No behavior regressions for current runtime.
- Invalid engine config fails fast with clear errors.

## Phase 2: App Typed Config (No Hot Reload Yet)
Tasks:
- Add typed app config model (static + dynamic sections).
- Implement app config loader and normalization.
- Wire app-data/logs/presets/saves path handling through typed config.
- Remove app runtime dependency on env flags.

Deliverables:
- App startup fully config-file driven.
- Paths resolved from config with sane defaults.

Acceptance:
- Existing app behavior preserved.
- App destination paths and logging remain deterministic.

## Phase 3: Dynamic Config Manager + Hot Reload
Tasks:
- Add `ConfigManager` with immutable snapshots and versioning.
- Add watcher/poller for app config changes.
- Add safe-field update routing (explicit allow-list).
- Emit structured reload success/failure logs.

Deliverables:
- Runtime updates for dynamic config fields without restart.
- Invalid reloads safely rejected.

Acceptance:
- No crashes on malformed edits.
- Safe fields update live; restart-required fields are flagged.

## Phase 4: Env Decommissioning
Tasks:
- Remove env loading from runtime path.
- Keep optional transitional compatibility layer only if required.
- Update tests and docs to config-file-first workflow.

Deliverables:
- No runtime behavior depends on env variables.
- Clear migration guide env->config mapping.

Acceptance:
- Fresh clone runs with config files only.
- Legacy env path either removed or isolated behind explicit compatibility mode.

## Phase 5: Documentation + Playbook
Tasks:
- Add complete config references and examples.
- Add hot-reload troubleshooting guide.
- Document safe vs restart-required fields.

Deliverables:
- Clear operator/developer docs.
- Predictable maintenance workflow.

Acceptance:
- Team can modify config safely without code edits.

---

## Validation & Testing

Unit:
- Schema validation and defaults.
- Invalid enum/range failures.
- Relative/absolute path normalization.
- Snapshot diffing and field-level change detection.

Integration:
- End-to-end startup with config files only.
- Hot-reload applies valid changes.
- Hot-reload rejects invalid changes and preserves current state.

Non-functional:
- Low overhead while no config changes occur.
- No frame-loop blocking on watcher updates.

---

## Risks and Mitigations

Risk: Overly broad hot-reload scope.
- Mitigation: strict allow-list for dynamic fields.

Risk: Boundary regressions (app importing runtime internals).
- Mitigation: enforce imports through engine API modules only.

Risk: Silent fallback behavior.
- Mitigation: fail-fast validation + explicit defaults documented.

---

## Decision Notes

- Static engine config + dynamic app config is intentional and recommended.
- Dynamic engine config is deferred to avoid runtime complexity and nondeterminism.
- Config files become source of truth; env usage is phased out.
