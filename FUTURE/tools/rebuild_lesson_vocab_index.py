"""Build the persistent shared lesson vocabulary index after code validation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write the derived index. Without this flag only count candidates.")
    parser.add_argument("--full", action="store_true", help="Discard the old derived rows before rebuilding every supported lesson.")
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--evidence", default="")
    return parser.parse_args()


def supported_lessons() -> list[Path]:
    rows = []
    for path in app.SERVER_DATA_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in app.VOCAB_STATS_SUPPORTED_EXTENSIONS:
            continue
        try:
            if app.server_data_manifest_should_skip(path):
                continue
        except Exception:
            pass
        rows.append(path)
    return sorted(rows, key=lambda path: str(path).lower())


def main() -> int:
    args = parse_args()
    lessons = supported_lessons()
    if args.max_files > 0:
        lessons = lessons[: args.max_files]
    if not args.apply:
        print(json.dumps({"apply": False, "lessons": len(lessons), "index": str(app.VOCAB_FILE_META_INDEX_PATH)}, separators=(",", ":")))
        return 0

    globals_map = app.lesson_file_vocab_meta_for_target.__globals__
    original_schedule = globals_map["schedule_vocab_file_meta_index_write"]
    original_loader = globals_map["load_future_lesson_document"]
    original_lookup = globals_map["qmdict_lookup_summary"]
    decoded = {"count": 0}
    lookups = {"count": 0}
    errors = []
    rebuilt = 0
    reused = 0
    pg_before = app.postgres_metrics_snapshot() if hasattr(app, "postgres_metrics_snapshot") else {}
    wall_started = time.perf_counter()
    cpu_started = time.process_time()

    def counted_loader(*loader_args, **loader_kwargs):
        decoded["count"] += 1
        return original_loader(*loader_args, **loader_kwargs)

    def counted_lookup(*lookup_args, **lookup_kwargs):
        lookups["count"] += 1
        return original_lookup(*lookup_args, **lookup_kwargs)

    try:
        globals_map["schedule_vocab_file_meta_index_write"] = lambda: None
        globals_map["load_future_lesson_document"] = counted_loader
        globals_map["qmdict_lookup_summary"] = counted_lookup
        if args.full:
            with app.VOCAB_FILE_META_INDEX_LOCK:
                app.VOCAB_FILE_META_INDEX_STATE.update({
                    "loaded": True,
                    "rows": {},
                    "lessons": {},
                    "revision": int(app.VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0) + 1,
                    "first_dirty_at": 0.0,
                    "timer": None,
                })
            app.VOCAB_FILE_META_RAM_CACHE.clear()
        else:
            app.load_vocab_file_meta_index_once()

        for index, path in enumerate(lessons, 1):
            try:
                before = app.lesson_file_vocab_meta_cached_for_target(path)
                meta = app.lesson_file_vocab_meta_for_target(path)
                if not meta or not meta.get("lesson_id"):
                    raise RuntimeError("missing lesson_id vocabulary metadata")
                if before:
                    reused += 1
                else:
                    rebuilt += 1
            except Exception as exc:
                errors.append({"path": app.server_data_relative(path), "error": str(exc)})
            if index % 100 == 0 or index == len(lessons):
                print(f"lesson_vocab_index {index}/{len(lessons)} rebuilt={rebuilt} reused={reused} errors={len(errors)}", flush=True)

        revision = int(app.VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0)
        app.write_vocab_file_meta_index_snapshot(revision)
    finally:
        globals_map["schedule_vocab_file_meta_index_write"] = original_schedule
        globals_map["load_future_lesson_document"] = original_loader
        globals_map["qmdict_lookup_summary"] = original_lookup

    pg_after = app.postgres_metrics_snapshot() if hasattr(app, "postgres_metrics_snapshot") else {}
    evidence = {
        "schema": "lesson-vocab-index-rebuild-v1",
        "full": bool(args.full),
        "lessons": len(lessons),
        "rebuilt": rebuilt,
        "reused": reused,
        "errors": errors,
        "decoded_files": decoded["count"],
        "qmdict_heavy_lookups": lookups["count"],
        "wall_ms": round((time.perf_counter() - wall_started) * 1000, 3),
        "cpu_ms": round((time.process_time() - cpu_started) * 1000, 3),
        "postgres_sql_round_trips": int(pg_after.get("sql_round_trips", 0) or 0) - int(pg_before.get("sql_round_trips", 0) or 0),
        "postgres_pool_wait_count": int(pg_after.get("pool_wait_count", 0) or 0) - int(pg_before.get("pool_wait_count", 0) or 0),
        "index_path": str(app.VOCAB_FILE_META_INDEX_PATH),
        "index_bytes": app.VOCAB_FILE_META_INDEX_PATH.stat().st_size if app.VOCAB_FILE_META_INDEX_PATH.is_file() else 0,
        "pid": os.getpid(),
    }
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2)
    if args.evidence:
        output = Path(args.evidence)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=True, separators=(",", ":")))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
