from __future__ import annotations

from pathlib import Path


def test_phase6_runtime_uses_backend_neutral_names() -> None:
    root = Path(__file__).resolve().parents[4]
    required_files = (
        root / "engine/runtime/window_frontend.py",
        root / "engine/runtime/bootstrap.py",
        root / "engine/api/hosted_runtime.py",
        root / "engine/api/__init__.py",
        root / "warships/game/app/engine_hosted_runtime.py",
    )
    for path in required_files:
        assert path.exists(), f"missing expected runtime/api file: {path}"

    legacy_frontend = root / "engine/runtime/pygfx_frontend.py"
    assert not legacy_frontend.exists(), "legacy pygfx frontend module should not exist"

    no_legacy_runtime_tokens = (
        "run_pygfx_hosted_runtime",
        "create_pygfx_window",
        "pygfx_frontend",
    )
    for path in required_files:
        text = path.read_text(encoding="utf-8")
        for token in no_legacy_runtime_tokens:
            assert token not in text, f"legacy runtime token {token!r} found in {path}"

