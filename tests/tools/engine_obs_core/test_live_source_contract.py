from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.engine_obs_core.datasource.live_source import LiveObsSource


@dataclass(frozen=True)
class _FakeEvent:
    ts_utc: str
    tick: int
    category: str
    name: str
    level: str
    value: float | int | str | bool | dict
    metadata: dict


@dataclass(frozen=True)
class _FakeSpan:
    tick: int
    category: str
    name: str
    start_s: float
    end_s: float
    duration_ms: float
    metadata: dict


@dataclass(frozen=True)
class _FakeMetrics:
    frame_count: int = 2
    rolling_frame_ms: float = 12.5
    rolling_fps: float = 80.0
    max_frame_ms: float = 21.0
    resize_count: int = 1
    resize_event_to_apply_p95_ms: float = 0.1
    resize_apply_to_frame_p95_ms: float = 0.2
    rolling_render_ms: float = 3.2


@dataclass(frozen=True)
class _FakeProfiling:
    mode: str = "on"
    span_count: int = 1
    top_spans_ms: list[tuple[str, float]] = None  # type: ignore[assignment]
    spans: list[_FakeSpan] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.top_spans_ms is None:
            object.__setattr__(self, "top_spans_ms", [("render:present", 2.2)])
        if self.spans is None:
            object.__setattr__(
                self,
                "spans",
                [
                    _FakeSpan(
                        tick=10,
                        category="render",
                        name="present",
                        start_s=1.0,
                        end_s=1.0022,
                        duration_ms=2.2,
                        metadata={},
                    )
                ],
            )


class _FakeHub:
    def snapshot(self, *, limit=None, category=None, name=None):
        _ = (limit, category, name)
        return [
            _FakeEvent(
                ts_utc="2026-01-01T00:00:00.000+00:00",
                tick=10,
                category="frame",
                name="frame.time_ms",
                level="info",
                value=16.0,
                metadata={},
            ),
            _FakeEvent(
                ts_utc="2026-01-01T00:00:00.000+00:00",
                tick=10,
                category="render",
                name="render.frame_ms",
                level="info",
                value=4.0,
                metadata={},
            ),
        ]


class _FakeHost:
    diagnostics_hub = _FakeHub()
    diagnostics_metrics_snapshot = _FakeMetrics()
    diagnostics_profiling_snapshot = _FakeProfiling()


def test_live_source_poll_contract() -> None:
    source = LiveObsSource(Path("."), host_provider=lambda: _FakeHost())
    snap = source.poll()
    assert len(snap.events) == 2
    assert len(snap.frame_points) == 1
    assert snap.frame_points[0].tick == 10
    assert snap.frame_points[0].frame_ms == 16.0
    assert len(snap.spans) == 1
    assert snap.rolling_fps == 80.0


def test_live_source_obs_methods() -> None:
    source = LiveObsSource(Path("."), host_provider=lambda: _FakeHost())
    session = source.list_sessions()[0]
    events = source.load_events(session)
    metrics = source.load_metrics(session)
    spans = source.load_spans(session, limit=10)
    replay = source.load_replay(session)
    crash = source.load_crash(session)

    assert session.id == "live"
    assert len(events) >= 1
    assert len(metrics.frame_points) >= 1
    assert len(spans) == 1
    assert replay.commands == []
    assert crash is None


def test_live_source_remote_poll(monkeypatch) -> None:
    source = LiveObsSource(Path("."), remote_url="http://127.0.0.1:8765")

    def fake_fetch(url: str):
        if url.endswith("/snapshot"):
            return {
                "events": [
                    {
                        "ts_utc": "2026-01-01T00:00:00.000+00:00",
                        "tick": 12,
                        "category": "frame",
                        "name": "frame.time_ms",
                        "level": "info",
                        "value": 20.0,
                        "metadata": {},
                    },
                    {
                        "ts_utc": "2026-01-01T00:00:00.000+00:00",
                        "tick": 12,
                        "category": "render",
                        "name": "render.frame_ms",
                        "level": "info",
                        "value": 5.0,
                        "metadata": {},
                    },
                ]
            }
        if url.endswith("/metrics"):
            return {
                "rolling_frame_ms": 20.0,
                "rolling_fps": 50.0,
                "rolling_render_ms": 5.0,
                "max_frame_ms": 24.0,
                "resize_count": 3,
            }
        if url.endswith("/profiling"):
            return {
                "spans": [
                    {
                        "tick": 12,
                        "category": "render",
                        "name": "present",
                        "start_s": 1.0,
                        "end_s": 1.005,
                        "duration_ms": 5.0,
                        "metadata": {},
                    }
                ]
            }
        return {}

    monkeypatch.setattr(source, "_fetch_json", fake_fetch)
    snap = source.poll()
    assert snap.rolling_fps == 50.0
    assert len(snap.events) == 2
    assert len(snap.frame_points) == 1
    assert snap.frame_points[0].tick == 12
