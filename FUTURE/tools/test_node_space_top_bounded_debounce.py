"""Regression checks for bounded node-space Top debounce and revision safety."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def wait_for_publish(board_type: str, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = app.node_space_top_batch_status(board_type)
        if not status.get("pending"):
            return status
        time.sleep(0.01)
    raise AssertionError(app.node_space_top_batch_status(board_type))


def main() -> int:
    original_loader = app.load_space_leaderboard_activity_state
    original_is_test = app.server_database_is_test_user
    original_quiet = app.VOCAB_NODE_TOP_BATCH_QUIET_SECONDS
    original_max_wait = app.VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS
    state = {
        "boards": {
            "space_w": {
                "users": {
                    "user001": {
                        "total_points": 10,
                        "day": {"points": 10, "bucket": app.vocab_period_bucket("day", time.time())},
                        "week": {"points": 10, "bucket": app.vocab_period_bucket("week", time.time())},
                        "month": {"points": 10, "bucket": app.vocab_period_bucket("month", time.time())},
                        "completed": {},
                    }
                },
                "updated_at": "2026-07-29T00:00:00Z",
            }
        }
    }
    app.load_space_leaderboard_activity_state = lambda clone=False: state
    app.server_database_is_test_user = lambda _username: False
    app.VOCAB_NODE_TOP_BATCH_QUIET_SECONDS = 0.08
    app.VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS = 0.16
    try:
        app.invalidate_vocab_leaderboard_response_cache("space_w")
        with app.VOCAB_NODE_TOP_BATCH_LOCK:
            app.VOCAB_NODE_TOP_BATCH_STATE["boards"] = {}
            app.VOCAB_NODE_TOP_BATCH_STATE["revision"] = 0
        cold = app.vocab_leaderboard_response_cache_row(80, "user001", "space_w")
        assert not cold.get("pending"), cold
        cold_payload = json.loads(cold["bytes"].decode("utf-8"))
        assert cold_payload["boards"]["total"][0]["score"] == 10

        before_seed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        state["boards"]["space_w"]["users"]["user001"]["total_points"] = 30
        state["boards"]["space_w"]["users"]["user001"]["day"]["points"] = 30
        for _ in range(20):
            app.mark_node_space_top_dirty("space_w")
            time.sleep(0.002)
        time.sleep(0.18)
        unopened_seed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        assert unopened_seed == before_seed, (before_seed, unopened_seed)
        assert app.node_space_top_batch_status("space_w").get("pending")
        pending = app.vocab_leaderboard_response_cache_row(80, "user001", "space_w")
        assert pending.get("pending"), pending
        pending_payload = json.loads(pending["bytes"].decode("utf-8"))
        assert pending_payload["boards"]["total"][0]["score"] == 10

        published = wait_for_publish("space_w")
        refreshed = app.vocab_leaderboard_response_cache_row(80, "user001", "space_w")
        refreshed_payload = json.loads(refreshed["bytes"].decode("utf-8"))
        after_seed = int(app.VOCAB_LEADERBOARD_RUNTIME_METRICS.get("response_seed_count", 0) or 0)
        assert refreshed_payload["boards"]["total"][0]["score"] == 30
        assert after_seed - before_seed == 1, (before_seed, after_seed)
        assert published["revision"] == published["published_revision"], published
        assert sum(1 for thread in app.threading.enumerate() if thread.name == "node-space-top-batch") == 1
        json.dumps(app.leaderboard_runtime_metrics_snapshot())
    finally:
        app.load_space_leaderboard_activity_state = original_loader
        app.server_database_is_test_user = original_is_test
        app.VOCAB_NODE_TOP_BATCH_QUIET_SECONDS = original_quiet
        app.VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS = original_max_wait
        app.invalidate_vocab_leaderboard_response_cache("space_w")

    print("node_space_top_bounded_debounce=ok dirty=20 unopened_builds=0 builds=1 worker=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
