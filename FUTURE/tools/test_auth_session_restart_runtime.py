"""Verify auth-session ACK durability, replacement, and restart rejection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
ROOT = Path(__file__).parents[2]
USER = "codexload100"


def health(timeout: float = 3.0) -> dict:
    return requests.get(f"{BASE}/health", timeout=timeout).json()


def start_server(old_pid: int) -> dict:
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + 50.0
    while time.monotonic() < deadline:
        try:
            payload = health()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) not in {0, old_pid}:
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not recover during auth-session restart test")


def hard_restart() -> tuple[int, int]:
    old_pid = int(health().get("pid", 0) or 0)
    process = psutil.Process(old_pid)
    process.kill()
    process.wait(timeout=15)
    restarted = start_server(old_pid)
    return old_pid, int(restarted.get("pid", 0) or 0)


def login(password: str) -> str:
    response = requests.post(
        f"{BASE}/auth/login",
        json={"username": USER, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError("Login returned no auth token")
    return token


def auth_me(token: str) -> requests.Response:
    return requests.get(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )


def require_current(token: str) -> None:
    response = auth_me(token)
    if response.status_code != 200 or str(response.json().get("username") or "").lower() != USER:
        raise RuntimeError(f"Current token failed: status={response.status_code}")


def require_rejected(token: str) -> None:
    response = auth_me(token)
    if response.status_code == 200:
        raise RuntimeError("Replaced token remained valid")


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime test only")

    first = login(password)
    first_old_pid, first_new_pid = hard_restart()
    require_current(first)

    second = login(password)
    if second == first:
        raise RuntimeError("Replacement login reused the previous token")
    require_rejected(first)
    require_current(second)

    second_old_pid, second_new_pid = hard_restart()
    require_rejected(first)
    require_current(second)

    print(json.dumps({
        "auth_session_restart": "ok",
        "ack_survived_hard_kill": True,
        "replacement_rejected_before_restart": True,
        "replacement_rejected_after_restart": True,
        "current_token_survived_restart": True,
        "pids": [first_old_pid, first_new_pid, second_old_pid, second_new_pid],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
