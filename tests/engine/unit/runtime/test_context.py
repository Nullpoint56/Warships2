from __future__ import annotations

import pytest

from engine.api.context import create_runtime_context


def test_runtime_context_provide_get_require() -> None:
    context = create_runtime_context()
    context.provide("logger", {"name": "engine"})
    assert context.get("logger") == {"name": "engine"}
    assert context.require("logger") == {"name": "engine"}


def test_runtime_context_get_missing_returns_none() -> None:
    context = create_runtime_context()
    assert context.get("missing") is None


def test_runtime_context_require_missing_raises() -> None:
    context = create_runtime_context()
    with pytest.raises(KeyError):
        context.require("missing")


def test_runtime_context_rejects_empty_service_name() -> None:
    context = create_runtime_context()
    with pytest.raises(ValueError):
        context.provide("   ", object())
