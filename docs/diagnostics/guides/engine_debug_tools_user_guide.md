# Engine Debug Tools User Guide

## Scope
This guide covers day-to-day usage of:
- `tools.engine_monitor`
- `tools.engine_session_inspector`
- `tools.engine_repro_lab`

All tools assume diagnostics data under `tools/data/` by default.

## 1. Engine Monitor (live triage)
Engine side (same machine):
- Diagnostics HTTP bridge is enabled by default.
- Optional env overrides:
  - `ENGINE_DIAGNOSTICS_HTTP_ENABLED=0|1`
  - `ENGINE_DIAGNOSTICS_HTTP_HOST` (default `127.0.0.1`)
  - `ENGINE_DIAGNOSTICS_HTTP_PORT` (default `8765`)

Run:
```bash
python -m tools.engine_monitor.main --remote-url http://127.0.0.1:8765 --refresh-ms 750 --hitch-threshold-ms 25
```

Tabs:
- `Health`: rolling FPS/frame timing plus alert list.
- `Timeline`: recent frame/render trend lanes.
- `Hitch Analyzer`: largest hitches with top span contributor.
- `Render/Resize`: resize/pixel/viewport signal counts.

## 2. Session Inspector (offline analysis)
Run:
```bash
python -m tools.engine_session_inspector.main --logs-root tools/data/logs
```

Key workflows:
- Select session from top combobox.
- Use `Events` tab filters and payload panel for root-cause.
- Use `Profiling` tab for top offenders and hitch correlation.
- Use `Replay` tab for continuous playback and scrub.
- Use `Crash` tab for crash corridor context.

### Events presets and shortcuts
- Presets:
  - Select preset from `Preset` dropdown.
  - Click `Save Preset` to persist current filter set.
  - Presets are stored in `tools/data/config/session_inspector_presets.json`.
- Shortcuts:
  - `Ctrl+F`: focus Events search box.
  - `Ctrl+R`: apply current Events filters.
  - `F5`: refresh session list.
  - `Space`: toggle Replay play/pause.

## 3. Repro Lab (determinism/repro checks)
Single replay:
```bash
python -m tools.engine_repro_lab.main --replay-json tools/data/replay/session.json --report-out tools/data/repro/report.json
```

Batch replay validation:
```bash
python -m tools.engine_repro_lab.main --batch-dir tools/data/replay
```

Differential comparison:
```bash
python -m tools.engine_repro_lab.main --baseline-dir tools/data/replay_baseline --candidate-dir tools/data/replay_candidate
```

Exit codes:
- `0`: pass / no regressions
- `1`: failed validation / regressions found
- `2`: invalid CLI input

