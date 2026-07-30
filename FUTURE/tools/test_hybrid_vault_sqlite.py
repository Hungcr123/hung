"""Regression for SQLite-only Lesson Vault placement operations."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from FUTURE import server_app as app


LIVE_ROOT = Path(r"C:\server data")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="future-vault-") as temp_name:
        root = Path(temp_name) / "server data"
        root.mkdir(parents=True)
        copied_db = root / "server2.db"
        source_db = sqlite3.connect(str(LIVE_ROOT / "server2.db"))
        target_db = sqlite3.connect(str(copied_db))
        source_db.backup(target_db)
        source_db.close()
        target_db.close()

        probe = sqlite3.connect(str(copied_db))
        row = probe.execute(
            "SELECT r.normalized_path,r.file_id FROM lesson_file_replicas r "
            "WHERE r.status='active' AND lower(r.normalized_path) LIKE 'common/%' "
            "ORDER BY r.file_size ASC LIMIT 1"
        ).fetchone()
        assert row, "production copy has no common lesson replica"
        source_rel, lesson_id = str(row[0]), str(row[1])
        now = "2026-07-23T00:00:00Z"
        probe.execute(
            "INSERT OR IGNORE INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES('codexvault001',0,1,'{}',?)",
            (now,),
        )
        probe.execute(
            "INSERT OR IGNORE INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES('codexvault002',0,1,'{}',?)",
            (now,),
        )
        probe.commit()
        progress_before = probe.execute("SELECT COUNT(*),COALESCE(SUM(server_revision),0) FROM lesson_progress").fetchone()
        probe.close()

        source_live = LIVE_ROOT.joinpath(*source_rel.split("/"))
        assert source_live.is_file(), source_live
        source_stage = root.joinpath(*source_rel.split("/"))
        source_stage.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_live, source_stage)
        (root / "codexvault001" / "Moved").mkdir(parents=True)
        (root / "codexvault002").mkdir(parents=True)
        (root / "hung").mkdir(parents=True)
        (root / "quynh" / "Empower A1 - link 2").mkdir(parents=True, exist_ok=True)
        huge_source = root / "common" / "HugeReference"
        huge_source.mkdir(parents=True, exist_ok=True)
        with (huge_source / "logical-10gb.bin").open("wb") as handle:
            handle.seek(10 * 1024 * 1024 * 1024 - 1)
            handle.write(b"\0")
        source_hash = sha256(source_stage)

        app.SERVER_DATA_ROOT = root
        app.SERVER_DATABASE_FILE = copied_db
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.server_database_submit_write = direct_submit
        app.clear_lesson_metadata_cache()
        first = app.initialize_server_database()
        assert first["ok"]
        admin_vault = app.server_database_vault_operation(
            {"action": "copy_link", "source": source_rel, "destination": "hung", "target_user": "hung"},
            "hung",
        )
        user_vault = app.server_database_vault_operation(
            {"action": "copy_link", "source": source_rel, "destination": "codexvault002", "target_user": "codexvault002"},
            "hung",
        )
        assert admin_vault["lesson_id"] == lesson_id == user_vault["lesson_id"]
        assert not root.joinpath(*admin_vault["path"].split("/")).exists()
        assert not root.joinpath(*user_vault["path"].split("/")).exists()
        admin_task = app.add_lesson_task("hung", source_rel, "hung", creator_role="admin")
        user_task = app.add_lesson_task("codexvault002", source_rel, "hung", creator_role="admin")
        assert admin_task["task"]["lesson_id"] == lesson_id == user_task["task"]["lesson_id"], (
            admin_task["task"].get("lesson_id"), lesson_id, user_task["task"].get("lesson_id")
        )
        tree_revision_before = app.server_data_tree_runtime_revision("codexvault001", False)
        try:
            app.server_database_vault_operation(
                {"action": "move", "source": source_rel, "destination": "codexvault001"},
                "codexvault001",
            )
            raise AssertionError("common move unexpectedly succeeded")
        except RuntimeError as exc:
            assert str(exc) == "COMMON_LIBRARY_READ_ONLY"

        migrated_quynh = app.server_database_vault_match("quynh/Empower A1 - link 2")
        if migrated_quynh:
            migrated_id = migrated_quynh["vault_folder_id"]
            quynh_children = app.server_database_vault_children(app._server_database_vault_root_id("quynh"), "quynh")
            assert any(item.get("vault_folder_id") == migrated_id for item in quynh_children), quynh_children
            quynh_root = app.list_server_data("quynh", "quynh", lightweight=True)
            quynh_cards = [item for item in quynh_root["entries"] if item.get("path") == "quynh/Empower A1 - link 2"]
            assert len(quynh_cards) == 1 and quynh_cards[0].get("virtual"), quynh_root["entries"]
            renamed_folder = app.server_database_vault_operation(
                {"action": "rename", "source": "quynh/Empower A1 - link 2", "name": "Empower reorganized"},
                "quynh",
            )
            assert renamed_folder["vault_folder_id"] == migrated_id
            assert not app.server_database_vault_match("quynh/Empower A1 - link 2")
            assert app.server_database_vault_match("quynh/Empower reorganized")["vault_folder_id"] == migrated_id
            renamed_listing = app.list_server_data("quynh/Empower reorganized", "quynh", lightweight=True)
            assert renamed_listing["entries"]
            materialized_check = app.server_database_connect()
            materialized_count = materialized_check.execute(
                "WITH RECURSIVE subtree(id) AS (SELECT ? UNION ALL SELECT f.vault_folder_id FROM vault_folders f JOIN subtree s ON f.parent_folder_id=s.id WHERE f.status='active') "
                "SELECT COUNT(*) FROM vault_entries WHERE status='active' AND parent_folder_id IN (SELECT id FROM subtree)",
                (migrated_id,),
            ).fetchone()[0]
            materialized_check.close()
            assert materialized_count > 0

        virtual_folder = app.server_database_vault_operation(
            {"action": "create_folder", "destination": "codexvault001", "name": "SQLite only"},
            "codexvault001",
        )
        assert virtual_folder["type"] == "folder"
        assert not root.joinpath(*virtual_folder["path"].split("/")).exists()

        copied = app.server_database_vault_operation(
            {"action": "copy_link", "source": source_rel, "destination": "codexvault001"},
            "codexvault001",
        )
        assert copied["lesson_id"] == lesson_id
        assert not root.joinpath(*copied["path"].split("/")).exists()
        entry_id = copied["vault_entry_id"]

        reorganized_rel = clean_rel = "common/Reorganized/" + source_stage.name
        reorganized_source = root.joinpath(*reorganized_rel.split("/"))
        reorganized_source.parent.mkdir(parents=True, exist_ok=True)
        source_stage.replace(reorganized_source)
        moved_entry = {
            "type": "file",
            "lesson_id": lesson_id,
            "path": reorganized_rel,
            "content_fingerprint": "",
            "modified_ns": reorganized_source.stat().st_mtime_ns,
            "size": reorganized_source.stat().st_size,
        }
        moved_registry = app.sync_server_data_lesson_identity_paths(
            {"folders": {"common/Reorganized": [moved_entry]}},
            {source_rel, reorganized_rel},
        )
        assert moved_registry["collisions"] == 0
        assert app.read_server_data_file(copied["path"], "codexvault001", admin=False) == reorganized_source.read_bytes()
        source_stage = reorganized_source

        # Simulate an admin copying the same self-identifying lesson into the
        # exact virtual destination.  Watcher registration must rebind, not add
        # a second Vault placement or a new lesson ID.
        materialized = root.joinpath(*copied["path"].split("/"))
        materialized.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_stage, materialized)
        materialized_entry = {
            "type": "file",
            "lesson_id": lesson_id,
            "path": copied["path"],
            "content_fingerprint": "",
            "modified_ns": materialized.stat().st_mtime_ns,
            "size": materialized.stat().st_size,
        }
        registry = app.sync_server_data_lesson_identity_paths(
            {"folders": {"codexvault001": [materialized_entry]}},
            {copied["path"]},
        )
        assert registry["registered"] == 1
        rebound = app.server_database_vault_entry_for_path(copied["path"])
        assert rebound["vault_entry_id"] == entry_id
        assert rebound["entry_type"] == "PHYSICAL_REPLICA"
        rebound_listing = app.list_server_data("codexvault001", "codexvault001", lightweight=True)
        rebound_cards = [item for item in rebound_listing["entries"] if item.get("path") == copied["path"]]
        assert len(rebound_cards) == 1
        assert rebound_cards[0].get("vault_entry_id") == entry_id
        duplicate = app.server_database_vault_operation(
            {"action": "copy_link", "source": copied["path"], "destination": "codexvault001/Moved"},
            "codexvault001",
        )
        assert duplicate["vault_entry_id"] != entry_id and duplicate["lesson_id"] == lesson_id
        tree_snapshot = app.build_server_data_tree_snapshot("codexvault001", False)
        columns = {name: index for index, name in enumerate(tree_snapshot["entry_columns"])}
        def compact_value(values, name):
            index = columns[name]
            return values[index] if index < len(values) else ""
        root_row = next(row for row in tree_snapshot["rows"] if row.get("path") == "codexvault001")
        assert any(compact_value(values, "path") == virtual_folder["path"] for values in root_row["entries"])
        moved_row = next(row for row in tree_snapshot["rows"] if row.get("path") == "codexvault001/Moved")
        assert any(compact_value(values, "vault_entry_id") == duplicate["vault_entry_id"] for values in moved_row["entries"])
        assert app.server_data_tree_runtime_revision("codexvault001", False) != tree_revision_before
        duplicate_connection = app.server_database_connect()
        assert duplicate_connection.execute(
            "SELECT COUNT(*) FROM vault_entries WHERE username='codexvault001' AND lesson_id=? AND status='active'",
            (lesson_id,),
        ).fetchone()[0] == 2
        duplicate_connection.close()
        app.server_database_vault_operation(
            {"action": "delete_link", "source": duplicate["path"]},
            "codexvault001",
        )

        moved = app.server_database_vault_operation(
            {"action": "move", "source": copied["path"], "destination": "codexvault001/Moved"},
            "codexvault001",
        )
        renamed = app.server_database_vault_operation(
            {"action": "rename", "source": moved["path"], "name": "Renamed lesson" + source_stage.suffix},
            "codexvault001",
        )
        assert app.server_database_vault_entry_for_path(renamed["path"])["vault_entry_id"] == entry_id
        assert app.read_server_data_file(renamed["path"], "codexvault001", admin=False) == source_stage.read_bytes()
        listed = app.list_server_data("codexvault001/Moved", "codexvault001", lightweight=True)
        listed_entry = next(item for item in listed["entries"] if item.get("vault_entry_id") == entry_id)
        assert listed_entry["lesson_id"] == lesson_id
        app.server_database_vault_operation(
            {"action": "delete_link", "source": renamed["path"]},
            "codexvault001",
        )

        folder_source = reorganized_rel.rsplit("/", 1)[0]
        folder_copy = app.server_database_vault_operation(
            {"action": "copy_link", "source": folder_source, "destination": "codexvault001"},
            "codexvault001",
        )
        assert folder_copy["type"] == "folder"
        assert not root.joinpath(*folder_copy["path"].split("/")).exists()
        assert sha256(source_stage) == source_hash
        cloned_folder = app.server_database_vault_operation(
            {"action": "copy_link", "source": folder_copy["path"], "destination": "codexvault001"},
            "codexvault001",
        )
        assert cloned_folder["vault_folder_id"] != folder_copy["vault_folder_id"]
        clone_check = app.server_database_connect()
        cloned_entry_count = clone_check.execute(
            "WITH RECURSIVE subtree(id) AS (SELECT ? UNION ALL SELECT f.vault_folder_id FROM vault_folders f JOIN subtree s ON f.parent_folder_id=s.id WHERE f.status='active') "
            "SELECT COUNT(*) FROM vault_entries WHERE status='active' AND parent_folder_id IN (SELECT id FROM subtree)",
            (cloned_folder["vault_folder_id"],),
        ).fetchone()[0]
        clone_check.close()
        assert cloned_entry_count == 1
        reordered = app.server_database_vault_operation(
            {"action": "move_up", "source": cloned_folder["path"]},
            "codexvault001",
        )
        assert reordered["vault_folder_id"] == cloned_folder["vault_folder_id"]
        ordered_root_folders = [
            item["vault_folder_id"]
            for item in app.server_database_vault_children(app._server_database_vault_root_id("codexvault001"), "codexvault001")
            if item.get("vault_folder_id")
        ]
        assert ordered_root_folders.index(cloned_folder["vault_folder_id"]) < ordered_root_folders.index(folder_copy["vault_folder_id"])
        cpu_started = time.process_time()
        wall_started = time.perf_counter()
        huge_copy = app.server_database_vault_operation(
            {"action": "copy_link", "source": "common/HugeReference", "destination": "codexvault001"},
            "codexvault001",
        )
        huge_cpu_ms = (time.process_time() - cpu_started) * 1000
        huge_wall_ms = (time.perf_counter() - wall_started) * 1000
        assert not root.joinpath(*huge_copy["path"].split("/")).exists()
        for blocked_payload in (
            {"action": "move", "source": source_rel, "destination": "codexvault001"},
            {"action": "copy_link", "source": source_rel, "destination": "common"},
        ):
            try:
                app.server_database_vault_operation(blocked_payload, "codexvault001")
            except RuntimeError as exc:
                assert str(exc) == "COMMON_LIBRARY_READ_ONLY"
            else:
                raise AssertionError("Common mutation was not rejected")
        try:
            app.server_database_vault_operation(
                {"action": "copy_link", "source": source_rel, "destination": "codexvault002", "target_user": "codexvault002"},
                "codexvault001",
            )
        except RuntimeError as exc:
            assert "Only admins" in str(exc)
        else:
            raise AssertionError("Non-admin cross-user Vault write was not rejected")
        assert app.server_database_vault_folder_rows("codexvault001")

        connection = app.server_database_connect()
        progress_after = connection.execute("SELECT COUNT(*),COALESCE(SUM(server_revision),0) FROM lesson_progress").fetchone()
        vault_counts = {
            "folders": connection.execute("SELECT COUNT(*) FROM vault_folders WHERE username='codexvault001' AND status='active'").fetchone()[0],
            "entries": connection.execute("SELECT COUNT(*) FROM vault_entries WHERE username='codexvault001' AND status='active'").fetchone()[0],
            "revision": connection.execute("SELECT revision FROM vault_revisions WHERE username='codexvault001'").fetchone()[0],
        }
        integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
        connection.close()
        assert tuple(progress_before) == tuple(progress_after)
        assert integrity == "ok"

        killed = subprocess.run([
            sys.executable,
            "-c",
            (
                "import os,sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
                "c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA synchronous=FULL'); "
                "c.execute('BEGIN IMMEDIATE'); "
                "c.execute(\"INSERT INTO vault_folders(vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,created_at_utc,updated_at_utc) VALUES('vault-kill-probe','codexvault001','vault-root-2f94b164cd704d63ee76d9b407a0','partial','VIRTUAL','','x','x')\"); "
                "os._exit(9)"
            ),
            str(copied_db),
        ], check=False)
        assert killed.returncode == 9
        crash_check = sqlite3.connect(str(copied_db))
        assert crash_check.execute("SELECT COUNT(*) FROM vault_folders WHERE vault_folder_id='vault-kill-probe'").fetchone()[0] == 0
        crash_check.close()

        revision_before_restart = vault_counts["revision"]
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.SERVER_DATABASE_VAULT_FOLDER_CACHE.clear()
        app.SERVER_DATABASE_VAULT_ENTRY_CACHE.clear()
        app.SERVER_DATABASE_VAULT_PATH_CACHE.clear()
        second = app.initialize_server_database()
        assert second["ok"]
        assert app.server_database_vault_match(folder_copy["path"])["vault_folder_id"] == folder_copy["vault_folder_id"]
        assert app.server_database_vault_revision("codexvault001") == revision_before_restart

        print(json.dumps({
            "ok": True,
            "source": source_rel,
            "lesson_id": lesson_id,
            "physical_copy_bytes": 0,
            "same_destination_rebound": True,
            "same_lesson_multiple_placements": True,
            "standalone_virtual_folder": True,
            "virtual_folder_clone_kept_lessons": True,
            "virtual_sort_order": True,
            "fresh_tree_preload_contains_virtual_rows": True,
            "physical_restructure_resolved_by_lesson_id": True,
            "physical_source_sha256_unchanged": True,
            "logical_10gb_copy": {"physical_bytes_written": 0, "cpu_ms": round(huge_cpu_ms, 3), "wall_ms": round(huge_wall_ms, 3)},
            "common_read_only": True,
            "cross_user_denied": True,
            "folder_picker_rows": len(app.server_database_vault_folder_rows("codexvault001")),
            "add_to_admin_and_user": True,
            "assign_to_admin_and_user": True,
            "progress_signature_unchanged": True,
            "vault": vault_counts,
            "restart_restored": True,
            "hard_kill_partial_rows": 0,
            "second_migration_actions": second.get("vault_folder_mounts", 0),
            "legacy_folder_rename_kept_id": bool(migrated_quynh),
            "quick_check": integrity,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
