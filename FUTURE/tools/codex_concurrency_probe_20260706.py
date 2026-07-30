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


ROOT = Path(r"C:\server data")
QROOT = Path(r"C:\QMLearn\users")
RUN_ID = f"{int(time.time())}{os.getpid()}"
USER_PREFIX = f"codexburst{RUN_ID}"
CODEX_RE = re.compile(r"\bcodexburst[0-9a-z_-]*", re.I)

SAMPLES = {
    "space_w": ROOT / r"common\Giao tiếp hàng ngày\Chào hỏi 10 câu.Space_W",
    "space_q": ROOT / r"common\Giao tiếp hàng ngày\So_dem_tieng_Anh_50_bai_tap.Space_Q",
    "space_p": ROOT / r"common\Space\Empower A1\Unit 1\Empower_A2_U1_Learning_English.Space_P",
}


def copy_sample(username: str, board: str) -> str:
    source = SAMPLES[board]
    target_dir = ROOT / username
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{board}{source.suffix}"
    shutil.copy2(source, target)
    return app.server_data_relative(target)


def progress_file(username: str, board: str) -> Path:
    names = {
        "space_w": "_future_space_w_progress.json",
        "space_q": "_future_space_q_progress.json",
        "space_p": "_future_space_p_progress.json",
    }
    return QROOT / username / names[board]


def progress_payload(username: str, board: str, rel_path: str, idx: int) -> dict:
    total = 10 if board == "space_w" else (50 if board == "space_q" else 23)
    state = {
        "title": board,
        "nodeCount": total,
        "savedAt": app.utc_timestamp(),
        "activeRun": True,
    }
    if board == "space_q":
        state.update({"questionTotal": total, "questionDone": min(total, 1 + idx % total)})
    elif board == "space_p":
        state.update({"totalSegments": total, "completedSegments": min(total, 1 + idx % total), "space": "Space_P"})
    else:
        state.update({"index": min(total, 1 + idx % total)})
    return {
        "path": rel_path,
        "identity": rel_path,
        "title": board,
        "nodeIndex": min(total, 1 + idx % total),
        "nodeCount": total,
        "savedAt": state["savedAt"],
        "state": state,
    }


def setup_users(kind: str, board: str, count: int) -> list[tuple[str, str]]:
    rows = []
    for idx in range(count):
        username = f"{USER_PREFIX}{kind}{idx:03d}"
        rows.append((username, copy_sample(username, board)))
    return rows


def complete_one(row: tuple[int, str, str], board: str) -> dict:
    idx, username, rel_path = row
    started = time.perf_counter()
    result = app.record_lesson_completion(rel_path, username, {"source": board, "title": board, "nodes": 25})
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    file_ok = progress_file(username, board).is_file()
    return {
        "user": username,
        "ok": True,
        "ms": elapsed_ms,
        "file_ok": file_ok,
        "timing": result.get("timing_ms", {}) if isinstance(result, dict) else {},
    }


def save_progress_one(row: tuple[int, str, str], board: str) -> dict:
    idx, username, rel_path = row
    payload = progress_payload(username, board, rel_path, idx)
    started = time.perf_counter()
    if board == "space_w":
        record = app.save_space_w_progress(username, payload)
    elif board == "space_q":
        record = app.save_space_q_progress(username, payload)
    else:
        record = app.save_space_p_progress(username, payload)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "user": username,
        "ok": True,
        "ms": elapsed_ms,
        "file_ok": progress_file(username, board).is_file(),
        "record_path": record.get("path") if isinstance(record, dict) else "",
    }


def list_only_one(row: tuple[int, str, str], board: str) -> dict:
    _idx, username, _rel_path = row
    started = time.perf_counter()
    listing = app.list_server_data(username, username=username, admin=False, fresh=False, lightweight=False)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "user": username,
        "ok": True,
        "ms": elapsed_ms,
        "file_ok": progress_file(username, board).is_file(),
        "entries": len(listing.get("entries", [])) if isinstance(listing, dict) else 0,
    }


def back_one(row: tuple[int, str, str], board: str) -> dict:
    saved = save_progress_one(row, board)
    started = time.perf_counter()
    listing = app.list_server_data(row[1], username=row[1], admin=False, fresh=False, lightweight=False)
    saved["list_ms"] = int((time.perf_counter() - started) * 1000)
    saved["ms"] = int(saved.get("ms", 0) or 0) + int(saved["list_ms"])
    saved["entries"] = len(listing.get("entries", [])) if isinstance(listing, dict) else 0
    return saved


def run_group(label: str, fn, board: str, count: int = 100, workers: int = 20) -> dict:
    setup_started = time.perf_counter()
    kind = "c" if label.startswith("complete") else "b"
    prepared = [(idx, username, rel_path) for idx, (username, rel_path) in enumerate(setup_users(kind, board, count))]
    setup_ms = int((time.perf_counter() - setup_started) * 1000)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    rows = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fn, row, board) for row in prepared]
        for future in concurrent.futures.as_completed(futures):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append(str(exc))
    wall_ms = int((time.perf_counter() - started_wall) * 1000)
    cpu_ms = int((time.process_time() - started_cpu) * 1000)
    times = sorted(int(row.get("ms", 0) or 0) for row in rows)
    save_times = sorted(int(row.get("save_ms", row.get("ms", 0)) or 0) for row in rows)
    list_times = sorted(int(row.get("list_ms", 0) or 0) for row in rows if "list_ms" in row)
    return {
        "label": label,
        "board": board,
        "count": count,
        "workers": workers,
        "ok": len(rows),
        "errors": errors[:5],
        "file_ok": sum(1 for row in rows if row.get("file_ok")),
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "setup_ms": setup_ms,
        "per_request_ms": percentile_summary(times),
        "save_ms": percentile_summary(save_times),
        "list_ms": percentile_summary(list_times),
    }


def percentile_summary(values: list[int]) -> dict:
    if not values:
        return {}
    def pick(percent: float) -> int:
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * percent))))
        return values[index]
    return {
        "min": values[0],
        "p50": pick(0.50),
        "p90": pick(0.90),
        "p99": pick(0.99),
        "max": values[-1],
    }


def is_codexburst(value) -> bool:
    return isinstance(value, str) and bool(CODEX_RE.search(value))


def scrub_codexburst(obj):
    removed = 0
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if is_codexburst(key):
                removed += 1
                continue
            if isinstance(value, dict) and any(is_codexburst(value.get(k)) for k in ("user", "username", "path", "effective_path")):
                removed += 1
                continue
            next_value, count = scrub_codexburst(value)
            removed += count
            out[key] = next_value
        return out, removed
    if isinstance(obj, list):
        out = []
        for value in obj:
            if is_codexburst(value):
                removed += 1
                continue
            if isinstance(value, dict) and any(is_codexburst(value.get(k)) for k in ("user", "username", "path", "effective_path")):
                removed += 1
                continue
            next_value, count = scrub_codexburst(value)
            removed += count
            out.append(next_value)
        return out, removed
    return obj, 0


def cleanup() -> dict:
    removed_paths = 0
    for root in (ROOT, QROOT):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.name.lower().startswith("codexburst"):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                removed_paths += 1
    state_files = [
        ROOT / "_future_vocab_leaderboard_ranks.json",
        ROOT / "_future_vocab_leaderboard_periods.json",
        ROOT / "_future_vocab_leaderboard_reward_claims.json",
        ROOT / "_future_vocab_leaderboard_viewers.json",
        ROOT / "_future_vocab_leaderboard_npc_top.json",
        ROOT / "space_leaderboard_activity.json",
    ]
    removed_state = {}
    for file in state_files:
        if not file.is_file():
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8-sig") or "{}")
            new_data, count = scrub_codexburst(data)
            if count:
                file.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            removed_state[str(file)] = count
        except Exception as exc:
            removed_state[str(file)] = f"error:{exc}"
    return {"paths": removed_paths, "state": removed_state}


def main() -> None:
    results = []
    try:
        args = sys.argv[1:]
        if args and args[0] == "cleanup":
            print(json.dumps({"cleanup": cleanup()}, ensure_ascii=False, indent=2))
            return
        groups = args or [
            "complete:space_w",
            "complete:space_q",
            "complete:space_p",
            "back:space_w",
            "back:space_q",
            "back:space_p",
        ]
        for group in groups:
            kind, board = group.split(":", 1)
            if kind == "complete":
                results.append(run_group("complete-100", complete_one, board))
            elif kind == "back":
                results.append(run_group("back-100-save-plus-list", back_one, board))
            elif kind == "save":
                results.append(run_group("save-100", save_progress_one, board))
            elif kind == "list":
                results.append(run_group("list-100", list_only_one, board))
    finally:
        app.flush_space_progress_store(True)
        cleanup_result = cleanup()
    print(json.dumps({"run_id": RUN_ID, "results": results, "cleanup": cleanup_result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
