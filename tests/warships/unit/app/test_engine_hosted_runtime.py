from __future__ import annotations

import warships.game.app.engine_hosted_runtime as runtime_mod


def test_run_engine_hosted_app_builds_controller_and_invokes_runtime(monkeypatch) -> None:
    called = {"run": 0}

    class _Controller:
        pass

    monkeypatch.setattr(runtime_mod, "_build_controller", lambda: _Controller())

    def _fake_run(*, module_factory, host_config):
        called["run"] += 1
        assert host_config.window_mode in {"windowed", "maximized", "fullscreen", "borderless"}
        _ = module_factory

    monkeypatch.setattr(runtime_mod, "run_hosted_runtime", _fake_run)
    runtime_mod.run_engine_hosted_app()
    assert called["run"] == 1
