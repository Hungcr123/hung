"""Verify Task Board lesson-state presence stays RAM-fast and generation-correct."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


class FakeRow:
    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        if key == "username":
            return self.value
        return self.value


class FakeConnection:
    def __init__(self, result=0, users=None, registered_users=None):
        self.result = result
        self.users = list(users or [])
        self.registered_users = list(registered_users or self.users)
        self.execute_count = 0

    def execute(self, query, params=()):
        self.execute_count += 1
        self.query_mode = "state" if "UNION SELECT username" in query else ("users" if query.strip() == "SELECT username FROM users" else "probe")
        return self

    def fetchall(self):
        if getattr(self, "query_mode", "") == "state":
            return [FakeRow(username) for username in self.users]
        if getattr(self, "query_mode", "") == "users":
            return [FakeRow(username) for username in self.registered_users]
        return []

    def fetchone(self):
        return (self.result,)

    def close(self):
        return None


def main() -> int:
    original_file = app.SERVER_DATABASE_FILE
    original_connect = app.server_database_connect
    original_users = set(app.SERVER_DATABASE_LESSON_STATE_USERS)
    original_signatures = dict(app.SERVER_DATABASE_LESSON_STATE_SIGNATURES)
    original_generations = {
        key: dict(value)
        for key, value in app.SERVER_DATABASE_USER_CHANGE_GENERATIONS.items()
    }
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "server2.db"
            database.touch()
            app.SERVER_DATABASE_FILE = database
            for key in ("progress", "lesson_time", "registry", "events"):
                app.SERVER_DATABASE_USER_CHANGE_GENERATIONS.setdefault(key, {}).clear()

            preload = FakeConnection(users=["cacheduser"], registered_users=["cacheduser", "emptyuser"])
            assert app.server_database_load_lesson_state_presence_cache(preload) == 1
            assert preload.execute_count == 2

            unexpected = FakeConnection(result=0)
            app.server_database_connect = lambda: unexpected
            assert app.server_database_user_has_lesson_state("cacheduser") is True
            assert unexpected.execute_count == 0
            assert app.server_database_user_has_lesson_state("emptyuser") is False
            assert unexpected.execute_count == 0

            changed = FakeConnection(result=0)
            app.server_database_bump_user_generation("progress", "cacheduser")
            app.server_database_connect = lambda: changed
            assert app.server_database_user_has_lesson_state("cacheduser") is False
            assert changed.execute_count == 1
            assert app.server_database_user_has_lesson_state("cacheduser") is False
            assert changed.execute_count == 1

            created = FakeConnection(result=1)
            app.server_database_bump_user_generation("lesson_time", "newuser")
            app.server_database_connect = lambda: created
            assert app.server_database_user_has_lesson_state("newuser") is True
            assert created.execute_count == 1
            assert app.server_database_user_has_lesson_state("newuser") is True
            assert created.execute_count == 1
    finally:
        app.SERVER_DATABASE_FILE = original_file
        app.server_database_connect = original_connect
        app.SERVER_DATABASE_LESSON_STATE_USERS.clear()
        app.SERVER_DATABASE_LESSON_STATE_USERS.update(original_users)
        app.SERVER_DATABASE_LESSON_STATE_SIGNATURES.clear()
        app.SERVER_DATABASE_LESSON_STATE_SIGNATURES.update(original_signatures)
        app.SERVER_DATABASE_USER_CHANGE_GENERATIONS.clear()
        app.SERVER_DATABASE_USER_CHANGE_GENERATIONS.update(original_generations)
    print("lesson_state_presence_cache=ok startup=preloaded unchanged=zero_sql changed=one_sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
