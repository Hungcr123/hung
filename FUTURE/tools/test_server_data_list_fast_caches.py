#!/usr/bin/env python3
"""Focused regression for persistent vocab metadata and serialized list caching."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ftg-list-cache-") as temp_dir:
        root = Path(temp_dir)
        lesson = root / "common" / "Cache Probe.Space_V"
        lesson.parent.mkdir(parents=True, exist_ok=True)
        source_lesson = Path(r"C:\server data\common\File 02 - {7}.Space_V")
        assert source_lesson.is_file(), source_lesson
        shutil.copyfile(source_lesson, lesson)

        original_root = app.SERVER_DATA_ROOT
        original_index_path = app.VOCAB_FILE_META_INDEX_PATH
        original_loader = app.load_future_lesson_document
        try:
            app.SERVER_DATA_ROOT = root
            app.VOCAB_FILE_META_INDEX_PATH = root / "runtime" / "vocab_file_meta_index_v1.json"
            app.VOCAB_FILE_META_RAM_CACHE.clear()
            app.VOCAB_FILE_META_INDEX_STATE.update({
                "loaded": False,
                "rows": {},
                "revision": 0,
                "first_dirty_at": 0.0,
                "timer": None,
            })
            first = app.lesson_file_vocab_meta_for_target(lesson)
            assert first.get("vocab_word_keys"), first
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not app.VOCAB_FILE_META_INDEX_PATH.is_file():
                time.sleep(0.05)
            assert app.VOCAB_FILE_META_INDEX_PATH.is_file()

            app.VOCAB_FILE_META_RAM_CACHE.clear()
            app.VOCAB_FILE_META_INDEX_STATE.update({
                "loaded": False,
                "rows": {},
                "revision": 0,
                "first_dirty_at": 0.0,
                "timer": None,
            })
            app.load_future_lesson_document = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unchanged lesson decoded"))
            second = app.lesson_file_vocab_meta_for_target(lesson)
            assert second == first, (first, second)

            cache_key = "v2|full|deferred-tasks|space-task-deferred|admin|admin|hung|hung|hung|hung"
            signature = ("manifest", "progress", "vault")
            payload = {"ok": True, "entries": [{"type": "file", "path": "hung/a.Space_W", "study": {"progress": {"percent": 10}}}]}
            built = app.remember_server_data_list(cache_key, signature, payload)
            cached = app.get_cached_server_data_list(cache_key, signature)
            assert built["_response_bytes"] == cached["_response_bytes"]
            assert cached["_response_cache_hit"] is True
            old_etag = cached["_response_etag"]
            patched = app.patch_server_data_list_cache_study(["hung/a.Space_W"], {"progress": {"percent": 20}}, "hung")
            assert patched == 1
            refreshed = app.get_cached_server_data_list(cache_key, signature)
            assert refreshed["_response_etag"] != old_etag
            assert json.loads(refreshed["_response_bytes"])["entries"][0]["study"]["progress"]["percent"] == 20
        finally:
            app.load_future_lesson_document = original_loader
            app.SERVER_DATA_ROOT = original_root
            app.VOCAB_FILE_META_INDEX_PATH = original_index_path
            app.VOCAB_FILE_META_RAM_CACHE.clear()
            app.clear_server_data_list_cache()

    print("server data list fast cache tests passed")


if __name__ == "__main__":
    main()
