"""Atomically install verified canonical assets/thin packages and reconcile the live registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import validate_space_pdf_package
from future_space_picture_package import validate_space_picture_package
from future_space_pdf_registry import initialize_space_pdf_registry_schema, register_space_pdf_package


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_copy(source: Path, target: Path, expected_hash: str) -> bool:
    if target.is_file() and target.stat().st_size == source.stat().st_size and _sha256(target) == expected_hash:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".deploy-{uuid.uuid4().hex}.tmp"
    try:
        with source.open("rb") as source_handle, temporary.open("wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle, length=4 * 1024 * 1024)
            target_handle.flush()
            os.fsync(target_handle.fileno())
        if _sha256(temporary) != expected_hash:
            raise RuntimeError(f"Deployment copy hash mismatch: {target}")
        os.replace(temporary, target)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, default=Path(r"C:\server data"))
    parser.add_argument("--database", type=Path, default=Path(r"C:\server data\server2.db"))
    parser.add_argument("--filesystem-only", action="store_true")
    args = parser.parse_args()
    staging = args.staging_root.resolve()
    live = args.live_root.resolve()
    report = json.loads((staging / "thin_asset_staging_report.json").read_text(encoding="utf-8"))

    created = 0
    changed = 0
    skipped = 0
    for source in sorted(path for path in (staging / "_assets").rglob("*") if path.is_file() and ".incoming" not in path.parts):
        relative = source.relative_to(staging)
        target = live / relative
        existed = target.exists()
        copied = _atomic_copy(source, target, _sha256(source))
        created += int(copied and not existed)
        changed += int(copied and existed)
        skipped += int(not copied)

    package_replaced = 0
    package_rows = []
    for row in report["rows"]:
        relative_text = str(row["package"]).replace("\\", "/")
        relative = Path(*PurePosixPath(relative_text).parts)
        staged_package = staging / "lessons" / relative
        target_package = live / relative
        validator = validate_space_picture_package if staged_package.suffix.lower() == ".space_picture" else validate_space_pdf_package
        staged_manifest = validator(staged_package, verify_source=True, server_data_root=staging)
        if target_package.is_file():
            current_manifest = validator(target_package, verify_source=True, server_data_root=live)
            if current_manifest["lesson_id"] != staged_manifest["lesson_id"] or current_manifest["source_sha256"] != staged_manifest["source_sha256"]:
                raise RuntimeError(f"Live package identity differs from staging: {relative_text}")
        existed = target_package.exists()
        copied = _atomic_copy(staged_package, target_package, _sha256(staged_package))
        package_replaced += int(copied)
        created += int(copied and not existed)
        changed += int(copied and existed)
        skipped += int(not copied)
        validator(target_package, verify_source=True, server_data_root=live)
        package_rows.append((relative_text, target_package, staged_manifest))

    if args.filesystem_only:
        result = {
            "created": created,
            "changed": changed,
            "skipped": skipped,
            "hash_mismatch": 0,
            "assets": len([path for path in (live / "_assets").rglob("*") if path.is_file() and ".incoming" not in path.parts]),
            "packages": len(package_rows),
        }
        print(json.dumps(result, sort_keys=True))
        return 0

    connection = sqlite3.connect(args.database.resolve(), isolation_level=None, timeout=30)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        initialize_space_pdf_registry_schema(connection)
        registered = 0
        idempotent = 0
        collisions = 0
        for relative_text, package, manifest in package_rows:
            legacy_relative = str(PurePosixPath(relative_text).parent / str(manifest.get("source_filename") or ""))
            journal_row = connection.execute(
                "SELECT operation_id FROM space_pdf_migration_journal WHERE legacy_path=? COLLATE NOCASE",
                (legacy_relative,),
            ).fetchone()
            operation_id = str(journal_row[0]) if journal_row is not None else "thin-v2-production:" + hashlib.sha256(str(manifest["lesson_id"]).encode("utf-8")).hexdigest()
            result = register_space_pdf_package(
                connection,
                package,
                relative_text,
                operation_id=operation_id,
                legacy_path=legacy_relative,
                actor_username="admin",
                actor_is_admin=True,
            )
            registered += int(result.get("status") == "active")
            idempotent += int(bool(result.get("idempotent")))
            collisions += int(result.get("status") == "collision")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        connection.execute("PRAGMA wal_checkpoint(FULL)")
    finally:
        connection.close()
    result = {
        "created": created,
        "changed": changed,
        "skipped": skipped,
        "package_replaced": package_replaced,
        "registered_active": registered,
        "registered_idempotent": idempotent,
        "collisions": collisions,
        "quick_check": quick_check,
        "foreign_key_errors": foreign_key_errors,
    }
    print(json.dumps(result, sort_keys=True))
    if registered != 130 or collisions or quick_check != "ok" or foreign_key_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
