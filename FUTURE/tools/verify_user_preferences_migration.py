"""Compare production preference rows with a pre-schema-10 database backup."""

from __future__ import annotations

import argparse
import atexit
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup")
    args = parser.parse_args()
    backup = sqlite3.connect(args.backup)
    current = sqlite3.connect(r"C:\server data\server2.db")
    try:
        production_users = {str(row[0]).lower() for row in backup.execute("SELECT username FROM users WHERE is_test=0")}
        expected = {}
        for path, content in backup.execute("SELECT path,content FROM documents WHERE lower(path) LIKE '%.txt'"):
            username = Path(str(path)).stem.lower()
            if username not in production_users or str(path).lower().endswith("_vocab_progress.txt"):
                continue
            text = bytes(content).decode("utf-8", errors="replace")
            for line in text.splitlines()[1:]:
                raw = str(line).strip()
                if not raw.startswith(app.PREFERENCES_PREFIX):
                    continue
                payload = json.loads(raw[len(app.PREFERENCES_PREFIX):].strip())
                expected[username] = app.server_database_preference_identity(app.normalize_user_preferences(payload, {}))
                break
        actual = {
            str(username).lower(): app.server_database_preference_identity(json.loads(str(raw)))
            for username, raw in current.execute(
                "SELECT p.username,p.preferences_json FROM user_preferences p JOIN users u ON u.username=p.username WHERE u.is_test=0"
            )
        }
        missing = sorted(set(expected) - set(actual))
        mismatch = sorted(username for username in expected.keys() & actual.keys() if expected[username] != actual[username])
        extra = sorted(set(actual) - set(expected))
        if missing or mismatch:
            raise RuntimeError(f"Preference migration mismatch: missing={missing} mismatch={mismatch}")
        print(json.dumps({
            "user_preferences_migration": "ok",
            "expected_rows": len(expected),
            "actual_rows": len(actual),
            "missing": len(missing),
            "mismatch": len(mismatch),
            "new_rows_without_legacy": len(extra),
        }, sort_keys=True))
        return 0
    finally:
        backup.close()
        current.close()
        atexit.unregister(app.flush_auth_sessions_to_disk)


if __name__ == "__main__":
    raise SystemExit(main())
