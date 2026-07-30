"""100-user metadata-only folder placement regression on a copied database."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from FUTURE import server_app as app


LIVE_ROOT = Path(r"C:\server data")
USERS = [f"codexvault{i:03d}" for i in range(100)]


def direct_submit(callback, timeout: float = 15.0, source: str = ""):
    del timeout, source
    connection = app.server_database_connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = callback(connection)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="future-vault-100-") as temp_name:
        root = Path(temp_name) / "server data"
        root.mkdir(parents=True)
        database = root / "server2.db"
        source_db = sqlite3.connect(str(LIVE_ROOT / "server2.db"))
        target_db = sqlite3.connect(str(database))
        source_db.backup(target_db)
        row = target_db.execute(
            "SELECT normalized_path,file_id FROM lesson_file_replicas WHERE status='active' AND lower(normalized_path) LIKE 'common/%' ORDER BY file_size ASC LIMIT 1"
        ).fetchone()
        assert row
        source_rel, lesson_id = str(row[0]), str(row[1])
        now = "2026-07-23T00:00:00Z"
        target_db.executemany(
            "INSERT OR IGNORE INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,'{}',?)",
            [(user, now) for user in USERS],
        )
        progress_before = target_db.execute("SELECT COUNT(*),COALESCE(SUM(server_revision),0) FROM lesson_progress").fetchone()
        target_db.commit()
        source_db.close()
        target_db.close()

        source_live = LIVE_ROOT.joinpath(*source_rel.split("/"))
        course = root / "common" / "Logical10GB"
        course.mkdir(parents=True)
        lesson = course / source_live.name
        shutil.copy2(source_live, lesson)
        lesson_hash = sha256(lesson)
        sparse = course / "logical-10gb.bin"
        with sparse.open("wb") as handle:
            handle.seek(10 * 1024 * 1024 * 1024 - 1)
            handle.write(b"\0")
        sparse_before = (sparse.stat().st_size, sparse.stat().st_mtime_ns)

        app.SERVER_DATA_ROOT = root
        app.SERVER_DATABASE_FILE = database
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.server_database_submit_write = direct_submit
        app.initialize_server_database()
        registered = app.server_database_register_lesson_file_entries([{
            "lesson_id": lesson_id,
            "path": f"common/Logical10GB/{lesson.name}",
            "content_fingerprint": "",
            "modified_ns": lesson.stat().st_mtime_ns,
            "size": lesson.stat().st_size,
        }])
        assert registered["registered"] == 1 and registered["collisions"] == 0

        refresh_calls = []
        app.refresh_server_data_manifest_paths_now = lambda *args, **kwargs: refresh_calls.append((args, kwargs))
        original_open = Path.open
        original_iterdir = Path.iterdir
        lesson_reads = []
        source_scans = []
        lesson_resolved = lesson.resolve()
        course_resolved = course.resolve()
        def guarded_open(path, *args, **kwargs):
            if path.resolve() == lesson_resolved:
                lesson_reads.append(str(path))
                raise AssertionError("Vault metadata placement read lesson bytes")
            return original_open(path, *args, **kwargs)
        def guarded_iterdir(path):
            if path.resolve() == course_resolved:
                source_scans.append(str(path))
                raise AssertionError("Vault metadata placement scanned source folder")
            return original_iterdir(path)
        cpu_started = time.process_time()
        wall_started = time.perf_counter()
        Path.open = guarded_open
        Path.iterdir = guarded_iterdir
        try:
            results = [
                app.server_data_operation({
                    "action": "get",
                    "source": "common/Logical10GB",
                    "destination": user,
                }, user)
                for user in USERS
            ]
        finally:
            Path.open = original_open
            Path.iterdir = original_iterdir
        cpu_ms = (time.process_time() - cpu_started) * 1000
        wall_ms = (time.perf_counter() - wall_started) * 1000

        connection = app.server_database_connect()
        progress_after = connection.execute("SELECT COUNT(*),COALESCE(SUM(server_revision),0) FROM lesson_progress").fetchone()
        folder_rows = connection.execute(
            "SELECT COUNT(*) FROM vault_folders WHERE username LIKE 'codexvault%' AND folder_type='VIRTUAL_IMPORT' AND status='active'"
        ).fetchone()[0]
        entry_rows = connection.execute(
            "SELECT COUNT(*) FROM vault_entries WHERE username LIKE 'codexvault%' AND lesson_id=? AND status='active'",
            (lesson_id,),
        ).fetchone()[0]
        revisions = connection.execute(
            "SELECT COUNT(*),MIN(revision),MAX(revision) FROM vault_revisions WHERE username LIKE 'codexvault%'"
        ).fetchone()
        integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
        connection.close()

        physical_user_files = sum(1 for user in USERS for path in (root / user).rglob("*") if path.is_file())
        assert all(item.get("virtual") for item in results)
        assert folder_rows == 100 and entry_rows == 100
        assert tuple(progress_before) == tuple(progress_after)
        assert physical_user_files == 0
        assert not refresh_calls
        assert not lesson_reads and not source_scans
        assert sha256(lesson) == lesson_hash
        assert (sparse.stat().st_size, sparse.stat().st_mtime_ns) == sparse_before
        assert tuple(revisions) == (100, 1, 1)
        assert integrity == "ok"

        print(json.dumps({
            "ok": True,
            "users": 100,
            "logical_source_bytes": sparse_before[0],
            "physical_user_files_created": physical_user_files,
            "watcher_refresh_calls": len(refresh_calls),
            "lesson_byte_reads": len(lesson_reads),
            "source_folder_scans": len(source_scans),
            "vault_folders": folder_rows,
            "vault_entries": entry_rows,
            "progress_signature_unchanged": True,
            "source_lesson_sha256_unchanged": True,
            "source_sparse_metadata_unchanged": True,
            "cpu_total_ms": round(cpu_ms, 3),
            "cpu_per_user_ms": round(cpu_ms / 100, 3),
            "wall_total_ms": round(wall_ms, 3),
            "wall_per_user_ms": round(wall_ms / 100, 3),
            "quick_check": integrity,
        }, indent=2))


if __name__ == "__main__":
    main()
