"""Regression for lossless chat migration, durable messages, and operation idempotency."""

from __future__ import annotations

import atexit
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-chat-sqlite-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root / "server-data"
        app.USER_ROOT = root / "users"
        app.CHAT_FILE = app.USER_ROOT / "_future_chat_messages.json"
        app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.initialize_server_database()

        legacy = {
            "messages": [
                {"id": 1, "username": "alpha", "sender": "user", "text": "hello", "at": "2026-07-20T02:00:00Z", "ts": 1784512800},
                {"id": 2, "username": "alpha", "sender": "admin", "text": "hi", "at": "2026-07-20T09:00:00+07:00", "ts": 1784512800},
            ],
            "admin_read": {"alpha": 1},
            "user_read": {"alpha": 2},
        }
        assert app.server_database_store_document_now(app.CHAT_FILE, json.dumps(legacy), authoritative=True)
        connection = app.server_database_connect()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM database_meta WHERE key='chat_rows_v1'")
        migrated = app.server_database_migrate_chat_document(connection)
        connection.commit()
        connection.close()
        assert migrated["messages"] == 2 and migrated["read_rows"] == 1 and migrated["retired_documents"] == 1

        state = app.server_database_load_chat_state()
        assert [row["id"] for row in state["messages"]] == [1, 2]
        assert state["admin_read"] == {"alpha": 1} and state["user_read"] == {"alpha": 2}
        item = {"username": "alpha", "sender": "user", "text": "durable", "at": "2026-07-20 09:00:00", "ts": 1784512800}
        first = app.server_database_add_chat_message(item, "chat-operation-0001")
        retry = app.server_database_add_chat_message(item, "chat-operation-0001")
        assert not first["duplicate"] and retry["duplicate"]
        assert first["message"]["id"] == retry["message"]["id"]
        assert app.server_database_update_chat_read("alpha", "admin_read", first["message"]["id"])
        assert not app.server_database_update_chat_read("alpha", "admin_read", first["message"]["id"])

        connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
        assert connection.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM documents WHERE lower(path) LIKE '%_future_chat_messages.json'").fetchone()[0] == 0
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        connection.close()
        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        atexit.unregister(app.flush_auth_sessions_to_disk)
        print("chat_sqlite=ok migrated=2 unique=1 duplicate=noop read_marker=monotonic legacy_document=retired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
