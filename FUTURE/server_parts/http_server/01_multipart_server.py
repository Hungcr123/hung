# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

import threading
import time
import ipaddress

# Added 2026-08-02: serialize low-priority builder enqueues only while learner traffic is active.
BUILDER_TTS_ENQUEUE_LOCK = threading.Lock()

def parse_multipart_form(headers, rfile, max_bytes: int = 80 * 1024 * 1024) -> tuple[dict[str, str], dict[str, dict]]:
    content_type = clean(headers.get("Content-Type", ""))
    if not content_type.lower().startswith("multipart/form-data"):
        raise RuntimeError("Expected multipart/form-data request.")
    try:
        content_length = int(headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise RuntimeError("Invalid Content-Length.") from exc
    if content_length <= 0:
        raise RuntimeError("Empty request body.")
    if max_bytes and content_length > max_bytes:
        raise RuntimeError("Request body qua lon.")
    body = rfile.read(content_length)
    raw = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n\r\n"
    ).encode("utf-8") + body
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if not message.is_multipart():
        raise RuntimeError("Malformed multipart body.")
    fields: dict[str, str] = {}
    files: dict[str, dict] = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = clean(part.get_param("name", header="content-disposition"))
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = clean(part.get_filename(""))
        if filename:
            files[name] = {
                "filename": filename,
                "content_type": clean(part.get_content_type()),
                "data": payload,
            }
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, errors="replace")
    return fields, files


class FutureThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = bounded_env_int("FUTURE_HTTP_BACKLOG", 128, 32, 512)
    _future_request_accept_times: dict[int, float] = {}
    _future_request_accept_times_lock = threading.Lock()
    _future_active_requests = 0
    _future_last_request_at = 0.0

    # Added 2026-07-29: start the quiet clock when HTTP binds, not at the first
    # request, so startup warmers cannot race ahead of the initial client burst.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._future_active_requests = 0
        self._future_last_request_at = time.monotonic()

    def process_request(self, request, client_address):
        try:
            fileno = int(request.fileno())
        except Exception:
            fileno = -1
        if fileno >= 0:
            with self._future_request_accept_times_lock:
                self._future_request_accept_times[fileno] = time.perf_counter()
        return super().process_request(request, client_address)

    def finish_request(self, request, client_address):
        try:
            return super().finish_request(request, client_address)
        finally:
            try:
                fileno = int(request.fileno())
            except Exception:
                fileno = -1
            if fileno >= 0:
                with self._future_request_accept_times_lock:
                    self._future_request_accept_times.pop(fileno, None)

    # Added 2026-07-29: CPU-heavy startup warmers yield to the first real HTTP
    # burst so cold login/completion work is served before derived cache work.
    def wait_for_request_quiet(self, quiet_seconds: float = 0.75, max_wait_seconds: float = 10.0) -> dict:
        started = time.monotonic()
        while time.monotonic() - started < max(0.0, float(max_wait_seconds or 0.0)):
            with self._future_request_accept_times_lock:
                active = max(0, int(self._future_active_requests or 0))
                last_request_at = float(self._future_last_request_at or 0.0)
            quiet_for = time.monotonic() - last_request_at if last_request_at > 0 else float(quiet_seconds or 0.0)
            if active <= 0 and quiet_for >= max(0.0, float(quiet_seconds or 0.0)):
                return {"quiet": True, "waited_ms": round((time.monotonic() - started) * 1000.0, 3)}
            time.sleep(0.05)
        return {"quiet": False, "waited_ms": round((time.monotonic() - started) * 1000.0, 3)}


# Added 2026-07-31: worker long-polls use a separate LAN listener and never
# expose the normal web routes through the worker port or public tunnel.
class FutureWorkerHTTPServer(FutureThreadingHTTPServer):
    future_worker_only = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bound long-poll request threads independently from the learner web listener.
        self.future_worker_max_threads = bounded_env_int("FUTURE_DISTRIBUTED_WORKER_HTTP_THREADS", 128, 16, 512)
        self._future_worker_slots = threading.BoundedSemaphore(self.future_worker_max_threads)
        self.future_worker_rejected_requests = 0

    def process_request(self, request, client_address):
        if not self._future_worker_slots.acquire(timeout=0.25):
            self.future_worker_rejected_requests += 1
            try:
                request.close()
            except Exception:
                pass
            return
        try:
            return super().process_request(request, client_address)
        except Exception:
            self._future_worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            return super().process_request_thread(request, client_address)
        finally:
            self._future_worker_slots.release()


def future_worker_listener_allows(self, path: str, method: str) -> bool:
    """Keep the dedicated worker listener private and route-scoped."""
    if not bool(getattr(self.server, "future_worker_only", False)):
        return True
    target = clean(path).rstrip("/") or "/"
    allowed = target == "/health" or target.startswith("/distributed-worker/")
    try:
        remote = ipaddress.ip_address(clean(self.client_address[0] if self.client_address else ""))
        private = bool(remote.is_private or remote.is_loopback)
    except ValueError:
        private = False
    if allowed and private:
        return True
    self.send_error(404 if allowed else 403)
    return False
