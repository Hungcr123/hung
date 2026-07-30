"""Regression: PostgreSQL period Top recovery does not require server2.db."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app
from FUTURE.postgres.repositories import vocabulary as pg_vocabulary


def main() -> int:
    original_database_file = app.SERVER_DATABASE_FILE
    original_backend_mode = app.postgres_backend_mode
    original_period_scopes = pg_vocabulary.period_scopes
    expected = {"day": {"bucket": "2026-07-29", "words": {"word": "2026-07-29T00:00:00Z"}}}
    try:
        with tempfile.TemporaryDirectory(prefix="future-pg-period-no-sqlite-") as temp:
            app.SERVER_DATABASE_FILE = Path(temp) / "missing-server2.db"
            app.postgres_backend_mode = lambda _domain: "postgres"
            pg_vocabulary.period_scopes = lambda username, buckets, resets=None: expected if username == "hung" else {}
            assert app.server_database_period_scopes("hung", {"day": "2026-07-29"}) == expected
            assert not app.SERVER_DATABASE_FILE.exists()
    finally:
        app.SERVER_DATABASE_FILE = original_database_file
        app.postgres_backend_mode = original_backend_mode
        pg_vocabulary.period_scopes = original_period_scopes
    print("postgres_period_scopes_without_sqlite=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
