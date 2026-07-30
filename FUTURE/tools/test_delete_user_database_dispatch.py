"""Regression checks for PostgreSQL and legacy SQLite account deletion."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


# Added 2026-07-29: account cleanup must cover PostgreSQL and any surviving legacy SQLite rows.
def main() -> int:
    original = {
        "backend": app.postgres_backend_mode,
        "pg_delete": app.postgres_delete_user_data,
        "db_file": app.SERVER_DATABASE_FILE,
        "submit": app.server_database_submit_write,
        "user_root": app.USER_ROOT,
        "server_data_root": app.SERVER_DATA_ROOT,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="future-delete-user-") as temp:
            root = Path(temp)
            app.USER_ROOT = root / "users"
            app.SERVER_DATA_ROOT = root / "server-data"
            app.SERVER_DATABASE_FILE = root / "missing.db"
            captured = {}
            app.postgres_backend_mode = lambda _domain: "postgres"
            app.postgres_delete_user_data = lambda username, fragments: captured.update({"username": username, "fragments": fragments}) or {"deleted": 7, "tables": {"users": 1}}
            result = app.server_database_delete_user("codexunit")
            assert result["deleted"] == 7
            assert captured["username"] == "codexunit"
            assert len(captured["fragments"]) == 3

            database = root / "server2.db"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE users(username TEXT PRIMARY KEY);
                CREATE TABLE vault_entries(username TEXT, value TEXT);
                CREATE TABLE documents(path_key TEXT PRIMARY KEY, path TEXT);
                INSERT INTO users VALUES('codexunit');
                INSERT INTO vault_entries VALUES('codexunit','x');
                """
            )
            connection.commit()
            connection.close()
            app.SERVER_DATABASE_FILE = database
            app.postgres_backend_mode = lambda _domain: "sqlite"

            def submit(callback):
                local = sqlite3.connect(database)
                try:
                    value = callback(local)
                    local.commit()
                    return value
                finally:
                    local.close()

            app.server_database_submit_write = submit
            result = app.server_database_delete_user("codexunit")
            assert result["sqlite"]["deleted"] == 2
            check = sqlite3.connect(database)
            try:
                assert check.execute("SELECT count(*) FROM users").fetchone()[0] == 0
                assert check.execute("SELECT count(*) FROM vault_entries").fetchone()[0] == 0
            finally:
                check.close()
    finally:
        app.postgres_backend_mode = original["backend"]
        app.postgres_delete_user_data = original["pg_delete"]
        app.SERVER_DATABASE_FILE = original["db_file"]
        app.server_database_submit_write = original["submit"]
        app.USER_ROOT = original["user_root"]
        app.SERVER_DATA_ROOT = original["server_data_root"]
    print("delete_user_database_dispatch=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
