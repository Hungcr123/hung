#!/usr/bin/env python3
"""Prove idle HTTP/1.1 sockets do not count as in-flight learner requests."""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
HTTP_PARTS = ROOT / "FUTURE" / "server_parts" / "http_server"


def load_runtime_classes():
    """Load the real split fragments with the minimum globals needed by this gate."""
    runtime_globals = {
        "BaseHTTPRequestHandler": BaseHTTPRequestHandler,
        "ThreadingHTTPServer": ThreadingHTTPServer,
        "threading": threading,
        "time": time,
        "clean": lambda value: str(value or "").strip(),
        "bounded_env_int": lambda _name, default, _minimum, _maximum: default,
    }
    server_source = (HTTP_PARTS / "01_multipart_server.py").read_text(encoding="utf-8-sig")
    exec(compile(server_source, str(HTTP_PARTS / "01_multipart_server.py"), "exec"), runtime_globals)

    handler_namespace = {}
    handler_source = (HTTP_PARTS / "02_handler_core.py").read_text(encoding="utf-8-sig")
    exec(compile(handler_source, str(HTTP_PARTS / "02_handler_core.py"), "exec"), runtime_globals, handler_namespace)

    release_slow = threading.Event()

    class ProbeHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        parse_request = handler_namespace["parse_request"]
        handle_one_request = handler_namespace["handle_one_request"]

        def do_GET(self):
            if self.path == "/slow":
                release_slow.wait(timeout=5)
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    return runtime_globals["FutureThreadingHTTPServer"], ProbeHandler, release_slow


def wait_for(predicate, timeout: float = 3.0) -> bool:
    """Wait briefly for the threaded handler to publish its counter transition."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def main() -> int:
    server_class, handler_class, release_slow = load_runtime_classes()
    server = server_class(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    sessions = [requests.Session() for _ in range(8)]
    try:
        for session in sessions:
            response = session.get(f"{base}/fast", timeout=3)
            response.raise_for_status()
        if not wait_for(lambda: server._future_active_requests == 0):
            raise AssertionError(f"idle keep-alive sockets counted as active: {server._future_active_requests}")

        slow_result = {}

        def run_slow() -> None:
            slow_result["response"] = sessions[0].get(f"{base}/slow", timeout=6)

        slow_thread = threading.Thread(target=run_slow)
        slow_thread.start()
        if not wait_for(lambda: server._future_active_requests == 1):
            raise AssertionError(f"in-flight request was not counted: {server._future_active_requests}")
        release_slow.set()
        slow_thread.join(timeout=7)
        if slow_thread.is_alive():
            raise AssertionError("slow request did not finish")
        slow_result["response"].raise_for_status()
        if not wait_for(lambda: server._future_active_requests == 0):
            raise AssertionError(f"completed request remained active: {server._future_active_requests}")

        print({"ok": True, "idle_keepalive_connections": len(sessions), "active_during_slow": 1, "active_after": 0})
        return 0
    finally:
        release_slow.set()
        for session in sessions:
            session.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
