"""Quick backend probe for window/event-loop overhead and integration readiness."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _probe_rendercanvas_glfw(duration_s: float) -> dict[str, Any]:
    try:
        from engine.window.rendercanvas_glfw import create_rendercanvas_window
    except Exception as exc:  # pragma: no cover
        return {"backend": "rendercanvas_glfw", "status": "error", "error": str(exc)}
    window = create_rendercanvas_window(width=640, height=360, title="probe", update_mode="ondemand")
    try:
        start = time.perf_counter()
        samples = 0
        events = 0
        while (time.perf_counter() - start) < duration_s:
            drained = window.poll_events()
            events += len(drained)
            samples += 1
            time.sleep(0.001)
        elapsed = max(1e-9, time.perf_counter() - start)
        return {
            "backend": "rendercanvas_glfw",
            "status": "ok",
            "samples": samples,
            "events": events,
            "poll_hz": samples / elapsed,
        }
    finally:
        window.close()


def _probe_direct_glfw(duration_s: float) -> dict[str, Any]:
    try:
        import glfw  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        return {"backend": "direct_glfw", "status": "error", "error": str(exc)}
    if not glfw.init():
        return {"backend": "direct_glfw", "status": "error", "error": "glfw.init failed"}
    window = None
    try:
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        window = glfw.create_window(640, 360, "probe", None, None)
        if not window:
            return {"backend": "direct_glfw", "status": "error", "error": "create_window failed"}
        start = time.perf_counter()
        samples = 0
        while (time.perf_counter() - start) < duration_s:
            glfw.poll_events()
            samples += 1
            time.sleep(0.001)
        elapsed = max(1e-9, time.perf_counter() - start)
        return {
            "backend": "direct_glfw",
            "status": "ok",
            "samples": samples,
            "poll_hz": samples / elapsed,
            "wgpu_surface_ready": False,
            "note": "no direct get_context('wgpu') provider in current engine contract",
        }
    finally:
        if window is not None:
            glfw.destroy_window(window)
        glfw.terminate()


def main() -> None:
    duration_s = 1.5
    payload = {
        "duration_s": duration_s,
        "probes": [
            _probe_rendercanvas_glfw(duration_s),
            _probe_direct_glfw(duration_s),
        ],
    }
    out = Path("artifacts/window_backend_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

