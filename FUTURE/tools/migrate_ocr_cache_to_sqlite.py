"""Migrate the OCR text cache into indexed rows in structure_assets.db."""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    files = sorted(path for path in args.source.rglob("*.txt") if path.is_file())
    connection = sqlite3.connect(args.database, timeout=30.0)
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    started = time.perf_counter()
    revision_ns = time.time_ns()
    with connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS ocr_pages (folder_key TEXT NOT NULL,folder_path TEXT NOT NULL,"
            "file_key TEXT NOT NULL,file_name TEXT NOT NULL,content_text TEXT NOT NULL,"
            "source_mtime_ns INTEGER NOT NULL,source_size INTEGER NOT NULL,PRIMARY KEY(folder_key,file_key)) WITHOUT ROWID"
        )
        connection.execute("DELETE FROM ocr_pages")
        for path in files:
            relative = path.relative_to(args.source)
            folder_path = relative.parent.as_posix()
            stat = path.stat()
            connection.execute(
                "INSERT INTO ocr_pages(folder_key,folder_path,file_key,file_name,content_text,source_mtime_ns,source_size) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    folder_path.lower(),
                    folder_path,
                    path.name.lower(),
                    path.name,
                    path.read_text(encoding="utf-8-sig", errors="replace"),
                    stat.st_mtime_ns,
                    stat.st_size,
                ),
            )
        connection.execute(
            "INSERT INTO database_meta(key,value) VALUES('ocr_revision_ns',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(revision_ns),),
        )
        connection.execute(
            "INSERT INTO database_meta(key,value) VALUES('ocr_migration_complete','1') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
    check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    count = int(connection.execute("SELECT COUNT(*) FROM ocr_pages").fetchone()[0])
    connection.close()
    if check != "ok" or count != len(files):
        raise RuntimeError(f"OCR SQLite verification failed: check={check} count={count}/{len(files)}")
    print(f"pages={count} quick_check={check} seconds={time.perf_counter()-started:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
