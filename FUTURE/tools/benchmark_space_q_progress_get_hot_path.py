"""Benchmark Space_Q progress reads with 100 users and real `hung` state."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import sqlite3
import time
from pathlib import Path

import requests

import benchmark_space_v_progress_get_hot_path as common


BASE = common.BASE
DATABASE = common.DATABASE
SERVER_DATA = common.SERVER_DATA
USERS = common.USERS


def lesson_paths() -> list[str]:
    rows = []
    for path in (SERVER_DATA / "common").rglob("*.Space_Q"):
        try:
            if int(path.stat().st_size) < 128:
                continue
        except OSError:
            continue
        rows.append(path.relative_to(SERVER_DATA).as_posix())
        if len(rows) >= len(USERS):
            return rows
    if not rows:
        raise RuntimeError("No Space_Q files were found")
    return [rows[index % len(rows)] for index in range(len(USERS))]


def hung_rows() -> list[tuple[str, str]]:
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT path,identity FROM lesson_progress WHERE username='hung' AND space='Space_Q' ORDER BY updated_at_utc DESC"
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise RuntimeError("Real user hung has no Space_Q progress rows")
    return [(common.clean(path), common.clean(identity)) for path, identity in rows if common.clean(path)]


def seed_record() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT record_json FROM lesson_progress WHERE username='hung' AND space='Space_Q' ORDER BY length(record_json) DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("No seed Space_Q record exists")
    return json.loads(row[0])


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = common.server_process()
    paths = lesson_paths()
    real_rows = hung_rows()
    template = seed_record()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return common.clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")

    def seed(index: int) -> None:
        record = copy.deepcopy(template)
        path = paths[index]
        saved_at = f"2026-07-20T02:{index % 50:02d}:00Z"
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        state.update({"savedAt": saved_at, "runId": f"codex-space-q-run-{index:03d}", "activeRun": True})
        record.update({
            "action": "autosave",
            "path": path,
            "identity": f"codex-space-q-get-{index:03d}",
            "title": Path(path).stem,
            "savedAt": saved_at,
            "runId": state["runId"],
            "activeRun": True,
            "state": state,
        })
        response = requests.post(
            f"{BASE}/space-q/progress?client_source=codex_get_seed",
            headers={"Authorization": f"Bearer {tokens[USERS[index]]}"},
            json=record,
            timeout=45,
        )
        response.raise_for_status()

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        list(pool.map(seed, range(100)))
    common.wait_for_writer_quiescence()

    def get_one(index: int, etag: str = "") -> tuple:
        headers = {"Authorization": f"Bearer {tokens[USERS[index]]}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-q/progress",
            headers=headers,
            params={"path": paths[index], "identity": f"codex-space-q-get-{index:03d}"},
            timeout=30,
        )
        payload = response.json() if response.content else {}
        return (time.perf_counter() - started) * 1000, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), common.clean(response.headers.get("ETag"))

    def get_hung(index: int, etag: str = "") -> tuple:
        path, identity = real_rows[index % len(real_rows)]
        headers = {"Authorization": f"Bearer {hung_token}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-q/progress",
            headers=headers,
            params={"path": path, "identity": identity},
            timeout=30,
        )
        payload = response.json() if response.content else {}
        return (time.perf_counter() - started) * 1000, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), common.clean(response.headers.get("ETag"))

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        _, phases["distinct_users_first"] = common.measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_rows, phases["distinct_users_warm"] = common.measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_etags = [row[4] for row in distinct_rows]
        distinct_conditional, phases["distinct_users_conditional"] = common.measured(
            process, lambda: list(pool.map(lambda index: get_one(index, distinct_etags[index]), range(100)))
        )
        hung_result, phases["hung_realistic"] = common.measured(process, lambda: list(pool.map(get_hung, range(100))))
        hung_etags = [row[4] for row in hung_result]
        hung_conditional, phases["hung_conditional"] = common.measured(
            process, lambda: list(pool.map(lambda index: get_hung(index, hung_etags[index]), range(100)))
        )
    if any(row[1] != 304 for row in distinct_conditional + hung_conditional):
        raise RuntimeError("One or more Space_Q conditional reads did not return 304")
    if any(not row[3] for row in hung_result):
        raise RuntimeError("One or more real hung Space_Q rows did not resolve")
    print(json.dumps({"space_q_progress_get_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
