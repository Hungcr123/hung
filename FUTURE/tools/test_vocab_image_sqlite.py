"""Regression for durable row-based derived Space_V image cache."""

from __future__ import annotations

import atexit
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
    with tempfile.TemporaryDirectory(prefix="future-vocab-image-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root
        app.SERVER_DATABASE_FILE = root / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = root / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.initialize_server_database()

        now = time.time()
        rows = [
            {
                "word_key": "apple",
                "image": {"u": "https://example.test/apple.jpg", "s": "Openverse/unit", "c": "Apple"},
                "expires_epoch": now + 86400,
            },
            {"word_key": "missing", "image": {}, "expires_epoch": now + 600},
        ]
        if app.server_database_store_vocab_image_cache_batch(rows) != 2:
            raise RuntimeError("Could not store the vocabulary image batch")
        positive = app.server_database_load_vocab_image_cache("apple") or {}
        negative = app.server_database_load_vocab_image_cache("missing") or {}
        hydrated = app.server_database_load_vocab_image_cache_rows()
        if positive.get("image", {}).get("u") != "https://example.test/apple.jpg":
            raise RuntimeError("Positive image row did not restore")
        if negative.get("image") != {} or float(negative.get("expires_epoch", 0)) <= now:
            raise RuntimeError("Negative image row did not restore")
        if {row.get("word_key") for row in hydrated} != {"apple", "missing"}:
            raise RuntimeError("Bounded vocabulary image preload did not restore both rows")

        connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
        try:
            schema = int(connection.execute("SELECT value FROM database_meta WHERE key='schema_version'").fetchone()[0])
            count = int(connection.execute("SELECT COUNT(*) FROM vocab_image_cache").fetchone()[0])
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
            synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
        finally:
            connection.close()
        if schema != 12 or count != 2 or quick_check.lower() != "ok" or journal_mode.lower() != "wal" or synchronous != 2:
            raise RuntimeError("Vocabulary image SQLite invariants failed")

        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        try:
            atexit.unregister(app.flush_auth_sessions_to_disk)
        except Exception:
            pass
        print("vocab_image_sqlite=ok schema=12 rows=2 positive=true negative=true wal=FULL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
