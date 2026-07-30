"""Verify archived legacy progress remains readable and reattaches without reviving stale runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def progress_key(username: str, file_id: str) -> str:
    return hashlib.sha256(f"{username.lower()}|identity:{file_id}".encode("utf-8")).hexdigest()[:32]


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE database_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at_utc TEXT NOT NULL);
        CREATE TABLE lesson_progress_namespaces(
            username TEXT NOT NULL COLLATE NOCASE,space TEXT NOT NULL,updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username,space)
        );
        CREATE TABLE lesson_progress(
            username TEXT NOT NULL COLLATE NOCASE,space TEXT NOT NULL,progress_key TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '',identity TEXT NOT NULL DEFAULT '',file_id TEXT NOT NULL DEFAULT '',
            node_index INTEGER NOT NULL DEFAULT 0,node_count INTEGER NOT NULL DEFAULT 0,
            learned_count INTEGER NOT NULL DEFAULT 0,complete INTEGER NOT NULL DEFAULT 0,
            server_revision INTEGER NOT NULL DEFAULT 0,updated_at_utc TEXT NOT NULL,record_json TEXT NOT NULL,
            PRIMARY KEY(username,space,progress_key)
        );
        CREATE UNIQUE INDEX lesson_progress_user_file_idx
            ON lesson_progress(username,file_id) WHERE file_id<>'';
        CREATE TABLE lesson_progress_orphans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL COLLATE NOCASE,space TEXT NOT NULL,
            progress_key TEXT NOT NULL,path TEXT NOT NULL DEFAULT '',identity TEXT NOT NULL DEFAULT '',
            server_revision INTEGER NOT NULL DEFAULT 0,updated_at_utc TEXT NOT NULL,record_json TEXT NOT NULL,
            archived_at_utc TEXT NOT NULL,reason TEXT NOT NULL DEFAULT 'missing_file',
            UNIQUE(username,space,progress_key)
        );
        """
    )
    return connection


def main() -> int:
    connection = make_connection()
    old_key = "legacy-path-key"
    path = "common/Returning.Space_V"
    legacy = {
        "path": path,
        "savedAt": "2026-07-20T02:50:00Z",
        "_serverRevision": 3,
        "learned": True,
        "completedRuns": 2,
        "state": {"learnedWords": [{"key": "alpha"}, {"key": "beta"}], "learned": True},
    }
    connection.execute(
        "INSERT INTO lesson_progress_orphans(username,space,progress_key,path,identity,server_revision,updated_at_utc,record_json,archived_at_utc,reason) "
        "VALUES(?,?,?,?,?,?,?,?,?,'missing_file')",
        ("hung", "Space_V", old_key, path, "legacy-identity", 3, legacy["savedAt"], json.dumps(legacy), legacy["savedAt"]),
    )

    assert app.server_database_restore_legacy_progress_orphans(connection) == 1
    assert app.server_database_restore_legacy_progress_orphans(connection) == 0
    assert connection.execute("SELECT COUNT(*) FROM lesson_progress_orphans").fetchone()[0] == 1
    restored = connection.execute("SELECT * FROM lesson_progress WHERE progress_key=?", (old_key,)).fetchone()
    assert restored is not None and restored["file_id"] == ""

    file_id = "ftg-lesson-returning"
    assert app._server_database_attach_legacy_progress_for_path(connection, file_id, path) == 1
    new_key = progress_key("hung", file_id)
    attached = connection.execute("SELECT * FROM lesson_progress WHERE progress_key=?", (new_key,)).fetchone()
    assert attached is not None and attached["file_id"] == file_id
    attached_record = json.loads(attached["record_json"])
    assert attached_record["lesson_id"] == file_id
    assert len(attached_record["state"]["learnedWords"]) == 2
    assert connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE progress_key=?", (old_key,)).fetchone()[0] == 0

    newer = {
        "path": path,
        "savedAt": "2026-07-20T09:51:00+07:00",
        "_serverRevision": 4,
        "completedRuns": 1,
        "state": {"learnedWords": [{"key": "gamma"}], "learned": False},
    }
    app._server_database_progress_upsert(connection, "hung", "Space_V", new_key, {**newer, "identity": file_id})
    older_key = "second-legacy-key"
    older = {
        "path": path,
        "savedAt": "2026-07-20T02:50:00Z",
        "_serverRevision": 3,
        "completedRuns": 5,
        "learned": True,
        "state": {"learnedWords": [{"key": "old-run"}], "learned": True},
    }
    app._server_database_progress_upsert(connection, "hung", "Space_V", older_key, older)
    assert app._server_database_attach_legacy_progress_for_path(connection, file_id, path) == 1
    merged = json.loads(connection.execute("SELECT record_json FROM lesson_progress WHERE progress_key=?", (new_key,)).fetchone()[0])
    assert [item["key"] for item in merged["state"]["learnedWords"]] == ["gamma"]
    assert merged["learned"] is True and merged["completedRuns"] == 5
    assert connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE progress_key=?", (older_key,)).fetchone()[0] == 0

    runtime_source = (ROOT / "FUTURE/server_parts/06a_server_database.py").read_text(encoding="utf-8")
    assert '"quarantined_aliases": quarantined_aliases' in runtime_source
    assert 'SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(path, None)' in runtime_source
    print("lesson_progress_orphan_recovery=ok archive_retained=true legacy_hot=true exact_path_reattach=true newest_run=true lifetime_history=true collision_cache_quarantined=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
