"""Live watcher regression for portable Space identity and replica quarantine."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.assign_space_lesson_ids import encode_payload
from future_lesson_identity import generate_future_lesson_id


SERVER_DATA_ROOT = Path(r"C:\server data")
COMMON_ROOT = SERVER_DATA_ROOT / "common"
DATABASE = SERVER_DATA_ROOT / "server2.db"
BASE = "http://127.0.0.1:8877"


def relative(path: Path) -> str:
    return path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()


def atomic_space(path: Path, lesson_id: str, word: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        encode_payload({
            "kind": "future_vocabulary_payload",
            "lesson_id": lesson_id,
            "words": [{"word": word}],
        }) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def identity_row(path: Path) -> tuple[str, int, str] | None:
    rel = relative(path)
    connection = sqlite3.connect(DATABASE, timeout=10.0)
    try:
        row = connection.execute(
            "SELECT a.file_id,a.active,COALESCE(r.status,'') FROM lesson_file_aliases a "
            "LEFT JOIN lesson_file_replicas r ON r.normalized_path=a.normalized_path "
            "WHERE a.normalized_path=? COLLATE NOCASE",
            (rel,),
        ).fetchone()
        return (str(row[0]), int(row[1]), str(row[2])) if row else None
    finally:
        connection.close()


def wait_identity(path: Path, file_id: str, active: int = 1, status: str = "active", timeout: float = 20.0) -> tuple[str, int, str]:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = identity_row(path)
        if last == (file_id, active, status):
            return last
        time.sleep(0.2)
    raise AssertionError(f"Identity did not settle for {path}: expected {(file_id, active, status)}, received {last}")


def listening_pid() -> int:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and int(connection.laddr.port) == 8877:
            return int(connection.pid or 0)
    return 0


def wait_health(timeout: float = 45.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{BASE}/health?view=dashboard-v1", timeout=2).status_code == 200:
                return listening_pid()
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Server 2 did not become ready.")


def hard_restart() -> tuple[int, int]:
    before = listening_pid()
    if before:
        psutil.Process(before).kill()
        psutil.Process(before).wait(timeout=10)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=str(ROOT),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return before, wait_health()


def cleanup(prefixes: list[Path], file_ids: set[str]) -> None:
    common = COMMON_ROOT.resolve()
    for target in sorted(set(prefixes), key=lambda item: len(str(item)), reverse=True):
        try:
            resolved = target.resolve()
            resolved.relative_to(common)
        except Exception:
            continue
        if target.name.lower().startswith("codexidentity") and target.exists():
            shutil.rmtree(target)
    try:
        requests.post(
            f"{BASE}/server-data/manifest-refresh",
            json={"paths": [relative(path) for path in prefixes]},
            timeout=120,
        ).raise_for_status()
    except Exception:
        pass
    # Let coalesced native-watch delete events finish before removing the test IDs, or a late callback can recreate them.
    time.sleep(3.0)
    connection = sqlite3.connect(DATABASE, timeout=30.0)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        for file_id in file_ids:
            connection.execute("DELETE FROM lesson_files WHERE file_id=?", (file_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# Added 2026-07-21: exercise real watcher identity transitions without retaining disposable lessons.
def main() -> int:
    token = uuid.uuid4().hex[:10]
    start_root = COMMON_ROOT / f"codexidentity-{token}"
    renamed_root = COMMON_ROOT / f"codexidentity-renamed-{token}"
    destination_root = COMMON_ROOT / f"codexidentity-destination-{token}"
    copied_root = COMMON_ROOT / f"codexidentity-copy-{token}"
    cleanup_paths = [start_root, renamed_root, destination_root, copied_root]
    lesson_id = generate_future_lesson_id()
    independent_id = generate_future_lesson_id({lesson_id})
    same_name_id = generate_future_lesson_id({lesson_id, independent_id})
    file_ids = {lesson_id, independent_id, same_name_id}
    restart_pair = (0, 0)
    try:
        original = start_root / "Original.Space_V"
        atomic_space(original, lesson_id, "alpha")
        wait_identity(original, lesson_id)

        renamed_file = start_root / "Renamed.Space_V"
        original.rename(renamed_file)
        wait_identity(renamed_file, lesson_id)
        old_row = identity_row(original)
        assert old_row and old_row[0] == lesson_id

        start_root.rename(renamed_root)
        renamed_file = renamed_root / "Renamed.Space_V"
        wait_identity(renamed_file, lesson_id)

        destination_root.mkdir(parents=True)
        moved_space = destination_root / "MovedSpace"
        renamed_root.rename(moved_space)
        wait_identity(moved_space / "Renamed.Space_V", lesson_id)

        shutil.copytree(moved_space, copied_root)
        copied_lesson = copied_root / "Renamed.Space_V"
        wait_identity(copied_lesson, lesson_id)

        exact_replica = copied_root / "Exact Replica.Space_V"
        shutil.copy2(copied_lesson, exact_replica)
        wait_identity(exact_replica, lesson_id)

        independent = copied_root / "Independent.Space_V"
        atomic_space(independent, independent_id, "alpha")
        wait_identity(independent, independent_id)

        same_name = destination_root / "Same Name" / "Independent.Space_V"
        atomic_space(same_name, same_name_id, "beta")
        wait_identity(same_name, same_name_id)

        atomic_space(exact_replica, lesson_id, "diverged")
        wait_identity(exact_replica, lesson_id, active=0, status="collision")
        assert wait_identity(copied_lesson, lesson_id) == (lesson_id, 1, "active")

        restart_pair = hard_restart()
        wait_identity(copied_lesson, lesson_id)
        wait_identity(exact_replica, lesson_id, active=0, status="collision")
        connection = sqlite3.connect(DATABASE, timeout=30.0)
        try:
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert int(connection.execute("PRAGMA synchronous").fetchone()[0]) == 2
        finally:
            connection.close()
    finally:
        if not listening_pid():
            hard_restart()
        cleanup(cleanup_paths, file_ids)

    print(
        "lesson_identity_live_matrix=ok rename_file=true rename_folder=true move_space=true "
        "copy_replica=true identical_independent=true same_name_independent=true divergence=quarantined "
        f"hard_restart={restart_pair[0]}->{restart_pair[1]} cleanup=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
