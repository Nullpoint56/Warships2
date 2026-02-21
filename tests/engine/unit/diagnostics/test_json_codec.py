from __future__ import annotations

from engine.diagnostics.json_codec import dumps_bytes, dumps_text


def test_dumps_text_roundtrip_ascii() -> None:
    payload = {"k": "v", "n": 1, "arr": [1, 2, 3]}
    raw = dumps_text(payload)
    assert isinstance(raw, str)
    assert "\"k\":\"v\"" in raw


def test_dumps_bytes_pretty_mode() -> None:
    payload = {"a": 1, "b": {"c": 2}}
    raw = dumps_bytes(payload, pretty=True)
    text = raw.decode("utf-8")
    assert "\n" in text
    assert "  " in text

