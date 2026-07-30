"""Hard-stop Server 2, restore the exact chat document row from a SQLite backup, and restart."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
ROOT = Path(__file__).parents[2]
DATABASE = Path(r"C:\server data\server2.db")
CHAT_PATH = r"C:\QMLearn\users\_future_chat_messages.json"


def wait_health(old_pid: int, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = requests.get(f"{BASE}/health", timeout=2).json()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) != old_pid:
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not restart after chat restore")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    old_pid = int(requests.get(f"{BASE}/health", timeout=10).json().get("pid", 0) or 0)
    psutil.Process(old_pid).kill()
    psutil.Process(old_pid).wait(timeout=15)

    backup = sqlite3.connect(args.backup)
    row = backup.execute("SELECT * FROM documents WHERE lower(path)=lower(?)", (CHAT_PATH,)).fetchone()
    columns = [item[1] for item in backup.execute("PRAGMA table_info(documents)")]
    backup.close()
    if row is None:
        raise RuntimeError("Backup chat document is missing")
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("DELETE FROM documents WHERE lower(path)=lower(?)", (CHAT_PATH,))
    connection.execute(
        f"INSERT INTO documents ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        row,
    )
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(FULL)")
    connection.close()

    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    health = wait_health(old_pid)
    print({"chat_restore": "ok", "old_pid": old_pid, "new_pid": health.get("pid")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
