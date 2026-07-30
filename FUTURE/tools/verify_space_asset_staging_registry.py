"""Verify canonical thin packages against an isolated copy of the production registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.legacy.sqlite_space_pdf_registry import initialize_space_pdf_registry_schema, register_space_pdf_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", type=Path, default=Path(r"C:\server data\server2.db"))
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    staging = args.staging_root.resolve()
    report = json.loads((staging / "thin_asset_staging_report.json").read_text(encoding="utf-8"))
    copied_db = staging.parent / "server2_thin_registry_staging.db"
    copied_db.unlink(missing_ok=True)
    source = sqlite3.connect(f"file:{args.source_db.resolve().as_posix()}?mode=ro", uri=True)
    target = sqlite3.connect(copied_db, isolation_level=None)
    source.backup(target)
    source.close()
    initialize_space_pdf_registry_schema(target)

    first_status = []
    replay_status = []
    for row in report["rows"]:
        relative = str(row["package"]).replace("\\", "/")
        package = staging / "lessons" / Path(*relative.split("/"))
        operation_id = "thin-v2-staging:" + hashlib.sha256(str(row["lesson_id"]).encode("utf-8")).hexdigest()
        first_status.append(register_space_pdf_package(
            target,
            package,
            relative,
            operation_id=operation_id,
            legacy_path=str(Path(relative).with_suffix("")),
            actor_username="admin",
            actor_is_admin=True,
        ))
        replay_status.append(register_space_pdf_package(
            target,
            package,
            relative,
            operation_id=operation_id,
            legacy_path=str(Path(relative).with_suffix("")),
            actor_username="admin",
            actor_is_admin=True,
        ))
    result = {
        "registered": len(first_status),
        "active": sum(row.get("status") == "active" for row in first_status),
        "collisions": sum(row.get("status") == "collision" for row in first_status),
        "replay_idempotent": sum(bool(row.get("idempotent")) for row in replay_status),
        "schema_v2_meta": target.execute("SELECT COUNT(*) FROM space_pdf_lesson_meta WHERE schema_version=2 AND status='active'").fetchone()[0],
        "asset_meta": target.execute("SELECT COUNT(*) FROM space_pdf_lesson_meta WHERE asset_id<>'' AND asset_locator<>'' AND status='active'").fetchone()[0],
        "active_documents": target.execute("SELECT COUNT(*) FROM space_pdf_documents WHERE status='active'").fetchone()[0],
        "asset_documents": target.execute("SELECT COUNT(*) FROM space_pdf_documents WHERE asset_id<>'' AND asset_locator<>'' AND status='active'").fetchone()[0],
        "foreign_key_errors": len(target.execute("PRAGMA foreign_key_check").fetchall()),
        "quick_check": target.execute("PRAGMA quick_check").fetchone()[0],
    }
    target.close()
    (staging.parent / "thin_registry_staging_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    if result["registered"] != 130 or result["active"] != 130 or result["collisions"] or result["replay_idempotent"] != 130:
        return 1
    if result["schema_v2_meta"] != 130 or result["asset_meta"] != 130 or result["foreign_key_errors"] or result["quick_check"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

