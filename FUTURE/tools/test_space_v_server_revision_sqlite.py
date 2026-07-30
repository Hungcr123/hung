"""Verify stale queued Space_V writes cannot overwrite a newer accepted server revision."""

from __future__ import annotations

import json
import sqlite3


DATABASE = r"C:\server data\server2.db"


def main() -> int:
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    row = connection.execute(
        "SELECT * FROM lesson_progress WHERE username=? AND space=? AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
        ("hung", "Space_V", "common/File 02 - {7}.Space_V"),
    ).fetchone()
    assert row is not None
    source = dict(row)
    base_revision = int(source.get("server_revision", 0) or 0)
    sql = (
        "INSERT INTO lesson_progress(username,space,progress_key,path,identity,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,record_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username,space,progress_key) DO UPDATE SET "
        "path=excluded.path,identity=excluded.identity,node_index=excluded.node_index,node_count=excluded.node_count,"
        "learned_count=excluded.learned_count,complete=excluded.complete,server_revision=excluded.server_revision,"
        "updated_at_utc=excluded.updated_at_utc,record_json=excluded.record_json "
        "WHERE excluded.server_revision>=lesson_progress.server_revision"
    )

    def values(revision: int, marker: str):
        record = json.loads(source["record_json"])
        record["_serverRevision"] = revision
        record["_revisionTestMarker"] = marker
        return (
            source["username"], source["space"], source["progress_key"], source["path"], source["identity"],
            source["node_index"], source["node_count"], source["learned_count"], source["complete"], revision,
            source["updated_at_utc"], json.dumps(record, ensure_ascii=False, separators=(",", ":")),
        )

    try:
        connection.execute("BEGIN IMMEDIATE")
        newer_revision = base_revision + 2
        stale_revision = base_revision + 1
        newest_revision = base_revision + 3
        connection.execute(sql, values(newer_revision, "newer"))
        connection.execute(sql, values(stale_revision, "stale"))
        kept = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress WHERE username=? AND space=? AND progress_key=?",
            (source["username"], source["space"], source["progress_key"]),
        ).fetchone()
        assert kept["server_revision"] == newer_revision and json.loads(kept["record_json"])["_revisionTestMarker"] == "newer"
        connection.execute(sql, values(newest_revision, "newest"))
        newest = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress WHERE username=? AND space=? AND progress_key=?",
            (source["username"], source["space"], source["progress_key"]),
        ).fetchone()
        assert newest["server_revision"] == newest_revision and json.loads(newest["record_json"])["_revisionTestMarker"] == "newest"
    finally:
        connection.execute("ROLLBACK")
        connection.close()
    print("space_v_server_revision_sqlite=ok stale=reject newer=accept rollback=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
