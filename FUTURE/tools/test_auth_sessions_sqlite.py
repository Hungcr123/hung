"""Regression for hashed session migration, touch batching, replacement, and expiry."""

from __future__ import annotations

import atexit
import concurrent.futures
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-auth-sessions-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root / "server-data"
        app.USER_ROOT = root / "users"
        app.AUTH_SESSIONS_FILE = app.USER_ROOT / "_future_auth_sessions.json"
        app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.initialize_server_database()

        connection = app.server_database_connect()
        connection.execute(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES('alpha',0,0,'{}','2026-07-20T02:50:00Z')"
        )
        connection.executemany(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,'{}','2026-07-20T02:50:00Z')",
            ((f"batch{index:02d}",) for index in range(20)),
        )
        connection.close()
        raw_token = "legacy-session-token-alpha"
        now = time.time()
        legacy = {"sessions": {raw_token: {
            "username": "alpha",
            "created_at": now - 10,
            "last_seen": now - 2,
            "last_seen_persisted": now - 3,
        }}}
        assert app.server_database_store_document_now(app.AUTH_SESSIONS_FILE, json.dumps(legacy), authoritative=True)
        connection = app.server_database_connect()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM database_meta WHERE key='auth_session_rows_v1'")
        migrated = app.server_database_migrate_auth_session_document(connection)
        connection.commit()
        connection.close()
        assert migrated["rows"] == 1 and migrated["retired_documents"] == 1
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        loaded = app.server_database_load_auth_sessions()
        assert token_hash in loaded and raw_token not in loaded
        with app.AUTH_LOCK:
            app.AUTH_SESSIONS.clear()
            app.AUTH_SESSIONS.update(loaded)
        session, reason = app.auth_session_state_for_token(raw_token)
        assert reason == "ok" and session["username"] == "alpha"

        replacement = "replacement-session-token-alpha"
        replacement_hash = app.auth_session_token_key(replacement)
        assert app.server_database_replace_auth_session("alpha", replacement_hash, now)
        loaded = app.server_database_load_auth_sessions()
        assert set(loaded) == {replacement_hash}
        touched = now + 120
        assert app.server_database_touch_auth_sessions({replacement_hash: {"last_seen": touched}}) == 1
        connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
        row = connection.execute(
            "SELECT token_hash,last_seen_epoch,last_persisted_epoch FROM auth_sessions WHERE username='alpha'"
        ).fetchone()
        assert row and row[0] == replacement_hash and float(row[1]) == touched and float(row[2]) == touched
        assert raw_token not in "".join(str(item) for item in connection.execute("SELECT token_hash FROM auth_sessions"))
        assert connection.execute("SELECT COUNT(*) FROM documents WHERE lower(path) LIKE '%_future_auth_sessions.json'").fetchone()[0] == 0
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        connection.close()
        assert app.server_database_delete_auth_sessions(username="alpha") == 1
        before_tasks = int(app.server_database_write_metrics_snapshot().get("tasks", 0) or 0)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            list(pool.map(
                lambda index: app.persist_auth_session_create(
                    f"batch{index:02d}",
                    app.auth_session_token_key(f"batch-token-{index:02d}"),
                    now + index,
                ),
                range(20),
            ))
        after_tasks = int(app.server_database_write_metrics_snapshot().get("tasks", 0) or 0)
        assert len(app.server_database_load_auth_sessions()) == 20
        assert after_tasks - before_tasks < 20
        expected_epoch = 1784515800.0
        assert app.timestamp_to_epoch("2026-07-20T02:50:00Z") == expected_epoch
        assert app.timestamp_to_epoch("2026-07-20T09:50:00+07:00") == expected_epoch
        assert app.timestamp_to_epoch("2026-07-20 09:50:00") == expected_epoch
        assert app.timestamp_to_epoch("") == 0.0
        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        atexit.unregister(app.flush_auth_sessions_to_disk)
        print("auth_sessions_sqlite=ok migration=hashed replace=atomic create=batch touch=row delete=durable legacy=retired time=epoch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
