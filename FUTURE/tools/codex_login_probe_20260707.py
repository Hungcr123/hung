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
USER_PREFIX = f"codexlogin{RUN_ID}"
CODEX_RE = re.compile(r"\bcodexlogin[0-9a-z_-]*", re.I)
PASSWORD = "codexpass"


def percentile_summary(values: list[int]) -> dict:
    if not values:
        return {}

    def pick(percent: float) -> int:
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * percent))))
        return values[index]

    return {"min": values[0], "p50": pick(0.50), "p90": pick(0.90), "p99": pick(0.99), "max": values[-1]}


def setup_users(count: int = 100) -> list[str]:
    users = [f"{USER_PREFIX}{idx:03d}" for idx in range(count)]
    for username in users:
        profile = {
            "full_name": f"Codex Login {username[-3:]}",
            "gender": "other",
            "birth_date": "2000-01-01",
            "avatar": "",
            "intro": "",
            "profile_photos": [],
            "updated_at": app.utc_timestamp(),
        }
        preferences = {
            "question_motion": {"picture": "always", "audio": "always"},
            "question_animation": {"paused": True},
            "space_w_voice": {"voice": "sot:en-GB"},
            "updated_at": app.utc_timestamp(),
        }
        app.write_user_lines(username, [
            f"{username}:{PASSWORD}",
            app.PROFILE_PREFIX + json.dumps(profile, ensure_ascii=False, separators=(",", ":")),
            app.PREFERENCES_PREFIX + json.dumps(preferences, ensure_ascii=False, separators=(",", ":")),
        ])
        app.ensure_server_data_folders(username)
    return users


def login_one(username: str, include_me: bool = True) -> dict:
    timing = {}
    started = time.perf_counter()

    t = time.perf_counter()
    ok, reason, profile = app.check_user_login(username, PASSWORD)
    timing["check_ms"] = int((time.perf_counter() - t) * 1000)
    if not ok:
        raise RuntimeError(f"login failed {username}: {reason}")

    t = time.perf_counter()
    session = app.create_auth_session(username)
    timing["session_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    app.chat_mark_online(username)
    app.mark_user_activity(username, {"status": "Logged in"})
    timing["activity_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    app.start_main_vocab_sync_user(username, force=False, reason="codex-login-probe")
    timing["main_sync_schedule_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    app.record_login_event(username, {"client": "127.0.0.1", "probe": "codex"})
    timing["login_event_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    server_data = app.ensure_server_data_folders(username)
    timing["server_data_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    preferences = app.read_user_preferences(username)
    timing["preferences_ms"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    missing = app.profile_missing(profile)
    is_admin = app.is_admin_user(username)
    timing["misc_ms"] = int((time.perf_counter() - t) * 1000)

    me_payload = {}
    if include_me:
        t = time.perf_counter()
        me_payload = app.auth_me_payload(username, include_rewards=True)
        timing["auth_me_ms"] = int((time.perf_counter() - t) * 1000)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "user": username,
        "ms": elapsed_ms,
        "timing": timing,
        "token": bool(session.get("token")),
        "needs_profile": bool(missing),
        "is_admin": is_admin,
        "preferences": bool(preferences),
        "server_data": bool(server_data),
        "auth_me": bool(me_payload.get("ok")) if isinstance(me_payload, dict) else False,
    }


def run_group(count: int = 100, workers: int = 32, include_me: bool = True) -> dict:
    users = setup_users(count)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    rows = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(login_one, username, include_me) for username in users]
        for future in concurrent.futures.as_completed(futures):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append(str(exc))
    wall_ms = int((time.perf_counter() - started_wall) * 1000)
    cpu_ms = int((time.process_time() - started_cpu) * 1000)
    timing_keys = sorted({key for row in rows for key in row.get("timing", {}).keys()})
    timing_summary = {
        key: percentile_summary(sorted(int(row.get("timing", {}).get(key, 0) or 0) for row in rows))
        for key in timing_keys
    }
    return {
        "count": count,
        "workers": workers,
        "include_me": include_me,
        "ok": len(rows),
        "errors": errors[:5],
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "per_login_ms": percentile_summary(sorted(int(row.get("ms", 0) or 0) for row in rows)),
        "timing": timing_summary,
        "auth_me_ok": sum(1 for row in rows if row.get("auth_me")),
    }


def scrub_codex(obj):
    removed = 0
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if CODEX_RE.search(str(key)):
                removed += 1
                continue
            if isinstance(value, dict) and any(CODEX_RE.search(str(value.get(field, ""))) for field in ("user", "username", "path", "effective_path")):
                removed += 1
                continue
            next_value, count = scrub_codex(value)
            removed += count
            out[key] = next_value
        return out, removed
    if isinstance(obj, list):
        out = []
        for value in obj:
            if isinstance(value, str) and CODEX_RE.search(value):
                removed += 1
                continue
            if isinstance(value, dict) and any(CODEX_RE.search(str(value.get(field, ""))) for field in ("user", "username", "path", "effective_path")):
                removed += 1
                continue
            next_value, count = scrub_codex(value)
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
            if path.name.lower().startswith("codexlogin"):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                removed_paths += 1
    for path in QROOT.glob("codexlogin*.txt"):
        path.unlink(missing_ok=True)
        removed_paths += 1
    state_files = [
        QROOT / "_future_auth_sessions.json",
        ROOT / "_future_vocab_leaderboard_ranks.json",
        ROOT / "_future_vocab_leaderboard_periods.json",
        ROOT / "_future_vocab_leaderboard_reward_claims.json",
        ROOT / "_future_vocab_leaderboard_viewers.json",
        ROOT / "space_leaderboard_activity.json",
    ]
    removed_state = {}
    for file in state_files:
        if not file.is_file():
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8-sig") or "{}")
            new_data, count = scrub_codex(data)
            if count:
                file.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            removed_state[str(file)] = count
        except Exception as exc:
            removed_state[str(file)] = f"error:{exc}"
    with app.AUTH_LOCK:
        for token, session in list(app.AUTH_SESSIONS.items()):
            if CODEX_RE.search(str(session.get("username", ""))):
                app.AUTH_SESSIONS.pop(token, None)
    with app.USER_ACTIVITY_LOCK:
        for key in list(app.USER_ACTIVITY.keys()):
            if CODEX_RE.search(str(key)):
                app.USER_ACTIVITY.pop(key, None)
    return {"paths": removed_paths, "state": removed_state}


def main() -> None:
    arg = (sys.argv[1] if len(sys.argv) > 1 else "100").strip().lower()
    if arg == "cleanup":
        print(json.dumps({"cleanup": cleanup()}, ensure_ascii=False, indent=2))
        return
    include_me = arg != "login-only"
    try:
        result = run_group(100, 32, include_me=include_me)
    finally:
        cleanup_result = cleanup()
    print(json.dumps({"result": result, "cleanup": cleanup_result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
