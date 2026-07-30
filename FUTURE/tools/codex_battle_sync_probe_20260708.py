import concurrent.futures
import copy
import json
import shutil
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import FUTURE.server_app as app


RUN_ID = f"{int(time.time())}{time.process_time_ns() % 100000}"
USER_PREFIX = f"codexbattle{RUN_ID}"
COUNT = 100
PAIR_COUNT = COUNT // 2
QROOT = Path(r"C:\QMLearn\users")


def make_user(index: int) -> str:
    return f"{USER_PREFIX}{index:03d}"


def make_battle(pair_index: int, user_a: str, user_b: str) -> dict:
    battle_id = f"codex_battle_{RUN_ID}_{pair_index:03d}"
    now = app.utc_timestamp()
    turn = user_a if pair_index % 2 == 0 else user_b
    return {
        "id": battle_id,
        "game": "fireball_vocab",
        "status": "active",
        "players": [user_a, user_b],
        "npc_bots": [],
        "hp": {user_a: 100, user_b: 100},
        "mp": {user_a: 0, user_b: 0},
        "buffs": {user_a: {}, user_b: {}},
        "recent_words": {user_a: [], user_b: []},
        "asked_words": {user_a: [], user_b: []},
        "wager": 0,
        "created_at": now,
        "updated_at": now,
        "turn": turn,
        "phase": "question",
        "deadline_at": app.local_timestamp(time.time() + 30),
        "question": {
            "prompt": "Type the English word.",
            "meaning": "kiem tra dong bo",
            "answer": "sync",
            "answer_text": "sync",
            "created_at": now,
        },
        "log": [
            {"at": now, "type": "start", "text": "Codex battle sync probe started."},
            {"at": now, "type": "coin", "text": f"Coin flip: {turn} starts first."},
        ],
    }


def setup_state() -> tuple[dict, list[tuple[str, str, str, str]]]:
    users = [make_user(index) for index in range(COUNT)]
    rows: list[tuple[str, str, str, str]] = []
    state = app.load_shared_world_battle_state()
    battles = state.setdefault("battles", {})
    for pair_index in range(PAIR_COUNT):
        user_a = users[pair_index * 2]
        user_b = users[pair_index * 2 + 1]
        battle = make_battle(pair_index, user_a, user_b)
        battles[battle["id"]] = battle
        rows.append((battle["id"], battle["turn"], user_a, user_b))
    app.write_shared_world_battle_state(state, force=False)
    return state, rows


def answer_one(row: tuple[str, str, str, str]) -> dict:
    battle_id, turn, user_a, user_b = row
    started = time.perf_counter()
    result = app.shared_world_battle_answer(turn, {"battle_id": battle_id, "answer": "sync"})
    left = app.shared_world_battle_state_for_user(user_a).get("battle") or {}
    right = app.shared_world_battle_state_for_user(user_b).get("battle") or {}
    left_log = left.get("log") if isinstance(left.get("log"), list) else []
    right_log = right.get("log") if isinstance(right.get("log"), list) else []
    left_last = left_log[-1] if left_log else {}
    right_last = right_log[-1] if right_log else {}
    return {
        "battle_id": battle_id,
        "ms": round((time.perf_counter() - started) * 1000, 3),
        "ok": bool(result.get("battle")),
        "deadline_match": left.get("deadline_epoch") == right.get("deadline_epoch"),
        "event_match": left_last.get("event_id") == right_last.get("event_id"),
        "left_event": left_last.get("event_id", ""),
        "right_event": right_last.get("event_id", ""),
        "left_seq": left.get("updated_seq", 0),
        "right_seq": right.get("updated_seq", 0),
    }


def main() -> None:
    original_cache = copy.deepcopy(app.SHARED_WORLD_BATTLE_STATE_CACHE)
    original_text = app.SHARED_WORLD_BATTLE_FILE.read_text(encoding="utf-8-sig", errors="replace") if app.SHARED_WORLD_BATTLE_FILE.is_file() else None
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    try:
        _state, rows = setup_state()
        setup_ms = round((time.perf_counter() - started_wall) * 1000, 3)
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(answer_one, rows))
        wall_ms = round((time.perf_counter() - started_wall) * 1000, 3)
        cpu_ms = round((time.process_time() - started_cpu) * 1000, 3)
        latencies = [row["ms"] for row in results]
        payload = {
            "users": COUNT,
            "battles": PAIR_COUNT,
            "setup_ms": setup_ms,
            "wall_ms": wall_ms,
            "cpu_ms": cpu_ms,
            "ok": sum(1 for row in results if row["ok"]),
            "deadline_match": sum(1 for row in results if row["deadline_match"]),
            "event_match": sum(1 for row in results if row["event_match"]),
            "latency_ms": {
                "min": min(latencies) if latencies else 0,
                "median": statistics.median(latencies) if latencies else 0,
                "p95": sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0,
                "max": max(latencies) if latencies else 0,
            },
            "sample": results[:3],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        for path in QROOT.glob(f"{USER_PREFIX}*"):
            if path.is_dir() and path.parent == QROOT:
                shutil.rmtree(path, ignore_errors=True)
        app.SHARED_WORLD_BATTLE_STATE_CACHE.clear()
        app.SHARED_WORLD_BATTLE_STATE_CACHE.update(original_cache)
        if original_text is None:
            try:
                app.SHARED_WORLD_BATTLE_FILE.unlink()
            except FileNotFoundError:
                pass
        else:
            app.atomic_write_json(app.SHARED_WORLD_BATTLE_FILE, json.loads(original_text or "{}"), indent=2)


if __name__ == "__main__":
    main()
