"""Regression checks for SQLite-backed NPC day/week/month leaderboard scores."""

from __future__ import annotations

import atexit
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-npc-period-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root / "server-data"
        app.USER_ROOT = root / "users"
        app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.initialize_server_database()

        scopes = {
            "day": {"bucket": "2026-07-20", "words": {"npc day": "2026-07-20T02:00:00Z"}},
            "week": {"bucket": "2026-07-20", "words": {"npc week": "2026-07-20T09:00:00+07:00"}},
            "month": {"bucket": "2026-07", "words": {"npc month": "2026-07-20 09:00:00"}},
        }
        result = app.server_database_record_npc_period_activity("npc1", scopes)
        assert result["recorded"] == 3
        loaded = app.server_database_period_scopes(
            "npc1",
            {"day": "2026-07-20", "week": "2026-07-20", "month": "2026-07"},
        )
        assert all(len(loaded[scope]["words"]) == 1 for scope in ("day", "week", "month"))
        assert app.timestamp_to_epoch("2026-07-20T02:00:00Z") == app.timestamp_to_epoch("2026-07-20T09:00:00+07:00")
        assert app.timestamp_to_epoch("2026-07-20 09:00:00") == app.timestamp_to_epoch("2026-07-20T09:00:00+07:00")

        app.VOCAB_LEADERBOARD_PERIOD_FILE = app.SERVER_DATA_ROOT / "_future_vocab_leaderboard_periods.json"
        app.VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE = {"stamp": (), "state": {}}
        cached_state = app.load_vocab_leaderboard_period_state(clone=False)
        assert cached_state is app.load_vocab_leaderboard_period_state(clone=False)
        cloned_state = app.load_vocab_leaderboard_period_state()
        assert cloned_state is not cached_state
        cloned_state.setdefault("users", {}).clear()
        assert "npc1" in cached_state.get("users", {})

        document = app.SERVER_DATA_ROOT / "same.json"
        assert app.server_database_store_document_now(document, '{"same":true}', authoritative=True)
        first_signature = app.server_database_document_signature(document)
        assert app.server_database_store_document_now(document, '{"same":true}', authoritative=True)
        assert app.server_database_document_signature(document) == first_signature

        connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
        try:
            assert connection.execute("SELECT COUNT(*) FROM users WHERE username='npc1'").fetchone()[0] == 0
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            connection.close()
        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        atexit.unregister(app.flush_auth_sessions_to_disk)
    print("npc_period_sqlite=ok scopes=day/week/month login_user=false timestamps=numeric")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
