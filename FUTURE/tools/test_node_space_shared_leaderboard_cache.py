"""Regression checks for the shared compact node-space Top cache."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original_loader = app.load_space_leaderboard_activity_state
    original_is_test = app.server_database_is_test_user
    original_full_build = app.vocabulary_leaderboard
    original_registered = app.list_registered_users
    original_profile = app.read_user_profile
    users = {
        f"user{index:03d}": {
            "total_points": index + 1,
            "day": {"points": index + 1},
            "week": {"points": index + 1},
            "month": {"points": index + 1},
            "completed": {},
        }
        for index in range(100)
    }
    state = {"boards": {"space_w": {"users": users, "updated_at": "2026-07-29T00:00:00Z"}}}

    app.load_space_leaderboard_activity_state = lambda clone=False: state
    app.server_database_is_test_user = lambda _username: False
    app.list_registered_users = lambda: [*(f"real{index:02d}" for index in range(12)), "sound"]
    app.read_user_profile = lambda username: {"full_name": f"Profile {username}", "gender": "other", "avatar": f"/{username}.webp"}
    app.vocabulary_leaderboard = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full build used"))
    try:
        app.invalidate_vocab_leaderboard_response_cache("space_w")
        before_seed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        with ThreadPoolExecutor(max_workers=20) as pool:
            rows = list(pool.map(lambda index: app.vocab_leaderboard_response_cache_row(80, f"viewer{index:03d}", "space_w"), range(40)))
        after_seed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        assert after_seed - before_seed == 1, (before_seed, after_seed)
        assert len({row["bytes"] for row in rows}) == 1
        assert ("space_w", 80, "") in app.VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE
        assert not any(key[0] == "space_w" and key[2] for key in app.VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE)

        users["user000"].update({
            "total_points": 250,
            "day": {"points": 250},
            "week": {"points": 250},
            "month": {"points": 250},
        })
        app.invalidate_vocab_leaderboard_response_cache("space_w")
        before_reseed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        with ThreadPoolExecutor(max_workers=20) as pool:
            refreshed = list(pool.map(lambda index: app.vocab_leaderboard_response_cache_row(80, f"next{index:03d}", "space_w"), range(40)))
        after_reseed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        assert after_reseed - before_reseed == 1, (before_reseed, after_reseed)
        row = refreshed[0]
        payload = json.loads(row["bytes"].decode("utf-8"))
        first = payload["boards"]["total"][0]
        assert first["username"] == "user000" and first["score"] == 250, first

        state["boards"]["space_w"]["users"] = {}
        app.invalidate_vocab_leaderboard_response_cache("space_w")
        empty_row = app.vocab_leaderboard_response_cache_row(10, "viewer", "space_w")
        empty_payload = json.loads(empty_row["bytes"].decode("utf-8"))
        placeholders = empty_payload["boards"]["total"]
        assert len(placeholders) == 10, len(placeholders)
        assert all(item.get("placeholder") and item.get("score") == 0 and item.get("avatar") for item in placeholders), placeholders
        assert not any(item.get("username") == "sound" for item in placeholders), placeholders
    finally:
        app.load_space_leaderboard_activity_state = original_loader
        app.server_database_is_test_user = original_is_test
        app.vocabulary_leaderboard = original_full_build
        app.list_registered_users = original_registered
        app.read_user_profile = original_profile
        app.invalidate_vocab_leaderboard_response_cache("space_w")

    print("node_space_shared_leaderboard_cache=ok shared_seed=1 shared_reseed=1 viewer_caches=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
