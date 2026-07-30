"""Exercise the production lesson-time credit function against an isolated SQLite database."""

from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import json
import math
import re
import sqlite3
import tempfile
import threading
from datetime import datetime
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "06a_server_database.py"


class FakeTime:
    now = 1784515800.0

    @classmethod
    def time(cls) -> float:
        return cls.now

    @classmethod
    def monotonic(cls) -> float:
        return cls.now


def load_production_function(database: Path):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "server_database_lesson_time_row",
        "server_database_lesson_time_offline_lease",
        "server_database_verify_lesson_time_offline_lease",
        "server_database_add_lesson_time",
    }
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]

    def clean(value) -> str:
        return str(value or "").strip()

    statements: list[str] = []

    def submit_write(callback, source=""):
        connection = sqlite3.connect(database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.set_trace_callback(statements.append)
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = callback(connection)
            connection.execute("COMMIT")
            return result
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    namespace = {
        "sqlite3": sqlite3,
        "base64": base64,
        "hashlib": hashlib,
        "hmac": hmac,
        "json": json,
        "math": math,
        "re": re,
        "time": FakeTime,
        "clean": clean,
        "clean_path_value": lambda value: clean(value).replace("\\", "/").strip("/"),
        "normalize_username": lambda value: clean(value).lower(),
        "space_w_int": lambda value, fallback=0: int(value if value is not None else fallback),
        "local_timestamp": lambda epoch: datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds"),
        "server_database_ensure_user": lambda connection, username: connection.execute(
            "INSERT OR IGNORE INTO users(username) VALUES(?)", (username,)
        ),
        "server_database_submit_write": submit_write,
        "SERVER_DATABASE_CHANGE_GENERATIONS": {"lesson_time": 0},
        "server_database_bump_user_generation": lambda *_args: 0,
        "SERVER_DATABASE_LESSON_TIME_RAM_CACHE_LOCK": threading.RLock(),
        "SERVER_DATABASE_LESSON_TIME_RAM_CACHE": {},
        "LESSON_TIME_SERVER_BOOT_ID": "boot-a",
        "LESSON_TIME_SERVER_BOOT_EPOCH": 1784515800,
        "LESSON_TIME_PROTOCOL": "server-time-v1",
        "LESSON_TIME_MAX_HEARTBEAT_SECONDS": 60,
        "LESSON_TIME_ACTIVE_SESSION_LEASE_SECONDS": 90,
        "LESSON_TIME_OFFLINE_CREDIT_MAX_SECONDS": 7200,
        "LESSON_TIME_OFFLINE_LEASE_SECONDS": 14400,
        "LESSON_TIME_OFFLINE_CLAIM_GRACE_SECONDS": 86400,
        "LESSON_TIME_RESTART_CLAIM_BOUNDARY_SECONDS": 900,
        "LESSON_TIME_LEASE_SECRET": hashlib.sha256(b"test-lesson-time-secret").digest(),
        "LESSON_TIME_HEARTBEAT_RAM_LOCK": threading.RLock(),
        "LESSON_TIME_HEARTBEAT_RAM": {},
        "LESSON_TIME_HEARTBEAT_RAM_MAX": 20_000,
        "_statements": statements,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace, namespace["server_database_add_lesson_time"]


def totals(database: Path) -> tuple[int, int]:
    connection = sqlite3.connect(database)
    row = connection.execute("SELECT COALESCE(SUM(seconds),0),COALESCE(SUM(ticks),0) FROM lesson_time").fetchone()
    connection.close()
    return int(row[0]), int(row[1])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-lesson-time-") as temp:
        database = Path(temp) / "lesson-time.db"
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            CREATE TABLE users (username TEXT PRIMARY KEY COLLATE NOCASE);
            CREATE TABLE lesson_time (
                username TEXT NOT NULL COLLATE NOCASE, lesson_key TEXT NOT NULL, file_id TEXT NOT NULL DEFAULT '', path TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '', space TEXT NOT NULL DEFAULT '', seconds INTEGER NOT NULL DEFAULT 0,
                ticks INTEGER NOT NULL DEFAULT 0, updated_at_utc TEXT NOT NULL, updated_epoch REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (username, lesson_key), FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            CREATE TABLE lesson_time_credit_state (
                username TEXT NOT NULL COLLATE NOCASE, lesson_key TEXT NOT NULL, file_id TEXT NOT NULL DEFAULT '', session_id TEXT NOT NULL,
                last_sequence INTEGER NOT NULL DEFAULT 0, last_seen_epoch REAL NOT NULL DEFAULT 0,
                boot_id TEXT NOT NULL DEFAULT '', lease_issued_epoch REAL NOT NULL DEFAULT 0,
                offline_credited_seconds INTEGER NOT NULL DEFAULT 0, updated_at_utc TEXT NOT NULL,
                PRIMARY KEY (username, lesson_key), FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            CREATE TABLE lesson_file_aliases (
                normalized_path TEXT PRIMARY KEY COLLATE NOCASE, file_id TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
            );
            INSERT INTO users(username) VALUES('codex_time');
            """
        )
        connection.close()
        namespace, add = load_production_function(database)

        statements = namespace["_statements"]
        statements.clear()
        query_session = "lesson-query-budget"
        query_key = "query-budget-key"
        query_start = add(
            "codex_time", query_key, "", "common/query.Space_V", "Query", "Space_V",
            0, query_session, 0, "server-time-v1", authenticated_user=True,
        )
        assert query_start["heartbeatReason"] == "session_started"
        assert not any("SELECT 1 FROM users" in sql for sql in statements)
        statements.clear()
        FakeTime.now += 30
        query_credited = add(
            "codex_time", query_key, "", "common/query.Space_V", "Query", "Space_V",
            30, query_session, 1, "server-time-v1", authenticated_user=True,
        )
        assert query_credited["acceptedSeconds"] == 30
        assert not any("SELECT 1 FROM users" in sql for sql in statements)
        assert not any("FROM lesson_time WHERE" in sql for sql in statements)
        cleanup = sqlite3.connect(database)
        cleanup.execute("DELETE FROM lesson_time_credit_state WHERE username=? AND lesson_key=?", ("codex_time", query_key))
        cleanup.execute("DELETE FROM lesson_time WHERE username=? AND lesson_key=?", ("codex_time", query_key))
        cleanup.commit()
        cleanup.close()
        FakeTime.now = 1784515800.0

        def heartbeat(seconds, session="lesson-session-a", sequence=0, protocol="server-time-v1", **kwargs):
            return add(
                "codex_time", "lesson-key", "", "common/test.Space_V", "Test", "Space_V",
                seconds, session, sequence, protocol, kwargs.get("offline_claims"), kwargs.get("offline_lease", ""),
            )

        assert heartbeat(0, sequence=0)["heartbeatReason"] == "session_started"
        FakeTime.now = 1784515830
        assert heartbeat(30, sequence=1)["acceptedSeconds"] == 30
        assert heartbeat(30, sequence=1)["heartbeatReason"] == "replay"
        for sequence in range(2, 102):
            assert heartbeat(30, sequence=sequence)["acceptedSeconds"] == 0
        assert totals(database) == (30, 1)
        assert heartbeat(30, sequence=50)["heartbeatReason"] == "replay"

        FakeTime.now = 1784515860
        assert heartbeat(30, sequence=102)["acceptedSeconds"] == 30
        assert heartbeat(30, session="lesson-session-b", sequence=0)["heartbeatReason"] == "session_conflict"
        FakeTime.now = 1784515951
        assert heartbeat(0, session="lesson-session-b", sequence=0)["heartbeatReason"] == "session_resumed"
        FakeTime.now = 1784515981
        assert heartbeat(30, session="lesson-session-b", sequence=1)["acceptedSeconds"] == 30

        namespace["LESSON_TIME_SERVER_BOOT_ID"] = "boot-b"
        FakeTime.now = 1784516011
        assert heartbeat(30, session="lesson-session-b", sequence=2)["heartbeatReason"] == "server_restarted"
        FakeTime.now = 1784516041
        assert heartbeat(30, session="lesson-session-b", sequence=3)["acceptedSeconds"] == 30
        FakeTime.now = 1784516000
        assert heartbeat(30, session="lesson-session-b", sequence=4)["acceptedSeconds"] == 0
        assert totals(database) == (120, 4)

        for invalid in (-1, 61, float("nan"), float("inf"), "30"):
            try:
                heartbeat(invalid, session="lesson-invalid", sequence=1)
                raise AssertionError(f"invalid seconds accepted: {invalid!r}")
            except RuntimeError:
                pass

        FakeTime.now = 1784517000
        offline_start = add(
            "codex_time", "offline-key", "", "common/offline.Space_V", "Offline", "Space_V",
            0, "lesson-offline-session", 0, "server-time-v1",
        )
        lease = offline_start["offlineLease"]
        FakeTime.now = 1784517030
        assert add(
            "codex_time", "offline-key", "", "common/offline.Space_V", "Offline", "Space_V",
            30, "lesson-offline-session", 1, "server-time-v1", None, lease,
        )["acceptedSeconds"] == 30
        namespace["LESSON_TIME_SERVER_BOOT_ID"] = "boot-c"
        namespace["LESSON_TIME_SERVER_BOOT_EPOCH"] = 1784517090
        FakeTime.now = 1784517150
        claims = [{"sequence": 2, "seconds": 30}, {"sequence": 3, "seconds": 30}]
        offline_result = add(
            "codex_time", "offline-key", "", "common/offline.Space_V", "Offline", "Space_V",
            0, "lesson-offline-session", 3, "server-time-v1", claims, lease,
        )
        assert offline_result["acceptedSeconds"] == 60 and offline_result["heartbeatReason"] == "offline_credited"
        replay = add(
            "codex_time", "offline-key", "", "common/offline.Space_V", "Offline", "Space_V",
            0, "lesson-offline-session", 3, "server-time-v1", claims, lease,
        )
        assert replay["acceptedSeconds"] == 0 and replay["heartbeatReason"] == "replay"
        try:
            add(
                "codex_time", "offline-key", "", "common/offline.Space_V", "Offline", "Space_V",
                0, "lesson-offline-session", 4, "server-time-v1", [{"sequence": 4, "seconds": 30}], lease + "x",
            )
            raise AssertionError("tampered offline lease was accepted")
        except RuntimeError:
            pass

        FakeTime.now = 1784518000
        boundary_start = add(
            "codex_time", "boundary-key", "", "common/boundary.Space_V", "Boundary", "Space_V",
            0, "lesson-boundary-session", 0, "server-time-v1",
        )
        namespace["LESSON_TIME_SERVER_BOOT_ID"] = "boot-d"
        namespace["LESSON_TIME_SERVER_BOOT_EPOCH"] = 1784519000
        FakeTime.now = 1784519901
        boundary_result = add(
            "codex_time", "boundary-key", "", "common/boundary.Space_V", "Boundary", "Space_V",
            0, "lesson-boundary-session", 1, "server-time-v1", [{"sequence": 1, "seconds": 30}], boundary_start["offlineLease"],
        )
        assert boundary_result["heartbeatReason"] == "offline_restart_window_expired"

        print("lesson_time_antitamper=ok replay=reject spam_100=zero multi_device=lease restart=no_catchup offline=signed_bounded restart_boundary=15m clock_back=no_credit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
