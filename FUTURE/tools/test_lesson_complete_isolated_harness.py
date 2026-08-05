#!/usr/bin/env python3
"""Isolated production-chain gate for one real Space_V /lesson/complete request.

The harness owns a temporary PostgreSQL cluster, server-data root, runtime root,
and HTTP port 18877. It never changes production PostgreSQL or server-data.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
PG_BIN = Path(r"C:\Program Files\PostgreSQL\17\bin")
RUN_ROOT = ROOT / "programe_cache" / "lesson_complete_isolated_18877"
PG_ROOT = RUN_ROOT / "postgres"
SERVER_DATA_ROOT = RUN_ROOT / "server-data"
RUNTIME_ROOT = RUN_ROOT / "runtime"
QMLEARN_ROOT = RUN_ROOT / "qml"
PG_PORT = 55432
HTTP_PORT = 18877
BASE = f"http://127.0.0.1:{HTTP_PORT}"
TEST_DATABASE = "future_server2_copy"
PG_DSN = f"postgresql://future_server2_app@127.0.0.1:{PG_PORT}/{TEST_DATABASE}"
PRODUCTION_DSN = os.environ.get("FUTURE_PG_DSN", "postgresql://future_server2_app@127.0.0.1:5432/future_server2")
LESSON_SOURCE = Path(r"C:\server data\common\File 02 - {7}.Space_V")
LESSON_PATH = "common/File 02 - {7}.Space_V"
LESSON_ID = "ftg-lesson-000002312"
TEST_USER = "codexcompleteisolated"
RECOVERY_USER = "codexcompleterecovery"
PASSWORD = secrets.token_urlsafe(24)
SERVER_LOG = RUN_ROOT / "server.log"
PG_LOG = RUN_ROOT / "postgres.log"
OUTPUT_PATH = Path(os.environ.get("FUTURE_COMPLETION_HARNESS_OUTPUT", r"C:\Users\Admin\.codex\plans\lesson_complete_isolated_20260729.json"))

POSTGRES_DOMAINS = (
    "AI_HISTORY_DOCUMENTS", "ANNOUNCEMENTS", "APPEND_EVENTS", "AUTH", "CHAT",
    "INVENTORY", "LEADERBOARD_DOCUMENTS", "LEARNING_SUMMARY_DOCUMENTS",
    "LESSON_FOLDER_LINKS", "LESSON_IDENTITY", "LESSON_LAST_FILE", "LESSON_PROGRESS",
    "LESSON_TASK", "LESSON_TASK_NOTICES", "LESSON_TIME", "PDF_DRAWINGS",
    "QMDICT_DOCUMENTS", "QM_CITY_DOCUMENTS", "SPACE_PDF_AI_DOCUMENTS",
    "SPACE_W_SPEAK_SKIP", "USER_AUTH_DOCS", "USER_PREFERENCES", "VAULT_METADATA",
    "VIEWER_TOOL_DOCUMENTS", "VOCABULARY", "VOCAB_IMAGE_CACHE",
)


def run(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, env=env, check=True, text=True, capture_output=True, timeout=timeout)


def password_hash(value: str) -> str:
    rounds = 2
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"


def start_postgres() -> subprocess.Popen:
    PG_ROOT.parent.mkdir(parents=True, exist_ok=True)
    run([str(PG_BIN / "initdb.exe"), "-D", str(PG_ROOT), "-U", "future_server2_app", "--auth-local=trust", "--auth-host=trust", "--encoding=UTF8"], timeout=120)
    process = subprocess.Popen(
        [str(PG_BIN / "pg_ctl.exe"), "-D", str(PG_ROOT), "-o", f"-p {PG_PORT} -h 127.0.0.1", "-l", str(PG_LOG), "start"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        probe = subprocess.run([str(PG_BIN / "pg_isready.exe"), "-h", "127.0.0.1", "-p", str(PG_PORT)], capture_output=True, text=True)
        if probe.returncode == 0:
            return process
        time.sleep(0.4)
    raise RuntimeError("isolated PostgreSQL did not become ready")


# Added 2026-07-29: every isolated run starts from a fresh production DB snapshot, never stale test data.
def sync_production_database_snapshot() -> Path:
    """Synchronize the isolated PostgreSQL database from the production source before testing."""
    dump_path = RUN_ROOT / "production_copy.dump"
    run([
        str(PG_BIN / "createdb.exe"), "-h", "127.0.0.1", "-p", str(PG_PORT),
        "-U", "future_server2_app", TEST_DATABASE,
    ], timeout=60)
    run([
        str(PG_BIN / "pg_dump.exe"), PRODUCTION_DSN, "--format=custom",
        "--schema=future_server2", "--no-owner", "--no-privileges", "--file", str(dump_path),
    ], timeout=900)
    run([
        str(PG_BIN / "pg_restore.exe"), "--no-owner", "--no-privileges",
        "--dbname", PG_DSN, str(dump_path),
    ], timeout=900)
    return dump_path


def stop_postgres() -> None:
    if PG_ROOT.is_dir():
        subprocess.run([str(PG_BIN / "pg_ctl.exe"), "-D", str(PG_ROOT), "-m", "fast", "stop"], capture_output=True, text=True, timeout=60)


def app_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "FUTURE_PG_DSN": PG_DSN,
        "FUTURE_POSTGRES_ONLY": "1",
        "FUTURE_SERVER_DATA_ROOT": str(SERVER_DATA_ROOT),
        "FUTURE_RUNTIME_ROOT": str(RUNTIME_ROOT),
        "FUTURE_QMLEARN_ROOT": str(QMLEARN_ROOT),
        "FUTURE_SKIP_POSTGRES_SERVICE_START": "1",
        "FUTURE_TEST_PASSWORD": "",
    })
    env.pop("FUTURE_TEST_AUTH_BYPASS", None)
    env.pop("FUTURE_TEST_FAIL_COMPLETION_BEFORE_FINALIZE", None)
    for domain in POSTGRES_DOMAINS:
        env[f"FUTURE_DB_{domain}_BACKEND"] = "postgres"
    return env


def initialize_schema() -> None:
    code = "import FUTURE.server_app as app; print(app.postgres_initialize_schema())"
    result = run([sys.executable, "-c", code], env=app_env(), timeout=120)
    if "future_server2" not in result.stdout:
        raise RuntimeError(f"schema initialization failed: {result.stdout} {result.stderr}")


def provision_postgres() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source = psycopg.connect(PRODUCTION_DSN, row_factory=dict_row)
    target = psycopg.connect(PG_DSN, row_factory=dict_row)
    try:
        with source.cursor() as cursor:
            cursor.execute("SELECT * FROM future_server2.vocabulary_registry WHERE lower(username)=lower(%s)", ("quynh",))
            rows = cursor.fetchall()
        if not rows:
            raise RuntimeError("production quynh registry is empty")
        with target.cursor() as cursor:
            for username in (TEST_USER, RECOVERY_USER):
                cursor.execute(
                """INSERT INTO future_server2.users
                   (username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test,migrated_at_utc,source_sha256)
                   VALUES (%s,false,%s,%s,0,false,'','')
                   ON CONFLICT (username) DO UPDATE SET is_test=false,profile_json=excluded.profile_json""",
                    (username, json.dumps({"load_test": True, "source": "isolated-harness"}), now),
                )
                cursor.execute(
                """INSERT INTO future_server2.user_auth_credentials
                   (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,%s,'isolated-harness',%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
                    (username, password_hash(PASSWORD), now),
                )
            columns = [
                "word_key", "word", "meaning", "pron", "word_type", "learn_count",
                "first_at_utc", "last_at_utc", "last_epoch", "sources_json", "qmdict_missing",
                "migrated_at_utc", "source_sha256",
            ]
            query = "INSERT INTO future_server2.vocabulary_registry (username," + ",".join(columns) + ") VALUES (%s," + ",".join(["%s"] * len(columns)) + ")"
            values = []
            for row in rows:
                copied = [Jsonb(row.get(column) or []) if column == "sources_json" else row.get(column) for column in columns]
                values.extend((username, *copied) for username in (TEST_USER, RECOVERY_USER))
            cursor.executemany(query, values)
        target.commit()
        return len(rows)
    finally:
        source.close()
        target.close()


def copy_lesson() -> None:
    if not LESSON_SOURCE.is_file():
        raise RuntimeError(f"real lesson missing: {LESSON_SOURCE}")
    target = SERVER_DATA_ROOT / LESSON_PATH.replace("/", "\\")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LESSON_SOURCE, target)
    for directory in ("Sound", "Picture", "NPC_TOP"):
        (SERVER_DATA_ROOT / directory).mkdir(parents=True, exist_ok=True)


def copied_lesson_sha256() -> str:
    target = SERVER_DATA_ROOT / LESSON_PATH.replace("/", "\\")
    return hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else ""


def lesson_words() -> list[str]:
    encoded = LESSON_SOURCE.read_text(encoding="utf-8").strip()
    payload = json.loads(gzip.decompress(base64.urlsafe_b64decode(encoded[5:] + "===")))
    return [str(item.get("w", "")).strip().lower() for item in payload.get("w", []) if isinstance(item, dict) and str(item.get("w", "")).strip()]


def start_server(fail_prefix: str = "", no_preload: bool = True, extra_env: dict[str, str] | None = None) -> subprocess.Popen:
    env = app_env()
    if fail_prefix:
        env["FUTURE_TEST_FAIL_COMPLETION_BEFORE_FINALIZE"] = fail_prefix
    if isinstance(extra_env, dict):
        env.update({str(key): str(value) for key, value in extra_env.items()})
    handle = SERVER_LOG.open("ab")
    # Added 2026-08-03: isolated fixtures must never inherit the production
    # entry point's automatic --replace-old behavior.
    command = [sys.executable, "FUTURE/server2/run_server_2.py", "--host", "127.0.0.1", "--port", str(HTTP_PORT), "--no-browser", "--no-tunnel"]
    if no_preload:
        command.append("--no-preload")
    return subprocess.Popen(
        command,
        cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def stop_server(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)
    except Exception:
        process.kill()
        process.wait(timeout=20)


def wait_health(process: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            health = requests.get(f"{BASE}/health", timeout=5).json()
            if int(health.get("pid", 0) or 0) == process.pid and health.get("ready") and health.get("warm_ready"):
                return health
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"isolated Server 2 not warm: {SERVER_LOG}")


def server_cpu(process: subprocess.Popen) -> float:
    try:
        current = psutil.Process(process.pid).cpu_times()
        return (current.user + current.system) * 1000
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def postgres_processes() -> list[psutil.Process]:
    result = []
    listener_pids = {
        int(connection.pid)
        for connection in psutil.net_connections(kind="tcp")
        if connection.laddr and connection.laddr.port == PG_PORT and connection.status == psutil.CONN_LISTEN and connection.pid
    }
    for pid in list(listener_pids):
        try:
            root = psutil.Process(pid)
            result.extend([root, *root.children(recursive=True)])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    unique = {process.pid: process for process in result}
    return list(unique.values())


def postgres_cpu() -> float:
    total = 0.0
    for process in postgres_processes():
        try:
            cpu = process.cpu_times()
            total += (cpu.user + cpu.system) * 1000
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


def login(username: str = TEST_USER) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": PASSWORD}, timeout=30)
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError(f"test login returned no token: {response.text[:300]}")
    return str(token)


def counts(username: str = TEST_USER) -> dict[str, int]:
    import psycopg
    with psycopg.connect(PG_DSN) as connection, connection.cursor() as cursor:
        result = {}
        for key, table in (("registry", "vocabulary_registry"), ("vocabulary_events", "vocabulary_events"), ("daily_earn", "daily_earn"), ("weekly_earn", "weekly_earn"), ("monthly_earn", "monthly_earn"), ("final_events", "append_events"), ("progress", "lesson_progress")):
            if key == "final_events":
                cursor.execute("SELECT count(*) FROM future_server2.append_events WHERE stream='learning' AND lower(username)=lower(%s)", (username,))
            elif key == "progress":
                cursor.execute("SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username)=lower(%s)", (username,))
            else:
                cursor.execute(f"SELECT count(*) FROM future_server2.{table} WHERE lower(username)=lower(%s)", (username,))
            result[key] = int(cursor.fetchone()[0] or 0)
        return result


def complete(token: str, body: dict) -> tuple[float, int, dict, float, float]:
    process = psutil.Process(int(requests.get(f"{BASE}/health", timeout=5).json()["pid"]))
    server_before = (process.cpu_times().user + process.cpu_times().system) * 1000
    pg_before = postgres_cpu()
    started = time.perf_counter()
    response = requests.post(f"{BASE}/lesson/complete", headers={"Authorization": f"Bearer {token}"}, json=body, timeout=90)
    wall = (time.perf_counter() - started) * 1000
    server_after = (process.cpu_times().user + process.cpu_times().system) * 1000
    pg_after = postgres_cpu()
    return wall, response.status_code, response.json(), server_after - server_before, pg_after - pg_before


def save_space_v_progress(token: str, words: list[str], trace: str) -> tuple[float, int, dict, float, float]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state = {
        "path": LESSON_PATH,
        "lessonSource": {"path": LESSON_PATH, "lesson_id": LESSON_ID, "file_id": LESSON_ID, "source": "server"},
        "learned": words,
        "learnedWords": [{"word": word} for word in words],
        "complete": True, "completed": True, "lessonComplete": True,
        "lessonCompletionSent": True, "vocabComplete": True, "registryReady": True,
        "savedAt": now,
    }
    body = {
        "action": "complete", "path": LESSON_PATH, "identity": LESSON_ID,
        "lesson_id": LESSON_ID, "file_id": LESSON_ID, "title": "File 02 - {7}",
        "nodeIndex": len(words), "nodeCount": len(words), "learnedCount": len(words),
        "learnedWords": [{"word": word} for word in words], "state": state,
        "savedAt": now, "completion_trace_id": trace,
    }
    server_pid = int(requests.get(f"{BASE}/health", timeout=5).json()["pid"])
    process = psutil.Process(server_pid)
    server_before = (process.cpu_times().user + process.cpu_times().system) * 1000
    pg_before = postgres_cpu()
    started = time.perf_counter()
    response = requests.post(f"{BASE}/space-v/progress?client_source=space_v_complete&response=compact-v1", headers={"Authorization": f"Bearer {token}"}, json=body, timeout=60)
    wall = (time.perf_counter() - started) * 1000
    server_after = (process.cpu_times().user + process.cpu_times().system) * 1000
    pg_after = postgres_cpu()
    return wall, response.status_code, response.json(), server_after - server_before, pg_after - pg_before


def read_progress_and_top(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    progress = requests.get(
        f"{BASE}/space-v/progress",
        headers=headers,
        params={"path": LESSON_PATH, "identity": LESSON_ID, "lesson_id": LESSON_ID},
        timeout=30,
    )
    top = requests.get(
        f"{BASE}/vocab/leaderboard",
        headers=headers,
        params={"limit": 500, "double_check": 0, "scope": "day", "type": "space_v"},
        timeout=30,
    )
    progress_payload = progress.json()
    top_payload = top.json()
    boards = top_payload.get("boards") if isinstance(top_payload.get("boards"), dict) else {}
    day_rows = boards.get("day") if isinstance(boards.get("day"), list) else []
    top_user_row = next(
        (row for row in day_rows if isinstance(row, dict) and str(row.get("username", "")).strip().lower() == TEST_USER.lower()),
        None,
    )
    return {
        "progress_status": progress.status_code,
        "progress": progress_payload,
        "top_status": top.status_code,
        "top_contains_user": isinstance(top_user_row, dict),
        "top_user_row": top_user_row,
        "top_day_rows": len(day_rows),
    }


def main() -> int:
    try:
        production_health_before = requests.get("http://127.0.0.1:8877/health", timeout=10).status_code
    except requests.RequestException:
        production_health_before = 0
    if any(connection.laddr and connection.laddr.port == HTTP_PORT and connection.status == psutil.CONN_LISTEN for connection in psutil.net_connections(kind="tcp")):
        raise RuntimeError("port 18877 is already in use")
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    pg_process = None
    server = None
    try:
        copy_lesson()
        lesson_sha_before = copied_lesson_sha256()
        pg_process = start_postgres()
        dump_path = sync_production_database_snapshot()
        cloned_rows = provision_postgres()
        server = start_server()
        health = wait_health(server)
        token = login()
        words = lesson_words()
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        trace = f"codex-isolated-{int(time.time())}-{secrets.token_hex(4)}"
        body = {
            "path": LESSON_PATH, "lesson_id": LESSON_ID, "file_id": LESSON_ID,
            "title": "Codex isolated real Space_V", "name": Path(LESSON_PATH).name,
            "nodes": 7, "completed_at": stamp, "source": "Space_V",
            "completion_trace_id": trace,
        }
        before = counts(TEST_USER)
        idle_server_before = server_cpu(server)
        idle_pg_before = postgres_cpu()
        time.sleep(5.0)
        idle_5s = {"server_cpu_ms": server_cpu(server) - idle_server_before, "postgres_cpu_ms": postgres_cpu() - idle_pg_before}
        progress_save = save_space_v_progress(token, words, trace)
        first = complete(token, body)
        server_post = server_cpu(server)
        pg_post = postgres_cpu()
        time.sleep(1.0)
        after_1s = {"server_cpu_ms": server_cpu(server) - server_post, "postgres_cpu_ms": postgres_cpu() - pg_post}
        time.sleep(4.0)
        after_5s = {"server_cpu_ms": server_cpu(server) - server_post, "postgres_cpu_ms": postgres_cpu() - pg_post}
        retry = complete(token, body)
        after_retry = counts(TEST_USER)
        fail_run = f"codex-isolated-fail-{secrets.token_hex(4)}"
        fail_body = {**body, "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "completion_run_id": fail_run, "completion_trace_id": f"{trace}-fail"}
        stop_server(server)
        server = start_server(fail_prefix=fail_run)
        wait_health(server)
        fail_token = login(RECOVERY_USER)
        failed = complete(fail_token, fail_body)
        failed_counts = counts(RECOVERY_USER)
        stop_server(server)
        server = start_server()
        wait_health(server)
        recovered_counts = counts(RECOVERY_USER)
        first_token_after_restart = login(TEST_USER)
        first_readback = read_progress_and_top(first_token_after_restart)
        first_retry_after_restart = complete(first_token_after_restart, body)
        recovery_retry = complete(login(RECOVERY_USER), fail_body)
        final_counts = counts(RECOVERY_USER)
        lesson_sha_after = copied_lesson_sha256()
        try:
            production_auth = requests.post(f"http://127.0.0.1:8877/lesson/complete", json={"path": LESSON_PATH}, timeout=20).status_code
        except requests.RequestException:
            production_auth = 0
        log_lines = SERVER_LOG.read_text(encoding="utf-8", errors="replace").splitlines() if SERVER_LOG.is_file() else []
        background_log = [line for line in log_lines if "BACKGROUND" in line or trace in line][-40:]
        output = {
            "resources": {"listen_port": HTTP_PORT, "postgres_database": TEST_DATABASE, "postgres_dsn": f"postgresql://future_server2_app@127.0.0.1:{PG_PORT}/{TEST_DATABASE}", "postgres_data_root": str(PG_ROOT), "server_data_root": str(SERVER_DATA_ROOT), "runtime_root": str(RUNTIME_ROOT), "database_dump_bytes": dump_path.stat().st_size, "test_mode": "isolated-postgres-cluster+full-production-copy+real-login"},
            "database_sync": {"enabled": True, "source": "127.0.0.1:5432/future_server2", "method": "fresh pg_dump + pg_restore before each run", "dump_bytes": dump_path.stat().st_size},
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready"), "server_data_root": health.get("server_data_root")}, "test_user": TEST_USER, "recovery_user": RECOVERY_USER, "real_lesson": {"path": LESSON_PATH, "lesson_id": LESSON_ID, "cloned_registry_rows": cloned_rows},
            "before": before,
            "idle_5s": idle_5s,
            "progress_save": {"wall_ms": progress_save[0], "status": progress_save[1], "payload": progress_save[2], "server_cpu_ms": progress_save[3], "postgres_cpu_ms": progress_save[4]},
            "first": {"wall_ms": first[0], "status": first[1], "payload": first[2], "server_cpu_ms": first[3], "postgres_cpu_ms": first[4]},
            "after_1s": after_1s, "after_5s": after_5s,
            "retry": {"wall_ms": retry[0], "status": retry[1], "payload": retry[2], "server_cpu_ms": retry[3], "postgres_cpu_ms": retry[4]},
            "after_retry": after_retry,
            "failure": {"wall_ms": failed[0], "status": failed[1], "payload": failed[2], "server_cpu_ms": failed[3], "postgres_cpu_ms": failed[4], "counts": failed_counts},
            "recovered_after_restart": recovered_counts,
            "first_user_after_restart": first_readback,
            "first_retry_after_restart": {"wall_ms": first_retry_after_restart[0], "status": first_retry_after_restart[1], "deduplicated": bool(first_retry_after_restart[2].get("deduplicated")), "server_cpu_ms": first_retry_after_restart[3], "postgres_cpu_ms": first_retry_after_restart[4]},
            "recovery_retry": {"wall_ms": recovery_retry[0], "status": recovery_retry[1], "payload": recovery_retry[2], "server_cpu_ms": recovery_retry[3], "postgres_cpu_ms": recovery_retry[4]},
            "final_counts": final_counts,
            "lesson_file": {"sha256_before": lesson_sha_before, "sha256_after": lesson_sha_after, "unchanged": bool(lesson_sha_before and lesson_sha_before == lesson_sha_after)},
            "production_health_before_status": production_health_before,
            "production_unauthenticated_complete_status": production_auth,
            "background_log": background_log,
        }
        progress_summary = first_readback.get("progress", {}).get("summary", {})
        gates = {
            "progress_after_restart": first_readback.get("progress_status") == 200 and progress_summary.get("text") == "10/10" and bool(progress_summary.get("completed")),
            "top_after_restart": (
                first_readback.get("top_status") == 200
                and bool(first_readback.get("top_contains_user"))
                and int((first_readback.get("top_user_row") or {}).get("score", 0) or 0) == len(words)
                and not bool((first_readback.get("top_user_row") or {}).get("placeholder"))
            ),
            "retry_after_restart": first_retry_after_restart[1] == 200 and bool(first_retry_after_restart[2].get("deduplicated")),
            "lesson_file_unchanged": bool(lesson_sha_before and lesson_sha_before == lesson_sha_after),
        }
        output["gates"] = gates
        encoded_output = json.dumps(output, ensure_ascii=False, indent=2, default=str)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(encoded_output, encoding="utf-8")
        print(encoded_output)
        if not all(gates.values()):
            raise RuntimeError(f"isolated completion gate failed: {gates}")
        return 0
    finally:
        stop_server(server)
        stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
