from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from FUTURE.server_parts.worker_jobs.heavy_language_jobs import (  # type: ignore
    set_worker_process_status,
    synthesize_message_audio_worker,
    warm_language_worker,
    worker_clean,
)


VOICE_STATE = {
    "ready": False,
    "loading": False,
    "last_error": "",
    "last_voice": "",
    "last_ms": 0,
    "warmed_at": 0.0,
}
VOICE_STATE_LOCK = threading.RLock()
VOICE_JOB_SEMAPHORE = threading.BoundedSemaphore(max(1, int(os.environ.get("FUTURE_VOICE_WORKER_SLOTS", "1") or "1")))
VOICE_WARM_THREAD: threading.Thread | None = None


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def voice_state() -> dict:
    with VOICE_STATE_LOCK:
        return {
            "ok": True,
            "service": "future-voice-worker-2",
            "ready": bool(VOICE_STATE.get("ready")),
            "loading": bool(VOICE_STATE.get("loading")),
            "last_error": worker_clean(VOICE_STATE.get("last_error", "")),
            "last_voice": worker_clean(VOICE_STATE.get("last_voice", "")),
            "last_ms": int(VOICE_STATE.get("last_ms", 0) or 0),
            "warmed_at": float(VOICE_STATE.get("warmed_at", 0.0) or 0.0),
            "pid": os.getpid(),
        }


def warm_voice_background(model: bool = False) -> bool:
    global VOICE_WARM_THREAD
    with VOICE_STATE_LOCK:
        if VOICE_WARM_THREAD and VOICE_WARM_THREAD.is_alive():
            return False
        VOICE_STATE["loading"] = True
        VOICE_STATE["last_error"] = ""

    def runner() -> None:
        started = time.perf_counter()
        try:
            warm_language_worker("voice")
            if model:
                warm_language_worker("voice-model")
            with VOICE_STATE_LOCK:
                VOICE_STATE.update({
                    "ready": True,
                    "loading": False,
                    "last_error": "",
                    "last_ms": int((time.perf_counter() - started) * 1000),
                    "warmed_at": time.time(),
                })
            print("Future voice worker 2 ready.", flush=True)
        except Exception as exc:
            with VOICE_STATE_LOCK:
                VOICE_STATE.update({"ready": False, "loading": False, "last_error": str(exc)})
            print(f"Future voice worker 2 warm failed: {exc}", flush=True)

    VOICE_WARM_THREAD = threading.Thread(target=runner, name="future-voice-worker-2-warm", daemon=True)
    VOICE_WARM_THREAD.start()
    return True


class FutureVoiceWorkerHandler(BaseHTTPRequestHandler):
    server_version = "FutureVoiceWorker2/1.0"

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
            self.send_json(200, voice_state())
            return
        self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        try:
            payload = self.read_json_body()
            if path == "/warm":
                started = warm_voice_background(model=bool(payload.get("model", False)))
                self.send_json(202, {"ok": True, "started": started, **voice_state()})
                return
            if path == "/synthesize":
                text = str(payload.get("text", "") or "").strip()
                voice = worker_clean(payload.get("voice", payload.get("voice_key", "")))
                if not text:
                    raise RuntimeError("Tin nhan dang trong.")
                if not voice:
                    raise RuntimeError("Chua chon voice.")
                if not VOICE_JOB_SEMAPHORE.acquire(blocking=False):
                    self.send_json(429, {"ok": False, "error": "Voice worker dang ban, hay thu lai sau.", **voice_state()})
                    return
                started_at = time.perf_counter()
                try:
                    result = synthesize_message_audio_worker(text, voice)
                finally:
                    VOICE_JOB_SEMAPHORE.release()
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                with VOICE_STATE_LOCK:
                    VOICE_STATE.update({
                        "ready": True,
                        "loading": False,
                        "last_error": "",
                        "last_voice": voice,
                        "last_ms": elapsed_ms,
                        "warmed_at": VOICE_STATE.get("warmed_at") or time.time(),
                    })
                self.send_json(200, {"ok": True, "worker_process_ms": elapsed_ms, **result, **voice_state()})
                return
            self.send_json(404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            with VOICE_STATE_LOCK:
                VOICE_STATE.update({"loading": False, "last_error": str(exc)})
            self.send_json(500, {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **voice_state()})

    def log_message(self, fmt, *args):
        print(f"[VOICE2 {time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}", flush=True)


def main() -> int:
    set_worker_process_status("voice-worker")
    parser = argparse.ArgumentParser(description="Future persistent voice worker 2")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8879)
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--warm-model", action="store_true")
    args = parser.parse_args()
    if args.warm or args.warm_model:
        warm_voice_background(model=bool(args.warm_model))
    httpd = ThreadingHTTPServer((args.host, int(args.port)), FutureVoiceWorkerHandler)
    print(f"Future voice worker 2 listening at http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
