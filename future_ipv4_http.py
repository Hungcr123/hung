from __future__ import annotations

import http.client
import io
import socket
import ssl
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit


# Added 2026-07-22: Gemini-only IPv4 transport avoids broken IPv6 without changing global networking.
def ipv4_https_request_bytes(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    timeout: float = 20.0,
) -> tuple[bytes, dict[str, float | int | str]]:
    parsed = urlsplit(str(url or ""))
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("IPv4 transport requires an HTTPS URL.")
    host = parsed.hostname
    port = int(parsed.port or 443)
    budget = max(1.0, float(timeout or 20.0))
    started = time.perf_counter()
    dns_started = time.perf_counter()
    infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    dns_ms = (time.perf_counter() - dns_started) * 1000.0
    addresses: list[str] = []
    for info in infos:
        address = str(info[4][0] or "")
        if address and address not in addresses:
            addresses.append(address)
    if not addresses:
        raise OSError(f"No IPv4 address found for {host}.")

    timing: dict[str, float | int | str] = {
        "dns_ms": round(dns_ms, 3),
        "ipv4_candidates": len(addresses),
        "ipv4_address": "",
        "tcp_ms": 0.0,
        "tls_ms": 0.0,
        "model_ms": 0.0,
        "read_ms": 0.0,
        "total_ms": 0.0,
    }
    deadline = time.monotonic() + budget
    connection = http.client.HTTPSConnection(host, port, timeout=budget, context=ssl.create_default_context())

    def connect_ipv4(_address, timeout_value=None, source_address=None):
        last_error: OSError | None = None
        for address in addresses:
            remaining = max(0.25, deadline - time.monotonic())
            tcp_started = time.perf_counter()
            try:
                sock = socket.create_connection((address, port), timeout=remaining, source_address=source_address)
                timing["ipv4_address"] = address
                timing["tcp_ms"] = round((time.perf_counter() - tcp_started) * 1000.0, 3)
                return sock
            except OSError as exc:
                last_error = exc
        raise last_error or OSError(f"Could not connect to {host} over IPv4.")

    connection._create_connection = connect_ipv4
    try:
        connect_started = time.perf_counter()
        connection.connect()
        connect_ms = (time.perf_counter() - connect_started) * 1000.0
        timing["tls_ms"] = round(max(0.0, connect_ms - float(timing["tcp_ms"])), 3)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        request_started = time.perf_counter()
        connection.request(method.upper(), path, body=data, headers=dict(headers or {}))
        response = connection.getresponse()
        timing["model_ms"] = round((time.perf_counter() - request_started) * 1000.0, 3)
        read_started = time.perf_counter()
        raw = response.read()
        timing["read_ms"] = round((time.perf_counter() - read_started) * 1000.0, 3)
        timing["total_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        timing["status"] = int(response.status or 0)
        if int(response.status or 0) >= 400:
            raise HTTPError(url, int(response.status), str(response.reason or "HTTP error"), response.headers, io.BytesIO(raw))
        return raw, timing
    finally:
        connection.close()
