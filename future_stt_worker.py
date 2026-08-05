from __future__ import annotations

import argparse
import json
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import FUTURE_SERVER as future


WORKER_PRELOAD_LOCK = threading.Lock()
WORKER_PRELOAD_THREAD: threading.Thread | None = None


def clean(value: object = "") -> str:
    return future.clean(value)


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def worker_state() -> dict:
    model_cache = future.MODEL_CACHE if isinstance(future.MODEL_CACHE, dict) else {}
    server_state = future.SERVER_STATE if isinstance(future.SERVER_STATE, dict) else {}
    return {
        "ok": True,
        "service": "future-stt-worker",
        "ready": bool(model_cache.get("obj") is not None or server_state.get("ready")),
        "loading": bool(server_state.get("loading")),
        "model_name": clean(server_state.get("model_name", "")),
        "model_ref": clean(server_state.get("model_ref", "")),
        "language": clean(server_state.get("language", "en")) or "en",
        "device": clean(server_state.get("device", "cpu")) or "cpu",
        "compute_type": clean(server_state.get("compute_type", "int8")) or "int8",
        "last_error": clean(server_state.get("last_error", "")),
        "pid": __import__("os").getpid(),
    }


def preload_background(model_name: str, language: str) -> bool:
    global WORKER_PRELOAD_THREAD
    with WORKER_PRELOAD_LOCK:
        if WORKER_PRELOAD_THREAD and WORKER_PRELOAD_THREAD.is_alive():
            return False

        def runner() -> None:
            try:
                future.preload_model(model_name, language)
                print(f"Future STT worker ready: {future.SERVER_STATE.get('model_ref', '')}", flush=True)
            except Exception as exc:
                future.SERVER_STATE.update({"ready": False, "loading": False, "last_error": str(exc)})
                print(f"Future STT worker preload failed: {exc}", flush=True)

        WORKER_PRELOAD_THREAD = threading.Thread(target=runner, name="future-stt-worker-preload", daemon=True)
        WORKER_PRELOAD_THREAD.start()
        return True


class FutureSttWorkerHandler(BaseHTTPRequestHandler):
    server_version = "FutureSttWorker/1.0"

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
            if path == "/preload":
                model_name = clean(payload.get("model_name", payload.get("model", future.SERVER_STATE.get("model_name", "small")))) or "small"
                language = clean(payload.get("language", future.SERVER_STATE.get("language", "en"))) or "en"
                started = preload_background(model_name, language)
                self.send_json(202, {"ok": True, "started": started, **worker_state()})
                return
            if path == "/reference":
                text = future.lesson_task_notice_text(payload.get("text", ""), limit=6000)
                if not text:
                    raise RuntimeError("Text to Explore is empty.")
                self.send_json(200, {"ok": True, "speech_training": future.build_speech_reference_payload(text), **worker_state()})
                return
            if path == "/transcribe":
                audio_path = clean(payload.get("audio_path", ""))
                if not audio_path:
                    raise RuntimeError("Missing audio_path.")
                expected = clean(payload.get("expected", ""))
                model_name = clean(payload.get("model_name", payload.get("model", future.SERVER_STATE.get("model_name", "small")))) or "small"
                language = clean(payload.get("language", future.SERVER_STATE.get("language", "en"))) or "en"
                started_at = time.perf_counter()
                result = future.transcribe_audio(audio_path, model_name, language)
                text = clean(result.get("text", ""))
                words = list(result.get("words", []) or [])
                scoring = future.score_spoken(expected, text, words) if expected else {}
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                self.send_json(200, {
                    "ok": True,
                    "text": text,
                    "words": words,
                    "worker_process_ms": elapsed_ms,
                    **scoring,
                    **worker_state(),
                })
                return
            self.send_json(404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            future.SERVER_STATE.update({"loading": False, "last_error": str(exc)})
            self.send_json(500, {"ok": False, "error": str(exc), "traceback": traceback.format_exc(), **worker_state()})

    def log_message(self, fmt, *args):
        print(f"[STT {time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Future persistent STT worker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="en")
    parser.add_argument("--preload", action="store_true")
    args = parser.parse_args()
    future.configure_paths()
    future.enable_stt_fault_logging()
    future.SERVER_STATE["model_name"] = clean(args.model) or "small"
    future.SERVER_STATE["language"] = clean(args.language) or "en"
    if args.preload:
        preload_background(future.SERVER_STATE["model_name"], future.SERVER_STATE["language"])
    httpd = ThreadingHTTPServer((args.host, int(args.port)), FutureSttWorkerHandler)
    print(f"Future STT worker listening at http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
