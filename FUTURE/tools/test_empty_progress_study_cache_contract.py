#!/usr/bin/env python3
"""Contract for the shared zero-progress lesson study summary cache."""

from __future__ import annotations

import concurrent.futures
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


# Added 2026-08-01: prove cross-user reuse is limited to empty indexes and exact revisions.
def main() -> int:
    original = app.summarize_lesson_study
    calls = []
    delay_summary = threading.Event()

    def fake_summary(path, username="", progress_index=None, time_index=None, **kwargs):
        calls.append({"username": username, "progress": bool(progress_index), "time": bool(time_index)})
        if delay_summary.is_set():
            time.sleep(0.05)
        return {"nodes": 8, "mine": 0, "progress": {}}

    app.summarize_lesson_study = fake_summary
    app.LESSON_EMPTY_PROGRESS_STUDY_CACHE.clear()
    try:
        common = {
            "progress_relative_path": "common/file.Space_Q",
            "path_is_effective": True,
            "progress_relative_paths": ["common/file.Space_Q"],
            "strict_progress_paths": False,
            "file_meta": {"mtime_ns": 10, "size": 20, "dependency_signature": "a", "lesson_id": "ftg-lesson-cache"},
            "lesson_id": "ftg-lesson-cache",
        }
        first = app.summarize_lesson_study_cached_empty_progress(Path("C:/server data/common/file.Space_Q"), "user-a", {}, {}, **common)
        second = app.summarize_lesson_study_cached_empty_progress(Path("C:/server data/common/file.Space_Q"), "user-b", {}, {}, **common)
        if first != second or len(calls) != 1:
            raise RuntimeError(f"empty cross-user cache miss: calls={calls}")
        string_alias = {**common, "progress_relative_paths": "common/file.Space_Q"}
        third = app.summarize_lesson_study_cached_empty_progress(Path("C:/server data/common/file.Space_Q"), "user-c", {}, {}, **string_alias)
        if third != first or len(calls) != 1:
            raise RuntimeError(f"string alias was not normalized: calls={calls}")
        app.summarize_lesson_study_cached_empty_progress(Path("C:/server data/common/file.Space_Q"), "user-c", {("Space_Q", "x"): {}}, {}, **common)
        if len(calls) != 2 or not calls[-1]["progress"]:
            raise RuntimeError(f"non-empty progress incorrectly reused cache: calls={calls}")
        changed = {**common, "file_meta": {**common["file_meta"], "mtime_ns": 11}}
        app.summarize_lesson_study_cached_empty_progress(Path("C:/server data/common/file.Space_Q"), "user-d", {}, {}, **changed)
        if len(calls) != 3:
            raise RuntimeError(f"revision change did not invalidate cache: calls={calls}")
        concurrent_common = {**common, "file_meta": {**common["file_meta"], "mtime_ns": 12}}
        barrier = threading.Barrier(16)
        delay_summary.set()

        def concurrent_read(index: int) -> dict:
            barrier.wait()
            return app.summarize_lesson_study_cached_empty_progress(
                Path("C:/server data/common/file.Space_Q"), f"concurrent-{index}", {}, {}, **concurrent_common
            )

        calls_before = len(calls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(concurrent_read, range(16)))
        if len(calls) != calls_before + 1 or any(result != results[0] for result in results):
            raise RuntimeError(f"concurrent cache miss was not single-flight: calls={len(calls) - calls_before}")
        print("empty_progress_study_cache_contract=ok shared_empty=1 string_alias=1 nonempty_bypass=1 revision_invalidation=1 singleflight=16_to_1")
        return 0
    finally:
        app.summarize_lesson_study = original
        app.LESSON_EMPTY_PROGRESS_STUDY_CACHE.clear()


if __name__ == "__main__":
    raise SystemExit(main())
