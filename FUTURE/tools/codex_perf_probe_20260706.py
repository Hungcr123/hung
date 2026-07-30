import cProfile
import io
import json
import os
import pstats
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import FUTURE.server_app as app


USER = f"codexperfprobe{int(time.time())}"
ROOT = Path(r"C:\server data")
QROOT = Path(r"C:\QMLearn\users")
TEST_DIR = ROOT / USER
CODEX_RE = re.compile(r"\bcodex[a-z0-9_-]*", re.I)

SAMPLES = {
    "space_v": ROOT / r"common\Study\360 dong tu bat quy tac day du - ZIM\Cot 2 (V2) - [13 Files] - {303 words}\File 01 - {1-25,26-50}.Space_V",
    "space_w": ROOT / r"common\Giao tiếp hàng ngày\Chào hỏi 10 câu.Space_W",
    "space_q": ROOT / r"common\Giao tiếp hàng ngày\So_dem_tieng_Anh_50_bai_tap.Space_Q",
    "space_p": ROOT / r"common\Space\Empower A1\Unit 1\Empower_A2_U1_Learning_English.Space_P",
    "space_s": ROOT / r"common\Space\Empower A1\Unit 1\Empower_A2_U1_Speaking_Practice.Space_S",
    "space_l": ROOT / r"common\Space\Empower A1\Unit 1\Empower_A2_U1_Studying_English.Space_L",
}


def profile_call(label, fn, *args, **kwargs):
    profiler = cProfile.Profile()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    result = profiler.runcall(fn, *args, **kwargs)
    wall_ms = int((time.perf_counter() - started_wall) * 1000)
    cpu_ms = int((time.process_time() - started_cpu) * 1000)
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumtime").print_stats(15)
    return {
        "label": label,
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "result_summary": summarize_result(result),
        "profile": stream.getvalue(),
    }


def summarize_result(value):
    if not isinstance(value, dict):
        return value
    out = {}
    for key in ("path", "updated_file", "timing_ms", "recorded", "day", "week", "month", "claimed_at"):
        if key in value:
            out[key] = value.get(key)
    if "boards" in value:
        out["boards"] = {k: len(v) for k, v in (value.get("boards") or {}).items() if isinstance(v, list)}
    if "claims" in value:
        out["claims"] = len(value.get("claims") or [])
    if "items" in value:
        out["items"] = len(value.get("items") or [])
    return out


def setup_files():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    rels = {}
    for board, src in SAMPLES.items():
        if not src.is_file():
            continue
        dst = TEST_DIR / f"{board}{src.suffix}"
        shutil.copy2(src, dst)
        rels[board] = app.server_data_relative(dst)
    return rels


def is_codex_string(value):
    return isinstance(value, str) and bool(CODEX_RE.search(value))


def row_is_codex(value):
    if not isinstance(value, dict):
        return False
    for key in ("user", "username", "viewer", "owner", "actor", "name", "path", "effective_path", "source_path", "link_target"):
        if is_codex_string(value.get(key)):
            return True
    return False


def scrub_codex(obj):
    removed = 0
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if is_codex_string(key) or row_is_codex(value):
                removed += 1
                continue
            next_value, count = scrub_codex(value)
            removed += count
            out[key] = next_value
        return out, removed
    if isinstance(obj, list):
        out = []
        for value in obj:
            if is_codex_string(value) or row_is_codex(value):
                removed += 1
                continue
            next_value, count = scrub_codex(value)
            removed += count
            out.append(next_value)
        return out, removed
    return obj, 0


def cleanup():
    for path in (TEST_DIR, QROOT / USER):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    state_files = [
        ROOT / "_future_vocab_leaderboard_ranks.json",
        ROOT / "_future_vocab_leaderboard_periods.json",
        ROOT / "_future_vocab_leaderboard_reward_claims.json",
        ROOT / "_future_vocab_leaderboard_viewers.json",
        ROOT / "_future_vocab_leaderboard_npc_top.json",
        ROOT / "space_leaderboard_activity.json",
    ]
    removed = {}
    for file in state_files:
        if not file.is_file():
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8-sig") or "{}")
        except Exception:
            continue
        new_data, count = scrub_codex(data)
        if count:
            file.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        removed[str(file)] = count
    return removed


def main():
    rels = setup_files()
    measurements = []
    for board, rel_path in rels.items():
        source = "Space_V" if board == "space_v" else board
        measurements.append(profile_call(f"complete:{board}", app.record_lesson_completion, rel_path, USER, {"source": source, "title": board, "nodes": 25}))
    for board in ("space_v", "space_w", "space_q", "space_p", "space_s", "space_l"):
        measurements.append(profile_call(f"top-cold:{board}", app.vocabulary_leaderboard, 80, False, USER, board))
    for board in ("space_v", "space_w", "space_q", "space_p", "space_s", "space_l"):
        measurements.append(profile_call(f"top-warm:{board}", app.vocabulary_leaderboard, 80, False, USER, board))
    measurements.append(profile_call("claim_rewards", app.claim_pending_vocab_leaderboard_rewards, USER, True))
    cleanup_removed = cleanup()
    print(json.dumps({"user": USER, "measurements": measurements, "cleanup_removed": cleanup_removed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
