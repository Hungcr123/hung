"""Regression checks for indexed lesson-time migration and lossless SQLite authority."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DATABASE = Path(r"C:\server data\server2.db")
BASELINE = Path(r"E:\FutureServer2LegacyBackup\2026-07-20_104235_lesson_time_sqlite_delta\server2.db")


def main() -> int:
    connection = sqlite3.connect(DATABASE)
    marker = connection.execute("SELECT value FROM database_meta WHERE key='lesson_time_table_v1'").fetchone()
    legacy_documents = connection.execute(
        "SELECT COUNT(*) FROM documents WHERE lower(path) LIKE ?",
        ("%_future_lesson_time.json",),
    ).fetchone()[0]
    rows = connection.execute(
        "SELECT username,lesson_key,seconds,ticks,updated_epoch FROM lesson_time",
    ).fetchall()
    connection.close()
    assert marker and int(marker[0]) > 0
    assert legacy_documents == 0
    assert rows and len({(row[0].lower(), row[1]) for row in rows}) == len(rows)
    assert all(int(row[2]) >= 0 and int(row[3]) >= 0 and float(row[4]) > 0 for row in rows)

    baseline = sqlite3.connect(BASELINE)
    documents = baseline.execute(
        "SELECT path,content FROM documents WHERE lower(path) LIKE ?",
        ("%_future_lesson_time.json",),
    ).fetchall()
    baseline.close()
    expected = {}
    for path, content in documents:
        username = Path(path).parent.name.lower()
        payload = json.loads(bytes(content).decode("utf-8"))
        for lesson_key, row in (payload.get("states") or {}).items():
            expected[(username, lesson_key)] = (int(row.get("seconds", 0) or 0), int(row.get("ticks", 0) or 0))
    actual = {(row[0].lower(), row[1]): (int(row[2]), int(row[3])) for row in rows}
    missing = [key for key in expected if key not in actual]
    regressed = [key for key, value in expected.items() if key in actual and (actual[key][0] < value[0] or actual[key][1] < value[1])]
    assert not missing and not regressed, (missing[:5], regressed[:5])
    print(f"lesson_time_sqlite=ok rows={len(rows)} users={len({row[0].lower() for row in rows})} legacy_documents=0 lossless=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
