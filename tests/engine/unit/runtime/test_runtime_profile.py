from __future__ import annotations

from engine.runtime_profile import resolve_runtime_profile, resolve_runtime_profile_name


def test_runtime_profile_defaults_to_release_like(monkeypatch) -> None:
    monkeypatch.delenv("ENGINE_RUNTIME_PROFILE", raising=False)
    assert resolve_runtime_profile_name() == "release-like"
    profile = resolve_runtime_profile()
    assert profile.name == "release-like"
    assert profile.render_loop_mode == "on_demand"
    assert profile.render_vsync is True


def test_runtime_profile_aliases_resolve(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_RUNTIME_PROFILE", "debug")
    assert resolve_runtime_profile_name() == "dev-debug"
    monkeypatch.setenv("ENGINE_RUNTIME_PROFILE", "dev_fast")
    assert resolve_runtime_profile_name() == "dev-fast"
    monkeypatch.setenv("ENGINE_RUNTIME_PROFILE", "release")
    assert resolve_runtime_profile_name() == "release-like"
