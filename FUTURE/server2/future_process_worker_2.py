from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SERVER2_ROOT = Path(__file__).resolve().parent
FUTURE_ROOT = SERVER2_ROOT.parent
APP_ROOT = FUTURE_ROOT.parent

for item in (str(APP_ROOT), str(FUTURE_ROOT)):
    if item not in sys.path:
        sys.path.insert(0, item)

from FUTURE.server_parts.worker_jobs.heavy_language_jobs import warm_language_worker  # noqa: E402


PROCESS_STATE = {
    "ready": True,
    "loading": False,
    "last_error": "",
    "last_ms": 0,
    "jobs": 0,
    "warmed": {},
}
PROCESS_LOCK = threading.RLock()
JOB_SEMAPHORE = threading.BoundedSemaphore(max(1, int(os.environ.get("FUTURE_PROCESS_WORKER_SLOTS", "1") or "1")))
ALLOWED_MODULES = {"FUTURE.server_parts.worker_jobs.heavy_language_jobs"}


def clean(value: object = "") -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def worker_state() -> dict:
    with PROCESS_LOCK:
        return {
            "ok": True,
            "service": "future-process-worker-2",
            "ready": bool(PROCESS_STATE.get("ready")),
            "loading": bool(PROCESS_STATE.get("loading")),
            "last_error": clean(PROCESS_STATE.get("last_error", "")),
            "last_ms": int(PROCESS_STATE.get("last_ms", 0) or 0),
            "jobs": int(PROCESS_STATE.get("jobs", 0) or 0),
            "warmed": dict(PROCESS_STATE.get("warmed") if isinstance(PROCESS_STATE.get("warmed"), dict) else {}),
            "pid": os.getpid(),
        }


def set_state(**kwargs) -> None:
    with PROCESS_LOCK:
        PROCESS_STATE.update(kwargs)


def import_allowed_function(module_name: str, function_name: str):
    module_name = clean(module_name)
    function_name = clean(function_name)
    if module_name not in ALLOWED_MODULES:
        raise RuntimeError(f"Worker module is not allowed: {module_name}")
    if not function_name or function_name.startswith("_"):
        raise RuntimeError("Worker function is not allowed.")
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name, None)
    if not callable(fn):
        raise RuntimeError(f"Worker function is unavailable: {function_name}")
    return fn


def warm_kinds(kinds: list[str]) -> dict:
    requested = [clean(kind).lower() for kind in kinds if clean(kind)]
    if not requested:
        requested = ["translate", "qmdict", "phonetic", "spacy"]
    started = time.perf_counter()
    results = {}
    set_state(loading=True, last_error="")
    try:
        for kind in requested:
            result = warm_language_worker(kind)
            results[kind] = result
        with PROCESS_LOCK:
            warmed = PROCESS_STATE.setdefault("warmed", {})
            if isinstance(warmed, dict):
                warmed.update({kind: time.time() for kind in results.keys()})
        return {"ok": True, "warmed": results, "warm_ms": int((time.perf_counter() - started) * 1000), **worker_state()}
    finally:
        set_state(loading=False)


class FutureProcessWorkerHandler(BaseHTTPRequestHandler):
    server_version = "FutureProcessWorker2/1.0"

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(max(0, length)) if length else b"{}"
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def send_json(self, status: int, payload: dict) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/health":
            self.send_json(200, worker_state())
            return
        self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        try:
            payload = self.read_json_body()
            if path == "/warm":
                kinds = payload.get("kinds") if isinstance(payload.get("kinds"), list) else []
                self.send_json(202, warm_kinds(kinds))
                return
            if path == "/run":
                if not JOB_SEMAPHORE.acquire(blocking=False):
                    self.send_json(429, {"ok": False, "error": "Process worker is busy.", **worker_state()})
                    return
                started = time.perf_counter()
                try:
                    fn = import_allowed_function(payload.get("module", ""), payload.get("function", ""))
                    args = payload.get("args") if isinstance(payload.get("args"), list) else []
                    kwargs = payload.get("kwargs") if isinstance(payload.get("kwargs"), dict) else {}
                    result = fn(*args, **kwargs)
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    with PROCESS_LOCK:
                        PROCESS_STATE["jobs"] = int(PROCESS_STATE.get("jobs", 0) or 0) + 1
                        PROCESS_STATE["last_ms"] = elapsed_ms
                        PROCESS_STATE["last_error"] = ""
                    self.send_json(200, {"ok": True, "result": result, "worker_process_ms": elapsed_ms, **worker_state()})
                finally:
                    JOB_SEMAPHORE.release()
                return
            self.send_json(404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            set_state(last_error=str(exc), loading=False)
            self.send_json(500, {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **worker_state()})

    def log_message(self, fmt, *args):
        print(f"[PROCESS2 {time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}", flush=True)


def warm_background() -> None:
    def runner() -> None:
        try:
            warm_kinds(["translate", "qmdict", "phonetic", "spacy"])
        except Exception as exc:
            set_state(last_error=str(exc), loading=False)
            print(f"Future process worker 2 warm failed: {exc}", flush=True)

    threading.Thread(target=runner, name="future-process-worker-2-warm", daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Future persistent process worker 2")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8880)
    parser.add_argument("--warm", action="store_true")
    args = parser.parse_args()
    if args.warm:
        warm_background()
    httpd = ThreadingHTTPServer((args.host, int(args.port)), FutureProcessWorkerHandler)
    print(f"Future process worker 2 listening at http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
