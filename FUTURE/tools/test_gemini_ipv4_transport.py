"""Regression for Gemini-only IPv4 transport and duplicate fallback suppression."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app
import future_ipv4_http as ipv4_http


def main() -> None:
    original_request = ipv4_http.ipv4_https_request_bytes
    original_available = app.distributed_worker_gemini_available
    original_worker = app.distributed_worker_try_gemini_model_once
    original_worker_flag = os.environ.get("FUTURE_GEMINI_USE_DISTRIBUTED_WORKER")
    calls = []

    def fake_request(url, **kwargs):
        calls.append((url, kwargs))
        return json.dumps({"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}).encode(), {
            "dns_ms": 1.0,
            "tcp_ms": 2.0,
            "tls_ms": 3.0,
            "model_ms": 4.0,
            "read_ms": 0.1,
            "total_ms": 10.1,
            "status": 200,
        }

    try:
        ipv4_http.ipv4_https_request_bytes = fake_request
        os.environ.pop("FUTURE_GEMINI_USE_DISTRIBUTED_WORKER", None)
        app.distributed_worker_gemini_available = lambda: True
        data = app.request_gemini_model_once("test-key", "gemini-test", b"{}")
        assert app.extract_gemini_text(data) == "OK"
        assert len(calls) == 1
        assert data["_future_gemini"]["attempt_id"] == "local-ipv4-1"

        os.environ["FUTURE_GEMINI_USE_DISTRIBUTED_WORKER"] = "1"
        app.distributed_worker_try_gemini_model_once = lambda *_args, **_kwargs: None
        try:
            app.request_gemini_model_once("test-key", "gemini-test", b"{}")
        except TimeoutError as exc:
            assert "duplicate local retry suppressed" in str(exc)
        else:
            raise AssertionError("worker timeout must not repeat the same request locally")
        assert len(calls) == 1
    finally:
        ipv4_http.ipv4_https_request_bytes = original_request
        app.distributed_worker_gemini_available = original_available
        app.distributed_worker_try_gemini_model_once = original_worker
        if original_worker_flag is None:
            os.environ.pop("FUTURE_GEMINI_USE_DISTRIBUTED_WORKER", None)
        else:
            os.environ["FUTURE_GEMINI_USE_DISTRIBUTED_WORKER"] = original_worker_flag

    source = (ROOT / "future_ipv4_http.py").read_text(encoding="utf-8")
    worker_source = (ROOT / "FUTURE/server2/future_distributed_worker_client.py").read_text(encoding="utf-8")
    gemini_worker_source = worker_source.split("def gemini_job", 1)[1].split("def phonemize_job", 1)[0]
    assert "socket.AF_INET" in source
    assert "ipv4_https_request_bytes(" in gemini_worker_source
    assert "urlopen(" not in gemini_worker_source
    print("gemini_ipv4_transport=ok af_inet=true default_local_ipv4=true local_attempts=1 worker_duplicate_suppressed=true worker_shared_transport=true")


if __name__ == "__main__":
    main()
