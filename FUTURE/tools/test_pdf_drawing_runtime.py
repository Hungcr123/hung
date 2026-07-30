"""Exercise PDF drawing idempotency, concurrency, stale ordering, and tombstones over HTTP."""

from __future__ import annotations

import concurrent.futures
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
USER = "codexload100"
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-restart", action="store_true")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active test only")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    path = next(
        str(entry.get("path"))
        for entries in (manifest.get("folders") or {}).values()
        for entry in entries if isinstance(entries, list) and isinstance(entry, dict)
        if str(entry.get("path", "")).lower().startswith("common/") and str(entry.get("path", "")).lower().endswith(".pdf")
    )
    login = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=30)
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    identity = "pdf-drawing-runtime-test"
    page = 7
    base_time = datetime.now(timezone.utc).replace(microsecond=0)

    def vector(offset: int) -> dict:
        return {
            "version": 2,
            "width": 10000,
            "height": 10000,
            "items": [{"kind": "pen", "color": "#123456", "width": 12, "points": [{"x": offset, "y": 100}, {"x": offset + 50, "y": 200}]}],
        }

    def vector_many(offset: int, count: int) -> dict:
        return {
            "version": 2,
            "width": 10000,
            "height": 10000,
            "items": [vector(offset + index * 100)["items"][0] for index in range(count)],
        }

    def save(
        operation: str,
        stamp: datetime,
        offset: int = 0,
        action: str = "",
        payload_vector: dict | None = None,
        base_revision: int | None = None,
    ) -> dict:
        payload = {
            "path": path,
            "identity": identity,
            "title": "PDF drawing runtime test",
            "mode": "pdf",
            "page": page,
            "operationId": operation,
            "clientUpdatedAt": stamp.isoformat().replace("+00:00", "Z"),
        }
        if action:
            payload["action"] = action
        else:
            payload["vector"] = payload_vector or vector(offset)
        if base_revision is not None:
            payload["baseRevision"] = base_revision
        response = requests.post(f"{BASE}/space-pdf/drawing", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["drawing"]

    def read() -> dict:
        response = requests.get(
            f"{BASE}/space-pdf/drawing",
            headers=headers,
            params={"path": path, "identity": identity, "page": page},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["drawing"]

    if args.verify_restart:
        before = read()
        stale = save("runtime-post-restart-stale", datetime(2000, 1, 1, tzinfo=timezone.utc), 999, base_revision=6)
        after = read()
        assert before.get("deleted") and before.get("serverRevision") == 7
        assert stale.get("stale") and stale.get("conflict") and stale.get("deleted") and stale.get("serverRevision") == 7
        assert after.get("deleted") and after.get("serverRevision") == 7
        print("pdf_drawing_restart=ok tombstone_revision=7 stale_rejected=true")
        return 0

    initial = save("runtime-initial", base_time, 100, base_revision=0)
    replay = save("runtime-initial", base_time, 100, base_revision=0)
    stale = save("runtime-stale", base_time - timedelta(days=1), 200)
    assert initial["serverRevision"] == replay["serverRevision"] == stale["serverRevision"] == 1
    assert replay["changed"] is False and stale["stale"] is True

    concurrent_time = base_time + timedelta(seconds=1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_rows = list(pool.map(lambda row: save(row[0], concurrent_time, row[1], base_revision=1), (("runtime-b", 300), ("runtime-c", 500))))
    merged = read()
    assert len((merged.get("vector") or {}).get("items") or []) == 3, merged
    assert merged["serverRevision"] == 3, (concurrent_rows, merged)

    longer_snapshot = save(
        "runtime-longer-snapshot",
        base_time + timedelta(seconds=2),
        payload_vector=vector_many(900, 4),
        base_revision=1,
    )
    assert longer_snapshot["serverRevision"] == 4
    assert len((read().get("vector") or {}).get("items") or []) == 7

    stale_clear = save("runtime-stale-clear", base_time, action="clear", base_revision=1)
    assert stale_clear["stale"] is True and stale_clear["conflict"] is True and read()["serverRevision"] == 4
    cleared = save("runtime-clear", base_time + timedelta(seconds=3), action="clear", base_revision=4)
    cleared_read = read()
    assert cleared["deleted"] is True and cleared["serverRevision"] == 5
    assert cleared_read["deleted"] is True and not (cleared_read.get("vector") or {}).get("items")
    stale_after_clear = save("runtime-after-clear-stale", concurrent_time, 900, base_revision=4)
    assert stale_after_clear["stale"] is True and stale_after_clear["conflict"] is True and stale_after_clear["deleted"] is True
    restored = save("runtime-restored", base_time + timedelta(seconds=4), 700, base_revision=5)
    assert restored["serverRevision"] == 6 and len((restored.get("vector") or {}).get("items") or []) == 1
    final_clear = save("runtime-final-clear", base_time + timedelta(seconds=5), action="clear", base_revision=6)
    assert final_clear["deleted"] is True and final_clear["serverRevision"] == 7
    print("pdf_drawing_runtime=ok replay=noop concurrent=merged longer_snapshot=no_loss stale=reject tombstone=durable newer=restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
