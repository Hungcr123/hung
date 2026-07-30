"""Verify Space_V hydration is single-flight per file revision, not globally serialized."""

from __future__ import annotations

import concurrent.futures
import tempfile
import threading
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def main() -> int:
    original = {
        "qmdict_source_signature": app.qmdict_source_signature,
        "load_future_lesson_document": app.load_future_lesson_document,
        "hydrate_space_v_payload_with_qmdict": app.hydrate_space_v_payload_with_qmdict,
        "encode_future_payload_code": app.encode_future_payload_code,
        "html_bytes": app.html_bytes,
    }
    calls = 0
    calls_lock = threading.Lock()

    def load_lesson(path: Path):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.08)
        return {"k": "ftv", "w": [{"w": path.stem}]}, None

    try:
        app.qmdict_source_signature = lambda: {"mtime_ns": 10, "size": 20}
        app.load_future_lesson_document = load_lesson
        app.hydrate_space_v_payload_with_qmdict = lambda payload: (payload, {"hydrated": 1, "removed": 0})
        app.encode_future_payload_code = lambda payload: payload["w"][0]["w"]
        app.html_bytes = lambda value: str(value).encode("utf-8")
        app.SPACE_V_QMDICT_PAYLOAD_CACHE.clear()
        app.SPACE_V_QMDICT_SINGLEFLIGHT.clear()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shared = root / "shared.Space_V"
            shared.write_text("shared", encoding="utf-8")
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                shared_rows = list(pool.map(lambda _index: app.cached_space_v_qmdict_file_bytes(shared), range(12)))
            shared_elapsed = time.perf_counter() - started
            assert calls == 1, calls
            assert len({row[0] for row in shared_rows}) == 1
            assert shared_elapsed < 0.35, shared_elapsed

            app.SPACE_V_QMDICT_PAYLOAD_CACHE.clear()
            calls = 0
            paths = []
            for index in range(8):
                path = root / f"file-{index}.Space_V"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                distinct_rows = list(pool.map(app.cached_space_v_qmdict_file_bytes, paths))
            distinct_elapsed = time.perf_counter() - started
            assert calls == len(paths), calls
            assert len({row[0] for row in distinct_rows}) == len(paths)
            assert distinct_elapsed < 0.35, distinct_elapsed
    finally:
        for name, value in original.items():
            setattr(app, name, value)
        app.SPACE_V_QMDICT_PAYLOAD_CACHE.clear()
        app.SPACE_V_QMDICT_SINGLEFLIGHT.clear()

    print("space_v_qmdict_singleflight=ok same_key=one_compute distinct_keys=parallel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
