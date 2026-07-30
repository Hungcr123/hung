"""Verify the pre-migration Structure backup and write a portable hash manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path


def io_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    raw = str(path.resolve())
    return Path(raw if raw.startswith("\\\\?\\") else "\\\\?\\" + raw)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with io_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    backup = args.backup.resolve()
    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        relative = path.relative_to(source)
        copied = backup / relative
        source_stat = io_path(path).stat()
        source_hash = sha256(path)
        copied_io = io_path(copied)
        copied_exists = copied_io.is_file()
        copied_size = copied_io.stat().st_size if copied_exists else -1
        copied_hash = sha256(copied) if copied_exists else ""
        verified = source_stat.st_size == copied_size and source_hash == copied_hash
        if not verified:
            failures.append(relative.as_posix())
        rows.append(
            {
                "relative_path": relative.as_posix(),
                "size": source_stat.st_size,
                "mtime_ns": source_stat.st_mtime_ns,
                "sha256": source_hash,
                "backup_size": copied_size,
                "backup_sha256": copied_hash,
                "verified": int(verified),
            }
        )

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["relative_path"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"files={len(rows)} bytes={sum(int(row['size']) for row in rows)} failures={len(failures)}")
    if failures:
        print("mismatches=" + ",".join(failures[:20]))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
