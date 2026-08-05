from __future__ import annotations

import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    now = time.time()
    with app.DISTRIBUTED_WORKER_CONDITION:
        app.DISTRIBUTED_WORKERS.clear()
        app.DISTRIBUTED_WORKER_JOBS.clear()
        app.DISTRIBUTED_WORKER_QUEUE.clear()
        worker_id = "contract-worker"
        app.DISTRIBUTED_WORKERS[worker_id] = {
            "worker_id": worker_id,
            "name": "Contract Worker",
            "status": "online",
            "capabilities": ["tts"],
            "max_jobs_by_kind": {"tts": 2},
            "last_seen": now,
            "active_jobs": {"tts": ["bulk", "interactive"]},
        }
        app.DISTRIBUTED_WORKER_JOBS.update({
            "bulk": {
                "job_id": "bulk",
                "kind": "tts",
                "priority": 3,
                "status": "queued",
                "created_at": now - 10,
            },
            "interactive": {
                "job_id": "interactive",
                "kind": "tts",
                "priority": 1,
                "status": "claimed",
                "worker_id": worker_id,
                "claimed_at": now - 70,
                "lease_seconds": 60,
                "attempts": 1,
                "attempts_by_worker": {},
                "failed_workers": [],
                "created_at": now,
            },
        })
        app.DISTRIBUTED_WORKER_QUEUE.extend(["bulk"])
        app.distributed_worker_prune_locked(now)
        assert app.DISTRIBUTED_WORKER_JOBS["interactive"]["status"] == "queued"
        assert app.DISTRIBUTED_WORKER_QUEUE[0] == "interactive"
        assert app.DISTRIBUTED_WORKERS[worker_id]["lease_failures"] == 1

        retry = app.DISTRIBUTED_WORKER_JOBS["interactive"]
        retry.update({"status": "claimed", "worker_id": worker_id, "claimed_at": now - 70})
        app.DISTRIBUTED_WORKERS[worker_id]["active_jobs"] = {"tts": ["interactive"]}
        app.distributed_worker_prune_locked(now)
        assert app.DISTRIBUTED_WORKERS[worker_id]["quarantine_until"] > now
        assert worker_id not in {
            row.get("worker_id")
            for row in app.distributed_worker_available_locked("tts", "", {"voice": "sot:en-US"})
        }

    print("distributed worker LAN broker contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
