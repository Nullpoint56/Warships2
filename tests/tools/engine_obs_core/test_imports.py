from __future__ import annotations

from importlib import import_module


def test_p0_scaffolds_import() -> None:
    modules = [
        "tools.engine_monitor.main",
        "tools.engine_obs_core",
        "tools.engine_obs_core.contracts",
        "tools.engine_obs_core.datasource.base",
        "tools.engine_obs_core.datasource.file_source",
        "tools.engine_obs_core.datasource.live_source",
        "tools.engine_repro_lab.main",
        "tools.engine_session_inspector.main",
    ]
    for module_name in modules:
        assert import_module(module_name) is not None
