"""Compatibility shim: runtime observability delegates to diagnostics implementation."""

from __future__ import annotations

from engine.diagnostics import observability as _obs


def __getattr__(name: str) -> object:
    return getattr(_obs, name)


__all__ = [name for name in dir(_obs) if not name.startswith("_")]
