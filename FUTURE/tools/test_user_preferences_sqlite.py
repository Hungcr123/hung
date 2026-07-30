"""Regression for preference migration, merge, retry no-op, and restart reads."""

from __future__ import annotations

import atexit
import concurrent.futures
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
    with tempfile.TemporaryDirectory(prefix="future-preferences-sqlite-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root / "server-data"
        app.USER_ROOT = root / "users"
        app.AUTH_SESSIONS_FILE = app.USER_ROOT / "_future_auth_sessions.json"
        app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.USER_PREFERENCES_RAM_CACHE.clear()
        app.initialize_server_database()

        connection = app.server_database_connect()
        connection.execute(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES('alpha',0,0,'{}','2026-07-20T02:50:00Z')"
        )
        connection.close()
        legacy = {
            "chat_voice": {"enabled": True, "voice": "male-us", "label": "Male US"},
            "updated_at": "2026-07-20T09:50:00+07:00",
        }
        text = "legacy-password\n" + app.PREFERENCES_PREFIX + json.dumps(legacy, separators=(",", ":")) + "\n"
        assert app.server_database_store_document_now(app.user_file_path("alpha"), text, authoritative=True)
        connection = app.server_database_connect()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM database_meta WHERE key='user_preferences_rows_v1'")
        migrated = app.server_database_migrate_user_preferences_documents(connection)
        connection.commit()
        app.server_database_load_user_preferences_cache(connection)
        connection.close()
        assert migrated["rows"] == 1

        app.USER_PREFERENCES_RAM_CACHE.clear()
        initial = app.read_user_preferences("alpha")
        assert initial["chat_voice"]["enabled"] is True
        assert initial["_serverRevision"] == 1
        signature_before = app.auth_me_cache_signature("alpha")
        first = app.save_user_preferences("alpha", {"question_animation": {"paused": True}, "updated_at": "2099-01-01T00:00:00Z"})
        assert first["question_animation"]["paused"] is True and first["_serverRevision"] == 2
        signature_after = app.auth_me_cache_signature("alpha")
        assert signature_after != signature_before
        time.sleep(1.05)
        retry = app.save_user_preferences("alpha", {"question_animation": {"paused": True}, "updated_at": "1999-01-01T00:00:00Z"})
        assert retry["_serverRevision"] == 2 and retry["updated_at"] == first["updated_at"]
        assert app.auth_me_cache_signature("alpha") == signature_after

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(
                lambda payload: app.save_user_preferences("alpha", payload),
                [
                    {"chat_voice_vi": {"enabled": True, "voice": "edge:vi-VN-NamMinhNeural"}},
                    {"pdf_settings": {"ui": {"voice": "edge:en-US-GuyNeural"}}},
                ],
            ))
        assert max(row["_serverRevision"] for row in rows) == 4
        app.USER_PREFERENCES_RAM_CACHE.clear()
        restored = app.read_user_preferences("alpha")
        assert restored["_serverRevision"] == 4
        assert restored["chat_voice_vi"]["enabled"] is True
        assert restored["pdf_settings"]["ui"]["voice"] == "edge:en-US-GuyNeural"
        assert app.timestamp_to_epoch("2026-07-20T02:50:00Z") == app.timestamp_to_epoch("2026-07-20T09:50:00+07:00")
        assert app.timestamp_to_epoch("2026-07-20 09:50:00") == 1784515800.0

        connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
        row = connection.execute("SELECT server_revision,updated_at_utc FROM user_preferences WHERE username='alpha'").fetchone()
        assert row and int(row[0]) == 4 and "2099" not in str(row[1]) and "1999" not in str(row[1])
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        connection.close()
        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        atexit.unregister(app.flush_auth_sessions_to_disk)
        print("user_preferences_sqlite=ok migrated=1 retry=noop concurrent_merge=2 restart=restored client_time=ignored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
