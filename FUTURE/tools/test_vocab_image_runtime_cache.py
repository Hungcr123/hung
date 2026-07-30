"""Regression for coalesced Space_V Openverse image lookup and negative caching."""

from __future__ import annotations

import atexit
import concurrent.futures
import json
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def main() -> int:
    source = (ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "07_qmlearn_audio_spacev_repair.py").read_text(encoding="utf-8")
    frontend = (ROOT / "FUTURE" / "web" / "js_parts" / "12_question_translation_loader.js").read_text(encoding="utf-8")
    if "from future_vocab_builder_gui import fetch_vocab_image" in source:
        raise RuntimeError("Runtime image lookup still imports the GUI builder")
    if "vocabImageResultCache.set(key" not in frontend or "10 * 60 * 1000" not in frontend:
        raise RuntimeError("Frontend negative image cache is missing")

    original_urlopen = app.urlopen
    original_load_cache = app.server_database_load_vocab_image_cache
    original_load_cache_rows = app.server_database_load_vocab_image_cache_rows
    original_store_cache = app.server_database_store_vocab_image_cache_batch
    calls = 0
    calls_lock = threading.Lock()

    def success_urlopen(_request, timeout=0):
        nonlocal calls
        with calls_lock:
            calls += 1
        return FakeResponse({"results": [{
            "thumbnail": "https://example.test/apple.jpg",
            "provider": "unit",
            "title": "Apple",
            "filetype": "jpg",
        }]})

    try:
        app.urlopen = success_urlopen
        app.server_database_load_vocab_image_cache = lambda _key: None
        app.server_database_load_vocab_image_cache_rows = lambda _limit=2048: []
        app.server_database_store_vocab_image_cache_batch = lambda rows: len(rows)
        with app.SPACE_V_DYNAMIC_IMAGE_CACHE_LOCK:
            app.SPACE_V_DYNAMIC_IMAGE_CACHE.clear()
            app.SPACE_V_DYNAMIC_IMAGE_INFLIGHT.clear()
            app.SPACE_V_DYNAMIC_IMAGE_SQLITE_LOADED = False
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            list(pool.map(lambda _index: app.qmdict_space_v_image_lookup("Unit Apple Image"), range(100)))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            row = app.qmdict_space_v_image_lookup("Unit Apple Image")
            if row.get("image", {}).get("u"):
                break
            time.sleep(0.02)
        if calls != 1 or row.get("image", {}).get("u") != "https://example.test/apple.jpg":
            raise RuntimeError(f"Positive image lookup did not coalesce: calls={calls}")
        app.qmdict_space_v_image_lookup("Unit Apple Image")
        if calls != 1:
            raise RuntimeError("Positive image cache missed on the second lookup")

        def failed_urlopen(_request, timeout=0):
            nonlocal calls
            with calls_lock:
                calls += 1
            raise URLError("offline")

        app.urlopen = failed_urlopen
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            list(pool.map(lambda _index: app.qmdict_space_v_image_lookup("Unit No Image Word"), range(100)))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            missing = app.qmdict_space_v_image_lookup("Unit No Image Word")
            if not missing.get("pending"):
                break
            time.sleep(0.02)
        if calls != 2 or missing.get("image"):
            raise RuntimeError(f"Negative image lookup did not coalesce: calls={calls}")
        app.qmdict_space_v_image_lookup("Unit No Image Word")
        if calls != 2:
            raise RuntimeError("Negative image cache missed on the second lookup")
        time.sleep(1.2)
    finally:
        app.urlopen = original_urlopen
        app.server_database_load_vocab_image_cache = original_load_cache
        app.server_database_load_vocab_image_cache_rows = original_load_cache_rows
        app.server_database_store_vocab_image_cache_batch = original_store_cache
        try:
            atexit.unregister(app.flush_auth_sessions_to_disk)
        except Exception:
            pass

    print("vocab_image_runtime_cache=ok gui_import=false async_pool=6 positive_calls=1 negative_calls=1 frontend_retry=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
