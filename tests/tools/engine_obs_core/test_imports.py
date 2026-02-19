from __future__ import annotations


def test_p0_scaffolds_import() -> None:
    import tools.engine_obs_core  # noqa: F401
    import tools.engine_obs_core.contracts  # noqa: F401
    import tools.engine_obs_core.datasource.base  # noqa: F401
    import tools.engine_obs_core.datasource.file_source  # noqa: F401
    import tools.engine_obs_core.datasource.live_source  # noqa: F401
    import tools.engine_session_inspector.main  # noqa: F401
    import tools.engine_monitor.main  # noqa: F401
    import tools.engine_repro_lab.main  # noqa: F401
