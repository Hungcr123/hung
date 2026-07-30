"""Prepare or clean the codexload099 multi-folder/type Space Task DOM fixture."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
USERNAME = "codexload099"
SERVER_DATA = Path(r"C:\server data")

PATHS = [
    "common/Ngữ pháp/Ngữ pháp/Thì hiện tại đơn/Bài tập/Writing - Lan's Good Habits.Space_W",
    "common/Daily Skills 115-125/Speaking Space_S - Successful Student.Space_S",
    "common/PDF/Destination/Destination B1 Grammar and Vocabulary with Answer key.space_pdf",
    "common/Space/Empower A1/Unit 1/Empower_A2_U1_Studying_English.Space_L",
    "common/Ngữ pháp/Ngữ pháp/Thì hiện tại đơn/Bài tập/Listening - Nam's Daily Routine.Space_Q",
    "common/PDF/Global Sucess/Sách lớp 2.space_pdf",
    "common/Daily Skills 115-125/Writing - Lan's Good Habits.Space_W",
    "common/PDF/Doraemon/Doremon Ep 01.space_pdf",
    "common/Ngữ pháp/Ngữ pháp/Thì hiện tại đơn/Bài tập/Listening Space_L - Nam's Daily Routine.Space_L",
    "common/Space/Empower A1/Unit 1/Empower_A2_U1_Speaking_Practice.Space_S",
    "common/PDF/Destination/Destination B2 Grammar and Vocabulary with Answer key.space_pdf",
    "common/Daily Skills 115-125/Listening - Nam's Daily Routine.Space_Q",
    "common/PDF/Global Sucess/Sách lớp 5 tập 1.space_pdf",
    "common/Ngữ pháp/Ngữ pháp/Thì hiện tại đơn/Bài tập/Speaking Space_S - Successful Student.Space_S",
    "common/Daily Skills 115-125/Listening Space_L - Nam's Daily Routine.Space_L",
    "common/PDF/Doraemon/Doremon Ep 02.space_pdf",
]


def login(password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=30)
    response.raise_for_status()
    return response.json()["token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def tasks(token: str) -> list[dict]:
    response = requests.get(f"{BASE}/lesson-tasks?user={USERNAME}", headers=headers(token), timeout=60)
    response.raise_for_status()
    return response.json().get("tasks", [])


def cleanup(token: str) -> int:
    removed = 0
    while True:
        rows = tasks(token)
        if not rows:
            return removed
        task = rows[0]
        response = requests.post(
            f"{BASE}/lesson-tasks",
            headers=headers(token),
            json={
                "action": "remove",
                "user": USERNAME,
                "id": task.get("id", ""),
                "path": task.get("path", ""),
                "folder_group_key": task.get("folder_group_key", ""),
                "folder_path": task.get("folder_path", ""),
            },
            timeout=60,
        )
        response.raise_for_status()
        removed += int(response.json().get("removed_count", 0) or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "cleanup"))
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this active fixture only")
    token = login(password)
    if args.action == "cleanup":
        print(json.dumps({"cleaned": cleanup(token), "remaining": len(tasks(token))}))
        return 0
    if tasks(token):
        raise RuntimeError(f"{USERNAME} must start empty; run cleanup first")
    missing = [path for path in PATHS if not (SERVER_DATA / Path(path)).is_file()]
    if missing:
        raise RuntimeError(f"Missing fixture files: {missing}")
    for path in PATHS:
        response = requests.post(
            f"{BASE}/lesson-tasks",
            headers=headers(token),
            json={"action": "add", "user": USERNAME, "path": path},
            timeout=60,
        )
        response.raise_for_status()
    rows = tasks(token)
    print(json.dumps({"prepared": len(rows), "paths": [row.get("path") for row in rows]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
