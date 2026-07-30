"""Regression checks for SQLite-only vocab, period state, dashboard logs, and Structure."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from FUTURE import server_app as app


def main() -> int:
    registry = app.read_user_vocab_registry("hung")
    summary = app.read_user_vocab_registry_summary("hung")
    snapshot = app.read_user_vocab_registry_snapshot("hung")
    period = app.load_vocab_leaderboard_period_state()
    learning = app.read_jsonl_log(app.LEARNING_LOG_FILE, limit=3, keep_days=0)
    login = app.read_jsonl_log(app.LOGIN_LOG_FILE, limit=3, keep_days=0)
    pdf_state = app.pdf_vocabulary_registry_cache_state("hung")
    app.append_jsonl_log(app.LOGIN_LOG_FILE, {"event": "login", "user": "codexsqliteprobe"})
    if app.LOGIN_LOG_FILE.exists():
        raise AssertionError("SQLite-only login logging recreated the retired text file")
    connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
    try:
        connection.execute("DELETE FROM append_events WHERE username='codexsqliteprobe'")
        connection.commit()
    finally:
        connection.close()
    counts = (len(registry.get("words", {})), int(summary.get("total_words", 0)), len(snapshot.get("words", {})))
    if not counts[0] or counts[0] != counts[1] or counts[0] != counts[2]:
        raise AssertionError(f"Vocabulary SQLite readers disagree: {counts}")
    print(
        f"vocab={counts[0]} period_users={len(period.get('users', {}))} "
        f"learning_rows={len(learning)} login_rows={len(login)} pdf_keys={len(pdf_state.get('learned_keys', set()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
