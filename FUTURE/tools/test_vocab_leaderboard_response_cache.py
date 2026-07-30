"""Regression checks for final leaderboard JSON-byte caching and cold-build coalescing."""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original = app.vocabulary_leaderboard
    calls = 0
    calls_lock = threading.Lock()

    def fake_leaderboard(limit=80, double_check=False, viewer="", board_type="space_v"):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.03)
        return {"board_type": board_type, "limit": limit, "viewer": viewer, "boards": {"total": []}}

    app.vocabulary_leaderboard = fake_leaderboard
    try:
        app.invalidate_vocab_leaderboard_response_cache("space_v")
        with ThreadPoolExecutor(max_workers=20) as pool:
            rows = list(pool.map(lambda _index: app.vocab_leaderboard_response_cache_row(80, "hung", "space_v"), range(40)))
        assert calls == 1, calls
        assert len({row["bytes"] for row in rows}) == 1
        assert all(row["etag"].startswith('"vocab-top-') for row in rows)
        assert json.loads(rows[0]["bytes"].decode("utf-8"))["viewer"] == "hung"

        app.invalidate_vocab_leaderboard_response_cache("space_v")
        rebuilt = app.vocab_leaderboard_response_cache_row(80, "hung", "space_v")
        assert calls == 2 and rebuilt["cache_hit"] is False
    finally:
        app.vocabulary_leaderboard = original
        app.invalidate_vocab_leaderboard_response_cache()

    print("vocab_leaderboard_response_cache=ok bytes=true etag=true cold_builds=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
