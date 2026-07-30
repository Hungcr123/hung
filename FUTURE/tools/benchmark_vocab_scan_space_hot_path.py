"""Benchmark vocabulary preflight scans for distributed lessons and real hung traffic."""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from pathlib import Path

import requests

import benchmark_space_v_progress_get_hot_path as common


BASE = common.BASE
SERVER_DATA = common.SERVER_DATA
USERS = common.USERS
EXTENSIONS = ("*.Space_W", "*.Space_Q", "*.Space_P", "*.Space_S", "*.Space_L")
HUNG_PATH = "common/Ngữ pháp/Ngữ pháp/Thì quá khứ đơn/Bài tập/Thì quá khứ đơn - 40 bài tập phân biệt thì.Space_Q"


def lesson_paths() -> list[str]:
    rows = []
    seen = set()
    for pattern in EXTENSIONS:
        for path in (SERVER_DATA / "common").rglob(pattern):
            try:
                if int(path.stat().st_size) < 128:
                    continue
            except OSError:
                continue
            relative = path.relative_to(SERVER_DATA).as_posix()
            if relative.lower() in seen:
                continue
            seen.add(relative.lower())
            rows.append(relative)
            if len(rows) >= len(USERS):
                return rows
    if not rows:
        raise RuntimeError("No supported lesson files were found")
    return [rows[index % len(rows)] for index in range(len(USERS))]


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = common.server_process()
    paths = lesson_paths()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return common.clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")

    def scan(token: str, path: str) -> tuple:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/vocab/scan-space-w?response=compact-v1",
            headers={"Authorization": f"Bearer {token}"},
            json={"path": path},
            timeout=60,
        )
        payload = response.json() if response.content else {}
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            len(response.content),
            response.status_code == 200 and isinstance(payload.get("new_count"), int),
            common.clean(payload.get("error")),
            payload.get("response_schema") == "vocab-scan-compact-v1" and "words" not in payload,
        )

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        distributed_first, phases["distributed_first"] = common.measured(
            process, lambda: list(pool.map(lambda index: scan(tokens[USERS[index]], paths[index]), range(100)))
        )
        distributed_warm, phases["distributed_warm"] = common.measured(
            process, lambda: list(pool.map(lambda index: scan(tokens[USERS[index]], paths[index]), range(100)))
        )
        hung_first, phases["hung_same_lesson_first"] = common.measured(
            process, lambda: list(pool.map(lambda _index: scan(hung_token, HUNG_PATH), range(100)))
        )
        hung_warm, phases["hung_same_lesson_warm"] = common.measured(
            process, lambda: list(pool.map(lambda _index: scan(hung_token, HUNG_PATH), range(100)))
        )
    for name, rows in (
        ("distributed_first", distributed_first),
        ("distributed_warm", distributed_warm),
        ("hung_same_lesson_first", hung_first),
        ("hung_same_lesson_warm", hung_warm),
    ):
        errors = [row[4] for row in rows if row[4]]
        phases[name]["errors"] = {error: errors.count(error) for error in sorted(set(errors))}
        if phases[name].get("statuses") != {"200": 100}:
            raise AssertionError(f"{name} did not return 100 successful responses: {phases[name].get('statuses')}")
        if phases[name].get("progress_rows") != 100:
            raise AssertionError(f"{name} did not return 100 valid progress rows")
        if not all(row[5] for row in rows):
            raise AssertionError(f"{name} returned a non-compact response")
    print(json.dumps({"vocab_scan_space_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
