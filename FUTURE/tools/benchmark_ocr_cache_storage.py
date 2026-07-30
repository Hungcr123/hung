"""Benchmark the many-small-file OCR cache against indexed SQLite reads."""

from __future__ import annotations

import argparse
import random
import sqlite3
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    files = [path for path in args.source.rglob("*.txt") if path.is_file()]
    if args.database.exists():
        args.database.unlink()
    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("CREATE TABLE pages(path TEXT PRIMARY KEY,content TEXT NOT NULL) WITHOUT ROWID")
    with connection:
        connection.executemany(
            "INSERT INTO pages(path,content) VALUES(?,?)",
            ((path.relative_to(args.source).as_posix().lower(), path.read_text(encoding="utf-8-sig", errors="replace")) for path in files),
        )
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    rng = random.Random(20260720)
    sample = [rng.choice(files) for _ in range(2000)]
    keys = [path.relative_to(args.source).as_posix().lower() for path in sample]
    start = time.perf_counter()
    cpu = time.process_time()
    file_bytes = sum(len(path.read_text(encoding="utf-8-sig", errors="replace")) for path in sample)
    file_wall, file_cpu = time.perf_counter() - start, time.process_time() - cpu
    start = time.perf_counter()
    cpu = time.process_time()
    db_bytes = sum(len(connection.execute("SELECT content FROM pages WHERE path=?", (key,)).fetchone()[0]) for key in keys)
    db_wall, db_cpu = time.perf_counter() - start, time.process_time() - cpu
    connection.close()
    print(
        f"files={len(files)} file_bytes={file_bytes} db_bytes={db_bytes} db_size={args.database.stat().st_size} "
        f"file_wall_ms={file_wall*1000:.3f} file_cpu_ms={file_cpu*1000:.3f} "
        f"db_wall_ms={db_wall*1000:.3f} db_cpu_ms={db_cpu*1000:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
