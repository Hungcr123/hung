"""Runtime proof that compound vocabulary/progress writes invalidate progress caches."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "codexload001"
    key = f"generation-write-{uuid.uuid4().hex}"
    before = app.server_database_user_generation("progress", username)
    record = {
        "key": key,
        "path": "common/File 02 - {7}.Space_V",
        "identity": "ftg-lesson-000002312",
        "lesson_id": "ftg-lesson-000002312",
        "nodeIndex": 0,
        "nodeCount": 10,
        "learnedCount": 0,
        "updatedAt": app.utc_timestamp(),
        "state": {"runId": f"generation-{uuid.uuid4().hex}", "nodeIndex": 0, "nodeCount": 10},
    }
    try:
        app.server_database_record_vocabulary_transaction(
            username,
            [],
            record["path"],
            False,
            record["updatedAt"],
            {},
            record_period_activity=False,
            progress_record=record,
        )
        after = app.server_database_user_generation("progress", username)
        assert after > before, (before, after)
        payload = app.server_database_load_progress_payload("Space_V", username) or {}
        assert key in (payload.get("states") or {})
    finally:
        app.server_database_apply_progress_entry("Space_V", username, {"op": "remove", "key": key})
    print("progress_generation_write_paths=ok vocabulary_transaction=true durable_progress=true invalidated=true cleanup=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
