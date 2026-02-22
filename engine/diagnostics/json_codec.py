"""Fast JSON codec helpers for diagnostics/export paths."""

from __future__ import annotations

import json
from importlib import import_module
from typing import Any


def _optional_import(name: str) -> Any | None:
    try:
        return import_module(name)
    except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
        return None


_ORJSON = _optional_import("orjson")


def dumps_bytes(
    payload: Any,
    *,
    pretty: bool = False,
    sort_keys: bool = False,
    compact: bool = True,
) -> bytes:
    """Serialize payload to UTF-8 JSON bytes using fastest available backend."""
    if _ORJSON is None:
        raise RuntimeError("orjson is required for diagnostics serialization paths")
    if compact:
        options = int(getattr(_ORJSON, "OPT_APPEND_NEWLINE", 0))
        # We control newline emission ourselves for line-oriented exports.
        options = 0
        if pretty:
            options |= int(getattr(_ORJSON, "OPT_INDENT_2", 0))
        if sort_keys:
            options |= int(getattr(_ORJSON, "OPT_SORT_KEYS", 0))
        try:
            return bytes(_ORJSON.dumps(payload, option=options))
        except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ImportError):
            raise
    text = json.dumps(
        payload,
        ensure_ascii=True,
        separators=None,
        indent=2 if pretty else None,
        sort_keys=bool(sort_keys),
    )
    return text.encode("utf-8")


def dumps_text(
    payload: Any,
    *,
    pretty: bool = False,
    sort_keys: bool = False,
    compact: bool = True,
) -> str:
    return dumps_bytes(
        payload,
        pretty=pretty,
        sort_keys=sort_keys,
        compact=compact,
    ).decode("utf-8")


__all__ = ["dumps_bytes", "dumps_text"]

