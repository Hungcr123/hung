"""Benchmark shared Space_P/L/S progress reads with 100 users and real hung state."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

import benchmark_space_v_progress_get_hot_path as common
import benchmark_space_p_progress_post_hot_path as paragraph_post


BASE = common.BASE
USERS = common.USERS


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = common.server_process()
    lessons = paragraph_post.lesson_rows()
    template = paragraph_post.seed_record()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return common.clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")
    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    def seed(index: int) -> None:
        path, space = lessons[index]
        record = copy.deepcopy(template)
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        saved_at = (base_time + timedelta(seconds=index)).isoformat().replace("+00:00", "Z")
        total = max(2, int(state.get("totalSegments") or 12))
        state.update({
            "savedAt": saved_at,
            "runId": f"codex-space-p-get-run-{index:03d}",
            "activeRun": True,
            "space": space,
            "spaceMode": space.lower(),
            "completedSegments": index % 5,
            "totalSegments": total,
            "syncOperationId": f"codex-space-p-get-operation-{index:03d}-{saved_at}",
            "complete": False,
            "lessonComplete": False,
        })
        record.update({
            "action": "autosave",
            "path": path,
            "identity": f"codex-space-p-get-{index:03d}",
            "space": space,
            "title": Path(path).stem,
            "nodeIndex": index % 5,
            "nodeCount": total,
            "savedAt": saved_at,
            "runId": state["runId"],
            "activeRun": True,
            "syncOperationId": state["syncOperationId"],
            "complete": False,
            "lessonComplete": False,
            "state": state,
        })
        response = requests.post(
            f"{BASE}/space-p/progress?client_source=codex_get_seed&response=compact-v1",
            headers={"Authorization": f"Bearer {tokens[USERS[index]]}"},
            json=record,
            timeout=45,
        )
        response.raise_for_status()

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        list(pool.map(seed, range(100)))
    common.wait_for_writer_quiescence()
    time.sleep(0.5)

    def get_one(index: int, etag: str = "") -> tuple:
        path, _space = lessons[index]
        headers = {"Authorization": f"Bearer {tokens[USERS[index]]}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-p/progress",
            headers=headers,
            params={"path": path, "identity": f"codex-space-p-get-{index:03d}"},
            timeout=30,
        )
        payload = response.json() if response.content else {}
        return ((time.perf_counter() - started) * 1000, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), common.clean(response.headers.get("ETag")))

    real_rows = paragraph_post.hung_rows()
    def get_hung(index: int, etag: str = "") -> tuple:
        path, identity = real_rows[index % len(real_rows)]
        headers = {"Authorization": f"Bearer {hung_token}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-p/progress",
            headers=headers,
            params={"path": path, "identity": identity},
            timeout=30,
        )
        payload = response.json() if response.content else {}
        return ((time.perf_counter() - started) * 1000, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), common.clean(response.headers.get("ETag")))

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        _, phases["distinct_users_first"] = common.measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_rows, phases["distinct_users_warm"] = common.measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_etags = [row[4] for row in distinct_rows]
        distinct_conditional, phases["distinct_users_conditional"] = common.measured(
            process, lambda: list(pool.map(lambda index: get_one(index, distinct_etags[index]), range(100)))
        )
        hung_rows, phases["hung_realistic"] = common.measured(process, lambda: list(pool.map(get_hung, range(100))))
        hung_etags = [row[4] for row in hung_rows]
        hung_conditional, phases["hung_conditional"] = common.measured(
            process, lambda: list(pool.map(lambda index: get_hung(index, hung_etags[index]), range(100)))
        )
    phases["distinct_users_conditional"]["actual_304"] = sum(1 for row in distinct_conditional if row[1] == 304)
    phases["hung_conditional"]["actual_304"] = sum(1 for row in hung_conditional if row[1] == 304)
    if phases["distinct_users_conditional"]["actual_304"] != 100 or phases["hung_conditional"]["actual_304"] != 100:
        raise RuntimeError("One or more paragraph conditional reads did not return 304")
    if any(not row[3] for row in hung_rows):
        raise RuntimeError("One or more real hung paragraph rows did not resolve")
    if any(phase["sqlite_writer"]["tasks"] for phase in phases.values()):
        raise RuntimeError("Paragraph GET created SQLite writer tasks")
    print(json.dumps({"space_p_progress_get_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
