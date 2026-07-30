"""Verify every compressed Structure SQLite row against its metadata and optional source."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import sqlite3
from pathlib import Path


def io_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    raw = str(path.resolve())
    return Path(raw if raw.startswith("\\\\?\\") else "\\\\?\\" + raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--ocr-source", type=Path)
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    rows = connection.execute("SELECT path,content_gzip,raw_size,raw_sha256 FROM assets ORDER BY path_key")
    count = total = failures = 0
    for relative, content_gzip, raw_size, raw_sha256 in rows:
        raw = gzip.decompress(bytes(content_gzip))
        digest = hashlib.sha256(raw).hexdigest()
        valid = len(raw) == int(raw_size) and digest == str(raw_sha256)
        if args.source:
            source_path = io_path(args.source / Path(str(relative)))
            valid = valid and source_path.is_file() and source_path.read_bytes() == raw
        count += 1
        total += len(raw)
        failures += int(not valid)
    ocr_count = 0
    if args.ocr_source:
        for folder_path, file_name, content_text in connection.execute(
            "SELECT folder_path,file_name,content_text FROM ocr_pages ORDER BY folder_key,file_key"
        ):
            source_path = args.ocr_source / Path(str(folder_path)) / str(file_name)
            valid = source_path.is_file() and source_path.read_text(encoding="utf-8-sig", errors="replace") == str(content_text)
            failures += int(not valid)
            ocr_count += 1
    connection.close()
    print(f"quick_check={check} assets={count} raw_bytes={total} ocr_pages={ocr_count} failures={failures}")
    return 0 if check == "ok" and failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
