"""Build and verify the authoritative compressed Structure SQLite database."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path


def io_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    raw = str(path.resolve())
    return Path(raw if raw.startswith("\\\\?\\") else "\\\\?\\" + raw)


def configure(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA cache_size=-65536")
    connection.execute("PRAGMA temp_store=MEMORY")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    database = args.database.resolve()
    building = Path(str(database) + ".building")
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(building) + suffix)
        if candidate.exists():
            candidate.unlink()

    connection = sqlite3.connect(building, timeout=30.0)
    connection.execute("PRAGMA page_size=32768")
    configure(connection)
    connection.execute("CREATE TABLE database_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID")
    connection.execute(
        "CREATE TABLE assets (path_key TEXT PRIMARY KEY, path TEXT NOT NULL, content_gzip BLOB NOT NULL, "
        "raw_size INTEGER NOT NULL, raw_sha256 TEXT NOT NULL, source_mtime_ns INTEGER NOT NULL, "
        "revision_ns INTEGER NOT NULL) WITHOUT ROWID"
    )
    count = raw_total = stored_total = 0
    started = time.perf_counter()
    with connection:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            raw = io_path(path).read_bytes()
            payload = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise RuntimeError(f"Structure payload is not an object: {relative}")
            compressed = gzip.compress(raw, compresslevel=6, mtime=0)
            stat = io_path(path).stat()
            digest = hashlib.sha256(raw).hexdigest()
            connection.execute(
                "INSERT INTO assets(path_key,path,content_gzip,raw_size,raw_sha256,source_mtime_ns,revision_ns) "
                "VALUES(?,?,?,?,?,?,?)",
                (relative.lower(), relative, compressed, len(raw), digest, stat.st_mtime_ns, stat.st_mtime_ns),
            )
            count += 1
            raw_total += len(raw)
            stored_total += len(compressed)
        meta = {
            "schema_version": "1",
            "migration_complete": "1",
            "asset_count": str(count),
            "raw_bytes": str(raw_total),
            "created_at_epoch": str(time.time()),
        }
        connection.executemany("INSERT INTO database_meta(key,value) VALUES(?,?)", meta.items())
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    db_count, db_raw = connection.execute("SELECT COUNT(*),COALESCE(SUM(raw_size),0) FROM assets").fetchone()
    connection.close()
    if check != "ok" or int(db_count) != count or int(db_raw) != raw_total:
        raise RuntimeError(f"Structure database verification failed: check={check} count={db_count} raw={db_raw}")
    if database.exists():
        raise RuntimeError(f"Refusing to replace existing Structure database: {database}")
    os.replace(building, database)
    print(
        f"assets={count} raw_bytes={raw_total} gzip_bytes={stored_total} database_bytes={database.stat().st_size} "
        f"quick_check={check} seconds={time.perf_counter() - started:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
