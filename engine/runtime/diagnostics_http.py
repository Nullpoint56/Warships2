"""Local HTTP bridge for live diagnostics polling by external tools."""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Any

from engine.api.debug import get_diagnostics_snapshot, get_metrics_snapshot, get_profiling_snapshot
from engine.diagnostics.json_codec import dumps_bytes

_LOG = logging.getLogger("engine.runtime.diag_http")


class DiagnosticsHttpServer:
    """Serve diagnostics snapshots over localhost HTTP in a background thread."""

    def __init__(
        self,
        *,
        host_obj: Any,
        bind_host: str,
        bind_port: int,
    ) -> None:
        self._host_obj = host_obj
        self._bind_host = bind_host
        self._bind_port = int(bind_port)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        return f"http://{self._bind_host}:{self._bind_port}"

    def start(self) -> None:
        if self._server is not None:
            return
        owner = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                owner._handle_get(self)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer((self._bind_host, self._bind_port), _Handler)
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="diag-http", daemon=True)
        self._thread.start()
        _LOG.info("diagnostics_http_started endpoint=%s", self.endpoint)

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        self._server = None
        try:
            server.shutdown()
            server.server_close()
        finally:
            thread = self._thread
            self._thread = None
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)
        _LOG.info("diagnostics_http_stopped endpoint=%s", self.endpoint)

    def _handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        raw_path = handler.path or "/"
        parsed = urlparse(raw_path)
        path = parsed.path or "/"
        query = parse_qs(parsed.query or "")
        snapshot_limit = _query_int(query, "limit", 5000, min_value=100, max_value=50000)
        profiling_limit = _query_int(query, "limit", 2000, min_value=100, max_value=50000)
        try:
            if path.startswith("/snapshot"):
                payload = asdict(get_diagnostics_snapshot(self._host_obj, limit=snapshot_limit))
                return self._write_json(handler, 200, payload)
            if path.startswith("/metrics"):
                payload = asdict(get_metrics_snapshot(self._host_obj))
                return self._write_json(handler, 200, payload)
            if path.startswith("/profiling"):
                payload = asdict(get_profiling_snapshot(self._host_obj, limit=profiling_limit))
                return self._write_json(handler, 200, payload)
            if path.startswith("/health"):
                return self._write_json(
                    handler,
                    200,
                    {
                        "status": "ok",
                        "endpoint": self.endpoint,
                    },
                )
            return self._write_json(handler, 404, {"error": "not_found", "path": path})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            # Client dropped the socket while we were writing; this is expected under polling timeouts.
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _LOG.exception("diagnostics_http_request_failed path=%s", path)
            return self._write_json(handler, 500, {"error": str(exc)})

    @staticmethod
    def _write_json(
        handler: BaseHTTPRequestHandler, status: int, payload: dict[str, object]
    ) -> None:
        raw = dumps_bytes(payload)
        try:
            handler.send_response(int(status))
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(raw)))
            handler.end_headers()
            handler.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return


def _query_int(
    query: dict[str, list[str]],
    key: str,
    default: int,
    *,
    min_value: int,
    max_value: int,
) -> int:
    raw_values = query.get(key)
    if not raw_values:
        return int(default)
    raw = str(raw_values[0]).strip()
    try:
        value = int(raw)
    except ValueError:
        return int(default)
    return max(min_value, min(max_value, value))
