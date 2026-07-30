"""Verify retired vocab/period/log files are fully represented in server2.db."""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def event_identity(row: dict) -> tuple:
    epoch = app.timestamp_to_epoch(row.get("at", "")) or 0.0
    return (
        app.clean(row.get("event", "")),
        app.normalize_username(row.get("user") or row.get("username") or ""),
        app.clean_path_value(row.get("path", "")),
        round(epoch, 3),
        app.clean(row.get("client", "")),
    )


def main() -> int:
    connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    failures = 0
    vocab_files = list(app.SERVER_DATA_ROOT.rglob("_future_learned_vocabulary.json"))
    for path in vocab_files:
        username = app.normalize_username(path.parent.name)
        legacy = json.loads(path.read_text(encoding="utf-8-sig"))
        legacy_keys = {app.vocab_key(key) for key in (legacy.get("words") or {}) if app.vocab_key(key)}
        database_keys = {
            str(row[0])
            for row in connection.execute("SELECT word_key FROM vocabulary_registry WHERE username=?", (username,))
        }
        missing = legacy_keys - database_keys
        failures += len(missing)
        print(f"vocab user={username} legacy={len(legacy_keys)} sqlite={len(database_keys)} missing={len(missing)}")

    period_path = app.VOCAB_LEADERBOARD_PERIOD_FILE
    if period_path.is_file():
        legacy_period = json.loads(period_path.read_text(encoding="utf-8-sig"))
        current_period = app.load_vocab_leaderboard_period_state()
        legacy_users = legacy_period.get("users") if isinstance(legacy_period.get("users"), dict) else {}
        current_users = current_period.get("users") if isinstance(current_period.get("users"), dict) else {}
        missing_users = {app.normalize_username(key) for key in legacy_users} - {app.normalize_username(key) for key in current_users}
        failures += len(missing_users)
        print(
            f"period legacy_users={len(legacy_users)} sqlite_users={len(current_users)} "
            f"missing={len(missing_users)} missing_users={sorted(missing_users)}"
        )

    for stream, path in (("learning", app.LEARNING_LOG_FILE), ("login", app.LOGIN_LOG_FILE)):
        if not path.is_file():
            continue
        legacy_rows = []
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                legacy_rows.append(row)
        database_rows = []
        for row in connection.execute("SELECT event_json FROM append_events WHERE stream=?", (stream,)):
            try:
                payload = json.loads(row[0])
            except Exception:
                continue
            if isinstance(payload, dict):
                database_rows.append(payload)
        legacy_counter = collections.Counter(map(event_identity, legacy_rows))
        database_counter = collections.Counter(map(event_identity, database_rows))
        missing = sum((legacy_counter - database_counter).values())
        failures += missing
        print(f"log stream={stream} legacy={len(legacy_rows)} sqlite={len(database_rows)} missing={missing}")
    connection.close()
    print(f"failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
