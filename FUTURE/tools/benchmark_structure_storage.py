"""Benchmark current Structure files against an indexed SQLite BLOB store."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import os
import random
import sqlite3
import statistics
import time
from pathlib import Path


def io_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    raw = str(path.resolve())
    return Path(raw if raw.startswith("\\\\?\\") else "\\\\?\\" + raw)


def read_file(path: Path) -> bytes:
    return io_path(path).read_bytes()


def configure(connection: sqlite3.Connection, *, writer: bool = False) -> None:
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA mmap_size=1073741824")
    connection.execute("PRAGMA cache_size=-65536")
    connection.execute("PRAGMA temp_store=MEMORY")
    if writer:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")


def build_database(source: Path, database: Path, use_gzip: bool = False) -> tuple[int, int, float]:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(database) + suffix)
        if candidate.exists():
            candidate.unlink()
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA page_size=32768")
    configure(connection, writer=True)
    connection.execute(
        "CREATE TABLE assets (path TEXT PRIMARY KEY, content BLOB NOT NULL, size INTEGER NOT NULL, "
        "mtime_ns INTEGER NOT NULL, sha256 TEXT NOT NULL) WITHOUT ROWID"
    )
    started = time.perf_counter()
    count = total = 0
    with connection:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            content = read_file(path)
            relative = path.relative_to(source).as_posix()
            stat = io_path(path).stat()
            stored = gzip.compress(content, compresslevel=6, mtime=0) if use_gzip else content
            connection.execute(
                "INSERT INTO assets(path,content,size,mtime_ns,sha256) VALUES(?,?,?,?,?)",
                (relative, stored, len(content), stat.st_mtime_ns, hashlib.sha256(content).hexdigest()),
            )
            count += 1
            total += len(content)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.execute("PRAGMA optimize")
    connection.close()
    return count, total, time.perf_counter() - started


class SQLiteReader:
    def __init__(self, database: Path) -> None:
        self.database = database
        self.local = __import__("threading").local()

    def __call__(self, key: str) -> bytes:
        connection = getattr(self.local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True)
            configure(connection)
            self.local.connection = connection
        row = connection.execute("SELECT content FROM assets WHERE path=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return bytes(row[0])


def measure(label: str, requests: list[str], read) -> tuple[str, float, float, int]:
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    byte_count = sum(len(read(key)) for key in requests)
    return label, time.perf_counter() - wall_start, time.process_time() - cpu_start, byte_count


def measure_parallel(label: str, requests: list[str], read, workers: int) -> tuple[str, float, float, int]:
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(read, requests))
    return label, time.perf_counter() - wall_start, time.process_time() - cpu_start, sum(map(len, results))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--requests", type=int, default=800)
    parser.add_argument("--gzip", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    database = args.database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)

    count, total, build_seconds = build_database(source, database, use_gzip=args.gzip)
    keys = [path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()]
    rng = random.Random(20260720)
    requests = [rng.choice(keys) for _ in range(args.requests)]
    file_read = lambda key: read_file(source / Path(key))
    db_read = SQLiteReader(database)
    db_decoded_read = lambda key: gzip.decompress(db_read(key)) if args.gzip else db_read(key)

    measurements = [
        measure("filesystem-1", requests, file_read),
        measure("filesystem-2", requests, file_read),
        measure("sqlite-raw-1", requests, db_read),
        measure("sqlite-raw-2", requests, db_read),
        measure("sqlite-decoded", requests, db_decoded_read),
        measure_parallel("filesystem-16", requests, file_read, 16),
        measure_parallel("sqlite-raw-16", requests, db_read, 16),
        measure_parallel("sqlite-decoded-16", requests, db_decoded_read, 16),
    ]
    sizes = [io_path(source / Path(key)).stat().st_size for key in requests]
    print(
        f"assets={count} source_bytes={total} database_bytes={database.stat().st_size} "
        f"build_seconds={build_seconds:.3f} sampled_median_bytes={statistics.median(sizes):.0f}"
    )
    for label, wall, cpu, byte_count in measurements:
        print(
            f"{label} requests={len(requests)} bytes={byte_count} wall_ms={wall * 1000:.3f} "
            f"cpu_ms={cpu * 1000:.3f} per_request_wall_ms={wall * 1000 / len(requests):.4f} "
            f"per_request_cpu_ms={cpu * 1000 / len(requests):.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
