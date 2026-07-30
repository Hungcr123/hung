import concurrent.futures
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import FUTURE.server_app as app

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(r"C:\server data")
QROOT = Path(r"C:\QMLearn\users")
RUN_ID = f"{int(time.time())}{os.getpid()}"
USER_PREFIX = f"codexopen{RUN_ID}"
CODEX_OPEN_RE = re.compile(r"\bcodexopen[0-9a-z_-]*", re.I)

SAMPLES = {
    "space_w": ROOT / r"common\Giao tiếp hàng ngày\Chào hỏi 10 câu.Space_W",
    "space_q": ROOT / r"common\Giao tiếp hàng ngày\So_dem_tieng_Anh_50_bai_tap.Space_Q",
    "space_p": ROOT / r"common\My Daily Life Paragraph Rewrite.Space_P",
    "space_l": ROOT / r"common\Study\Empower A1\space L\unit 9\Empower A1 Unit 9 Page 71 - Getting Started.Space_L",
}


def sample_path(board: str) -> Path:
    target = SAMPLES.get(board)
    if isinstance(target, Path) and target.is_file():
        return target
    suffix = {
        "space_w": ".Space_W",
        "space_q": ".Space_Q",
        "space_p": ".Space_P",
        "space_l": ".Space_L",
    }[board]
    for path in (ROOT / "common").rglob(f"*{suffix}"):
        if path.is_file():
            return path
    raise RuntimeError(f"Khong tim thay file mau cho {board}.")


def percentile_summary(values: list[int]) -> dict:
    if not values:
        return {}

    def pick(percent: float) -> int:
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * percent))))
        return values[index]

    return {"min": values[0], "p50": pick(0.50), "p90": pick(0.90), "p99": pick(0.99), "max": values[-1]}


def prepared_users(count: int = 100) -> list[str]:
    return [f"{USER_PREFIX}{idx:03d}" for idx in range(count)]


def setup_user_folders(users: list[str]) -> None:
    QROOT.mkdir(parents=True, exist_ok=True)
    for username in users:
        (QROOT / username).mkdir(parents=True, exist_ok=True)


def read_progress(board: str, username: str, rel_path: str) -> dict | None:
    if board == "space_w":
        return app.read_space_w_progress(username, rel_path, "")
    if board == "space_q":
        return app.read_space_q_progress(username, rel_path, "")
    return app.read_space_p_progress(username, rel_path, "")


def progress_payload(board: str, username: str, rel_path: str, idx: int) -> dict:
    total = {"space_w": 10, "space_q": 50, "space_p": 23, "space_l": 18}.get(board, 10)
    done = min(total, 1 + idx % max(1, total))
    state = {
        "title": board,
        "nodeCount": total,
        "savedAt": app.utc_timestamp(),
        "activeRun": True,
    }
    if board == "space_q":
        state.update({"questionTotal": total, "questionDone": done})
    elif board in {"space_p", "space_l"}:
        state.update({"totalSegments": total, "completedSegments": done, "space": "Space_L" if board == "space_l" else "Space_P"})
    else:
        state.update({"index": done})
    return {
        "path": rel_path,
        "identity": rel_path,
        "title": board,
        "nodeIndex": done,
        "nodeCount": total,
        "savedAt": state["savedAt"],
        "state": state,
    }


def seed_progress(board: str, users: list[str], target: Path) -> None:
    rel_path = app.server_data_relative(target)
    for idx, username in enumerate(users):
        payload = progress_payload(board, username, rel_path, idx)
        if board == "space_w":
            app.save_space_w_progress(username, payload)
        elif board == "space_q":
            app.save_space_q_progress(username, payload)
        else:
            app.save_space_p_progress(username, payload)
    with app.SPACE_PROGRESS_STORE_LOCK:
        for key in list(app.SPACE_PROGRESS_STORE.keys()):
            if CODEX_OPEN_RE.search(str(key)):
                app.SPACE_PROGRESS_STORE.pop(key, None)


def open_one(board: str, username: str, target: Path) -> dict:
    rel_path = app.server_data_relative(target)
    started = time.perf_counter()
    app.chat_mark_online(username)
    app.mark_user_activity(username, {
        "status": f"Opening {board}",
        "space": board,
        "path": rel_path,
    })
    file_started = time.perf_counter()
    payload = app.cached_server_data_file_bytes(target)
    file_ms = int((time.perf_counter() - file_started) * 1000)
    progress_started = time.perf_counter()
    progress = read_progress(board, username, rel_path)
    progress_ms = int((time.perf_counter() - progress_started) * 1000)
    pref_ms = 0
    if board == "space_w":
        pref_started = time.perf_counter()
        app.read_user_preferences(username)
        pref_ms = int((time.perf_counter() - pref_started) * 1000)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "user": username,
        "ms": elapsed_ms,
        "file_ms": file_ms,
        "progress_ms": progress_ms,
        "pref_ms": pref_ms,
        "bytes": len(payload),
        "has_progress": isinstance(progress, dict),
    }


def run_group(board: str, count: int = 100, workers: int = 32, seeded: bool = False) -> dict:
    target = sample_path(board)
    app.cached_server_data_file_bytes(target)
    users = prepared_users(count)
    setup_user_folders(users)
    if seeded:
        seed_progress(board, users, target)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    rows = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(open_one, board, username, target) for username in users]
        for future in concurrent.futures.as_completed(futures):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append(str(exc))
    wall_ms = int((time.perf_counter() - started_wall) * 1000)
    cpu_ms = int((time.process_time() - started_cpu) * 1000)
    return {
        "board": board,
        "seeded": seeded,
        "sample": str(target),
        "count": count,
        "workers": workers,
        "ok": len(rows),
        "errors": errors[:5],
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "per_request_ms": percentile_summary(sorted(int(row.get("ms", 0) or 0) for row in rows)),
        "file_ms": percentile_summary(sorted(int(row.get("file_ms", 0) or 0) for row in rows)),
        "progress_ms": percentile_summary(sorted(int(row.get("progress_ms", 0) or 0) for row in rows)),
        "pref_ms": percentile_summary(sorted(int(row.get("pref_ms", 0) or 0) for row in rows if int(row.get("pref_ms", 0) or 0))),
        "bytes": rows[0].get("bytes", 0) if rows else 0,
        "has_progress": sum(1 for row in rows if row.get("has_progress")),
    }


def cleanup() -> dict:
    removed_paths = 0
    for root in (ROOT, QROOT):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.name.lower().startswith("codexopen"):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                removed_paths += 1
    with app.USER_ACTIVITY_LOCK:
        for key in list(app.USER_ACTIVITY.keys()):
            if CODEX_OPEN_RE.search(str(key)):
                app.USER_ACTIVITY.pop(key, None)
    with app.CHAT_LOCK:
        for target in (app.CHAT_ONLINE, app.CHAT_ONLINE_FIRST_SEEN):
            for key in list(target.keys()):
                if CODEX_OPEN_RE.search(str(key)):
                    target.pop(key, None)
    with app.SPACE_PROGRESS_STORE_LOCK:
        for key in list(app.SPACE_PROGRESS_STORE.keys()):
            if CODEX_OPEN_RE.search(str(key)):
                app.SPACE_PROGRESS_STORE.pop(key, None)
    return {"paths": removed_paths}


def main() -> None:
    arg = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if arg == "cleanup":
        print(json.dumps({"cleanup": cleanup()}, ensure_ascii=False, indent=2))
        return
    seeded = False
    if arg.endswith(":seeded"):
        seeded = True
        arg = arg.split(":", 1)[0] or "all"
    boards = ["space_w", "space_q", "space_p", "space_l"] if arg == "all" else [arg]
    results = []
    try:
        for board in boards:
            if board not in SAMPLES:
                raise RuntimeError(f"Unknown board: {board}")
            results.append(run_group(board, seeded=seeded))
    finally:
        cleanup_result = cleanup()
    print(json.dumps({"results": results, "cleanup": cleanup_result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
