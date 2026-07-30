"""Regression checks that retired local-database readers stay unreachable."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from FUTURE import server_app as app


def main() -> int:
    if hasattr(app, "SERVER_DATABASE_FILE"):
        raise AssertionError("Retired local database path is still exported")
    runtime_sources = [ROOT / "FUTURE_SERVER_2.py", ROOT / "FUTURE/server_app.py"]
    runtime_sources.extend((ROOT / "FUTURE/server_parts").rglob("*.py"))
    if any("sqlite3.connect(" in path.read_text(encoding="utf-8", errors="replace") for path in runtime_sources):
        raise AssertionError("A Server 2 runtime connector still reaches sqlite3.connect")
    registry = app.read_user_vocab_registry("hung")
    summary = app.read_user_vocab_registry_summary("hung")
    snapshot = app.read_user_vocab_registry_snapshot("hung")
    period = app.load_vocab_leaderboard_period_state()
    learning = app.read_jsonl_log(app.LEARNING_LOG_FILE, limit=3, keep_days=0)
    login = app.read_jsonl_log(app.LOGIN_LOG_FILE, limit=3, keep_days=0)
    pdf_state = app.pdf_vocabulary_registry_cache_state("hung")
    counts = (len(registry.get("words", {})), int(summary.get("total_words", 0)), len(snapshot.get("words", {})))
    if not counts[0] or counts[0] != counts[1] or counts[0] != counts[2]:
        raise AssertionError(f"Vocabulary PostgreSQL readers disagree: {counts}")
    print(
        f"vocab={counts[0]} period_users={len(period.get('users', {}))} "
        f"learning_rows={len(learning)} login_rows={len(login)} pdf_keys={len(pdf_state.get('learned_keys', set()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
