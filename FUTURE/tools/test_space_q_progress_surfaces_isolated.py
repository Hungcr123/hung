"""Fresh-snapshot HTTP/restart gate for unified Space_Q progress surfaces."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "FUTURE" / "tools"))

import test_lesson_complete_isolated_harness as isolated


RUN_ROOT = ROOT / "programe_cache" / "space_q_progress_surfaces_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\space_q_progress_surfaces_isolated_20260803.json")
TEST_USER = "codexspaceqsurface"
RELATIVE = "common/Ngữ pháp/Ngữ pháp/Câu bị động/Bài tập/Câu bị động - 40 bài tập từ cơ bản đến vận dụng.Space_Q"
PARENT = RELATIVE.rsplit("/", 1)[0]
SOURCE = Path(r"C:\server data") / Path(RELATIVE.replace("/", os.sep))


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    isolated.OUTPUT_PATH = OUTPUT
    isolated.TEST_USER = TEST_USER


def provision_user() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = "2026-08-03T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,false,true,%s,%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET is_test=true,profile_json=excluded.profile_json""",
            (TEST_USER, Jsonb({"source": "space-q-progress-surfaces-isolated"}), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.user_auth_credentials
               (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,'space-q-progress-surfaces-isolated',%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
            (TEST_USER, isolated.password_hash(isolated.PASSWORD), now),
        )
        connection.commit()


def prepare_server_data() -> str:
    wrapper = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    if not str(wrapper.get("structure") or "").strip():
        raise RuntimeError("Space_Q fixture has no Structure dependency")
    # Structure bytes are authoritative in the freshly restored PostgreSQL asset store.
    relative = SOURCE.relative_to(Path(r"C:\server data"))
    target = isolated.SERVER_DATA_ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target)
    for name in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / name).mkdir(parents=True, exist_ok=True)
    return str(wrapper.get("lesson_id") or "").strip()


def wait_health(process, timeout_seconds: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last = {}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"isolated Server 2 exited with {process.returncode}")
        try:
            last = requests.get(f"{isolated.BASE}/health", timeout=5).json()
            if int(last.get("pid", 0) or 0) == process.pid and last.get("ready") and last.get("warm_ready"):
                return last
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"isolated Server 2 not warm: {last}")


def local_login() -> str:
    token = isolated.login(TEST_USER)
    if not token:
        raise RuntimeError("isolated local login returned no token")
    return token


def progress_payload(lesson_id: str, done: int, operation: str) -> dict:
    timestamp = f"2026-08-03T00:00:{done + 10:02d}Z"
    return {
        "action": "autosave",
        "path": RELATIVE,
        "identity": lesson_id,
        "lesson_id": lesson_id,
        "title": "Space_Q progress surface probe",
        "nodeIndex": 2,
        "nodeCount": 8,
        "savedAt": timestamp,
        "updatedAt": timestamp,
        "activeRun": True,
        "runId": "space-q-surface-run",
        "syncOperationId": operation,
        "state": {
            "currentIndex": 2,
            "nodeIndex": 2,
            "nodePointer": 3,
            "questionIndex": done,
            "questionDone": done,
            "questionTotal": 48,
            "completedNodes": 0,
            "totalNodes": 8,
            "activeRun": True,
            "runId": "space-q-surface-run",
            "savedAt": timestamp,
            "updatedAt": timestamp,
        },
    }


def task_progress(payload: dict, lesson_id: str, *, automatic: bool | None = None) -> dict:
    rows = list(payload.get("space_tasks") or []) if automatic is True else list(payload.get("tasks") or [])
    if automatic is None:
        rows += list(payload.get("space_tasks") or [])
    for task in rows:
        if str(task.get("lesson_id") or task.get("file_id") or "").strip() == lesson_id or str(task.get("path") or "").strip() == RELATIVE:
            study = task.get("study") if isinstance(task.get("study"), dict) else {}
            return study.get("progress") if isinstance(study.get("progress"), dict) else {}
    return {}


def wait_for_auto_task(headers: dict, lesson_id: str, timeout_seconds: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest = {}
    while time.monotonic() < deadline:
        response = requests.get(f"{isolated.BASE}/lesson-tasks", headers=headers, timeout=30)
        response.raise_for_status()
        latest = response.json()
        if task_progress(latest, lesson_id, automatic=True):
            return latest
        time.sleep(0.25)
    raise RuntimeError(f"automatic Space Task did not become ready: {latest}")


def vault_progress(payload: dict, lesson_id: str) -> dict:
    for entry in payload.get("entries") or []:
        if str(entry.get("lesson_id") or entry.get("file_id") or "").strip() == lesson_id or str(entry.get("path") or "").strip() == RELATIVE:
            study = entry.get("study") if isinstance(entry.get("study"), dict) else {}
            return study.get("progress") if isinstance(study.get("progress"), dict) else {}
    return {}


def run_dom_surface_probe(lesson_id: str) -> dict:
    env = dict(os.environ)
    env.update({
        "FUTURE_DOM_BASE": isolated.BASE,
        "FUTURE_DOM_USER": TEST_USER,
        "FUTURE_DOM_PASSWORD": isolated.PASSWORD,
        "FUTURE_SPACE_Q_PATH": RELATIVE,
        "FUTURE_SPACE_Q_ID": lesson_id,
    })
    completed = subprocess.run(
        ["node", str(ROOT / "FUTURE" / "tools" / "test_space_q_exit_dom_runtime.cjs")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Space_Q DOM Exit probe failed: {completed.stderr[-4000:]}")
    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return json.loads(rows[-1]) if rows else {}


def main() -> int:
    configure()
    if RUN_ROOT.exists():
        def clear_readonly(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(RUN_ROOT, onerror=clear_readonly)
    RUN_ROOT.mkdir(parents=True)
    server = None
    try:
        isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        provision_user()
        lesson_id = prepare_server_data()
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_DISTRIBUTED_WORKER_PORT": "18890"})
        health = wait_health(server)
        process = psutil.Process(server.pid)
        token = local_login()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        folders = requests.post(
            f"{isolated.BASE}/lesson-tasks",
            headers=headers,
            json={"action": "space-folders", "folders": [PARENT]},
            timeout=30,
        )
        folders.raise_for_status()
        initial_auto_tasks = wait_for_auto_task(headers, lesson_id)

        cpu_before = sum(process.cpu_times()[:2])
        zero_post = requests.post(f"{isolated.BASE}/space-q/progress?response=compact-v1", headers=headers, json=progress_payload(lesson_id, 0, "surface-zero"), timeout=30)
        zero_post.raise_for_status()
        zero_get = requests.get(f"{isolated.BASE}/space-q/progress", headers=headers, params={"path": RELATIVE, "identity": lesson_id}, timeout=30)
        zero_get.raise_for_status()
        zero_body = zero_get.json()
        etag = str(zero_get.headers.get("ETag") or "").strip()
        unchanged = requests.get(f"{isolated.BASE}/space-q/progress", headers={**headers, "If-None-Match": etag}, params={"path": RELATIVE, "identity": lesson_id}, timeout=30)
        zero_tasks = requests.get(f"{isolated.BASE}/lesson-tasks", headers=headers, timeout=30)
        zero_tasks.raise_for_status()
        zero_vault = requests.get(f"{isolated.BASE}/server-data/list", headers=headers, params={"path": PARENT, "task_owner": TEST_USER, "fresh": "1"}, timeout=30)
        zero_vault.raise_for_status()

        partial_post = requests.post(f"{isolated.BASE}/space-q/progress?response=compact-v1", headers=headers, json=progress_payload(lesson_id, 2, "surface-two"), timeout=30)
        partial_post.raise_for_status()
        partial_get = requests.get(f"{isolated.BASE}/space-q/progress", headers=headers, params={"path": RELATIVE, "identity": lesson_id}, timeout=30)
        partial_get.raise_for_status()
        partial_tasks = requests.get(f"{isolated.BASE}/lesson-tasks", headers=headers, timeout=30)
        partial_tasks.raise_for_status()
        partial_vault = requests.get(f"{isolated.BASE}/server-data/list", headers=headers, params={"path": PARENT, "task_owner": TEST_USER, "fresh": "1"}, timeout=30)
        partial_vault.raise_for_status()
        dom_runtime = run_dom_surface_probe(lesson_id)
        token = local_login()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        add = requests.post(f"{isolated.BASE}/lesson-tasks", headers=headers, json={"action": "add", "path": RELATIVE, "title": "Space_Q surface probe"}, timeout=30)
        add.raise_for_status()
        partial_tasks_with_manual = requests.get(f"{isolated.BASE}/lesson-tasks", headers=headers, timeout=30)
        partial_tasks_with_manual.raise_for_status()
        cpu_after = sum(process.cpu_times()[:2])

        zero_summary = zero_body.get("summary") or {}
        partial_summary = partial_get.json().get("summary") or {}
        zero_auto_task = task_progress(zero_tasks.json(), lesson_id, automatic=True)
        partial_task = task_progress(partial_tasks_with_manual.json(), lesson_id, automatic=False)
        partial_auto_task = task_progress(partial_tasks.json(), lesson_id, automatic=True)
        zero_vault_progress = vault_progress(zero_vault.json(), lesson_id)
        partial_vault_progress = vault_progress(partial_vault.json(), lesson_id)

        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_DISTRIBUTED_WORKER_PORT": "18890"})
        restart_health = wait_health(server)
        token = local_login()
        restart_headers = {"Authorization": f"Bearer {token}"}
        restart_progress = requests.get(f"{isolated.BASE}/space-q/progress", headers=restart_headers, params={"path": RELATIVE, "identity": lesson_id}, timeout=30)
        restart_progress.raise_for_status()
        restart_tasks_payload = wait_for_auto_task(restart_headers, lesson_id)
        restart_vault = requests.get(f"{isolated.BASE}/server-data/list", headers=restart_headers, params={"path": PARENT, "task_owner": TEST_USER, "fresh": "1"}, timeout=30)
        restart_vault.raise_for_status()
        restart_summary = restart_progress.json().get("summary") or {}
        restart_task = task_progress(restart_tasks_payload, lesson_id, automatic=False)
        restart_auto_task = task_progress(restart_tasks_payload, lesson_id, automatic=True)
        restart_vault_progress = vault_progress(restart_vault.json(), lesson_id)

        gates = {
            "fresh_snapshot": True,
            "zero_checkpoint_not_progress": (zero_summary.get("done"), zero_summary.get("total")) == (0, 48),
            "zero_auto_task_matches": (zero_auto_task.get("done"), zero_auto_task.get("total")) == (0, 48),
            "zero_vault_matches": (zero_vault_progress.get("done"), zero_vault_progress.get("total")) == (0, 48),
            "etag_is_real_304": unchanged.status_code == 304 and not unchanged.content,
            "partial_endpoint_matches": (partial_summary.get("done"), partial_summary.get("total")) == (2, 48),
            "partial_task_matches": (partial_task.get("done"), partial_task.get("total")) == (2, 48),
            "partial_auto_task_matches": (partial_auto_task.get("done"), partial_auto_task.get("total")) == (2, 48),
            "partial_vault_matches": (partial_vault_progress.get("done"), partial_vault_progress.get("total")) == (2, 48),
            "dom_runtime_matches": bool(dom_runtime.get("ok")) and (dom_runtime.get("after") or {}).get("row", {}).get("progressText") not in {"", "0/48"} and (dom_runtime.get("after") or {}).get("row", {}).get("progressText") == (dom_runtime.get("after") or {}).get("task", {}).get("progressText"),
            "interactive_exit_matches": bool((dom_runtime.get("interactive") or {}).get("afterExit")) and (dom_runtime.get("interactive") or {}).get("afterExit", {}).get("row", {}).get("progressText") == (dom_runtime.get("interactive") or {}).get("afterExit", {}).get("task", {}).get("progressText"),
            "restart_endpoint_matches": (restart_summary.get("done"), restart_summary.get("total")) == (2, 48),
            "restart_task_matches": (restart_task.get("done"), restart_task.get("total")) == (2, 48),
            "restart_auto_task_matches": (restart_auto_task.get("done"), restart_auto_task.get("total")) == (2, 48),
            "restart_vault_matches": (restart_vault_progress.get("done"), restart_vault_progress.get("total")) == (2, 48),
        }
        result = {
            "ok": all(gates.values()),
            "database_sync": {"enabled": True, "source": isolated.PRODUCTION_DSN, "method": "fresh pg_dump + pg_restore before run", "dump_bytes": dump_path.stat().st_size},
            "resources": {"http": isolated.BASE, "postgres_port": isolated.PG_PORT, "production_mutated": False},
            "lesson_id": lesson_id,
            "zero": {"summary": zero_summary, "auto_task": zero_auto_task, "vault": zero_vault_progress, "etag_status": unchanged.status_code},
            "partial": {"summary": partial_summary, "task": partial_task, "auto_task": partial_auto_task, "vault": partial_vault_progress, "dom_runtime": dom_runtime},
            "restart": {"health": restart_health, "summary": restart_summary, "task": restart_task, "auto_task": restart_auto_task, "vault": restart_vault_progress},
            "performance": {"server_cpu_ms_for_post_get_task_matrix": round((cpu_after - cpu_before) * 1000, 3)},
            "startup": {"ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "gates": gates,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"ok": result["ok"], "output": str(OUTPUT), "gates": gates, "cpu_ms": result["performance"]["server_cpu_ms_for_post_get_task_matrix"]}, ensure_ascii=True))
        if not result["ok"]:
            raise RuntimeError(f"Space_Q progress surface isolated gate failed: {gates}")
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
