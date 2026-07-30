"""Regression for canonical root-only folder-link rows in SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def marker_payload(target: str) -> dict:
    return {
        "kind": "future_server_data_link",
        "version": 1,
        "target": target,
        "target_type": "folder",
        "created_by": "codexlink",
        "created_at": "2026-07-21T10:00:00Z",
    }


# Added 2026-07-21: migration keeps logical roots only and serves parsed payloads from RAM.
def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-folder-link-db-") as temporary:
        root = Path(temporary) / "server data"
        root.mkdir(parents=True)
        database = root / "server2.db"
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE documents (
                path_key TEXT PRIMARY KEY,path TEXT NOT NULL,content BLOB NOT NULL,encoding TEXT NOT NULL,
                sha256 TEXT NOT NULL,file_size INTEGER NOT NULL,file_mtime_ns INTEGER NOT NULL,updated_at_utc TEXT NOT NULL
            );
            CREATE TABLE lesson_folder_links (
                link_path TEXT PRIMARY KEY COLLATE NOCASE,target_path TEXT NOT NULL,created_by TEXT NOT NULL DEFAULT '',
                created_at_utc TEXT NOT NULL DEFAULT '',payload_json TEXT NOT NULL DEFAULT '{}',revision INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',updated_at_utc TEXT NOT NULL
            );
            """
        )
        rows = [
            ("learner/Linked", marker_payload("common/Study")),
            ("learner/Linked/Unit 01", marker_payload("common/Study/Unit 01")),
        ]
        for relative, payload in rows:
            marker = root.joinpath(*relative.split("/")) / "._future_folder_link.json"
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            connection.execute(
                "INSERT INTO documents(path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc) VALUES(?,?,?,?,?,?,?,?)",
                (str(marker).lower(), str(marker), data, "utf-8", hashlib.sha256(data).hexdigest(), len(data), 1, "2026-07-21T10:00:00Z"),
            )
        original_root = app.SERVER_DATA_ROOT
        try:
            app.SERVER_DATA_ROOT = root
            migrated = app.server_database_migrate_folder_link_documents(connection)
            assert migrated == 1
            stored = list(connection.execute("SELECT link_path,target_path,revision FROM lesson_folder_links"))
            assert [tuple(row) for row in stored] == [("learner/Linked", "common/Study", 1)]
            assert app.server_database_load_folder_link_cache(connection) == 1
            cached = app.server_database_folder_link_payload(root / "learner" / "Linked")
            assert cached["target"] == "common/Study"
            assert cached["revision"] == 1
            assert app.server_database_folder_link_payload(root / "learner" / "Linked" / "Unit 01") == {}
            matched = app.server_database_folder_link_match(root / "learner" / "Linked" / "Unit 01" / "A.Space_V")
            assert matched["link_path"] == "learner/linked"
            assert matched["suffix"] == "Unit 01/A.Space_V"

            changed = marker_payload("common/Study Renamed")
            app._server_database_upsert_folder_link_row(connection, "learner/Linked", changed, "2026-07-21T10:01:00Z")
            row = connection.execute("SELECT target_path,revision FROM lesson_folder_links").fetchone()
            assert tuple(row) == ("common/Study Renamed", 2)
        finally:
            app.SERVER_DATA_ROOT = original_root
            with app.SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK:
                app.SERVER_DATABASE_FOLDER_LINK_CACHE.clear()
            connection.close()

    print("folder_link_sqlite_registry=ok roots=1 propagated=ignored revision=2 ram_cache=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
