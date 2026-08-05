#!/usr/bin/env python3
"""Fresh-snapshot HTTP gate for learner-triggered PDF/Picture AI notice audio repair."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import test_lesson_complete_isolated_harness as isolated
import test_pdf_ai_notice_postgres_isolated as notice_base

RUN_ROOT = ROOT / "programe_cache" / "pdf_ai_notice_audio_repair_18887"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\pdf_ai_notice_audio_repair_20260801.json")
ADMIN_USER = "codexnoticeadmin"
LEARNER_USERS = tuple(f"codexnoticelearner{index:02d}" for index in range(10))
ISOLATED_SERVER_ENV = {
    "FUTURE_DISTRIBUTED_WORKER_TOKEN": "codex-ai-notice-isolated-only",
    "FUTURE_DISTRIBUTED_WORKER_PORT": "18890",
    "FUTURE_VOICE_WORKER_PORT": "18767",
}


def configure() -> None:
    isolated.PG_PORT = 55442
    isolated.HTTP_PORT = 18887
    isolated.BASE = f"http://127.0.0.1:{isolated.HTTP_PORT}"
    isolated.TEST_DATABASE = "future_server2_ai_notice_copy"
    isolated.PG_DSN = f"postgresql://future_server2_app@127.0.0.1:{isolated.PG_PORT}/{isolated.TEST_DATABASE}"
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    notice_base.RUN_ROOT = RUN_ROOT


def provision_users() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = "2026-08-01T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for username, is_admin in ((ADMIN_USER, True), *((username, False) for username in LEARNER_USERS)):
            cursor.execute(
                """INSERT INTO future_server2.users
                   (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,%s,true,%s,%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET is_admin=excluded.is_admin,is_test=true,profile_json=excluded.profile_json""",
                (username, is_admin, Jsonb({"source": "isolated-ai-notice-audio-repair"}), now),
            )
            cursor.execute(
                """INSERT INTO future_server2.user_auth_credentials
                   (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,%s,'isolated-ai-notice-audio-repair',%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
                (username, isolated.password_hash(isolated.PASSWORD), now),
            )
            if is_admin:
                cursor.execute(
                    """INSERT INTO future_server2.admin_users
                       (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                       VALUES (%s,true,%s,0,'','isolated-ai-notice-audio-repair')
                       ON CONFLICT (username) DO UPDATE SET enabled=true,updated_at_utc=excluded.updated_at_utc""",
                    (username, now),
                )


def auth_headers(username: str) -> dict[str, str]:
    response = requests.post(
        f"{isolated.BASE}/auth/login",
        json={"username": username, "password": isolated.PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def sound_index_assets() -> dict[str, str]:
    index_file = isolated.SERVER_DATA_ROOT / "_future_sound_asset_index.json"
    wal_file = isolated.SERVER_DATA_ROOT / "_future_sound_asset_index.wal.jsonl"
    payload = json.loads(index_file.read_text(encoding="utf-8-sig")) if index_file.is_file() else {}
    assets = dict(payload.get("assets") or {})
    if wal_file.is_file():
        for line in wal_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            digest = str(row.get("digest") or "").lower()
            extension = str(row.get("extension") or "").lower()
            path = str(row.get("path") or "")
            if digest and extension and path:
                assets[f"{digest}.{extension}"] = path
    return assets


def sound_index_key(audio_path: str) -> str:
    match = re.search(r"_([0-9a-fA-F]{40})\.([0-9A-Za-z]+)$", Path(audio_path).name)
    if not match:
        raise RuntimeError(f"audio path has no sound digest: {audio_path}")
    return f"{match.group(1).lower()}.{match.group(2).lower()}"


def remove_exact_sound_index_entry(key: str) -> tuple[int, int]:
    index_file = isolated.SERVER_DATA_ROOT / "_future_sound_asset_index.json"
    wal_file = isolated.SERVER_DATA_ROOT / "_future_sound_asset_index.wal.jsonl"
    payload = json.loads(index_file.read_text(encoding="utf-8-sig")) if index_file.is_file() else {"assets": {}}
    assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
    before = len(assets)
    assets.pop(key, None)
    payload["assets"] = assets
    index_file.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if wal_file.is_file():
        kept = []
        for line in wal_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                kept.append(line)
                continue
            row_key = f"{str(row.get('digest') or '').lower()}.{str(row.get('extension') or '').lower()}"
            if row_key != key:
                kept.append(line)
        wal_file.write_text(("\n".join(kept) + "\n") if kept else "", encoding="utf-8")
    return before, len(assets)


def stop_processes_holding_run_files() -> None:
    server_log = str(isolated.SERVER_LOG.resolve()).lower()
    for process in psutil.process_iter(["pid"]):
        try:
            if process.pid == os.getpid():
                continue
            if process.name().lower().startswith("postgres"):
                continue
            if any(str(item.path).lower() == server_log for item in (process.open_files() or [])):
                process.terminate()
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    process.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass


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
        production_pattern_root = Path(r"C:\server data\Sound\_v2\chat\202608")
        production_before = {str(path) for path in production_pattern_root.rglob("chat-kokoro-af_jessica-Audio-repair-*")} if production_pattern_root.is_dir() else set()
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        provision_users()
        notice_base.copy_media()
        server = isolated.start_server(no_preload=True, extra_env=ISOLATED_SERVER_ENV)
        health = isolated.wait_health(server)
        admin_headers = auth_headers(ADMIN_USER)
        learner_headers_by_user = {username: auth_headers(username) for username in LEARNER_USERS}
        process = psutil.Process(server.pid)
        rows = []

        for mode_index, (path, mode) in enumerate((("common/proof.pdf", "pdf"), ("common/proof.png", "picture"))):
            learner_headers = learner_headers_by_user[LEARNER_USERS[mode_index]]
            save_response = requests.post(
                f"{isolated.BASE}/space-pdf/ai-region-notices",
                headers=admin_headers,
                json={
                    "path": path,
                    "mode": mode,
                    "page": 1,
                    "rect": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2},
                    "text": f"Notice repair {mode}",
                    "audioText": f"Audio repair {mode}",
                    "voice": "kokoro:af_jessica",
                    "speakMode": "click",
                },
                timeout=30,
            )
            save_response.raise_for_status()
            saved = save_response.json().get("notice") or {}
            if saved.get("audio_path") or saved.get("audioPath"):
                raise RuntimeError(f"normal save unexpectedly generated audio: {saved}")

            before_cpu = sum(process.cpu_times()[:2])
            started = time.perf_counter()
            repair_response = requests.post(
                f"{isolated.BASE}/space-pdf/ai-region-notices",
                headers=learner_headers,
                json={"path": path, "mode": mode, "page": 1, "id": saved.get("id"), "action": "ensure_audio"},
                timeout=180,
            )
            repair_wall_ms = (time.perf_counter() - started) * 1000
            repair_cpu_ms = (sum(process.cpu_times()[:2]) - before_cpu) * 1000
            if not repair_response.ok:
                raise RuntimeError(f"learner repair HTTP {repair_response.status_code}: {repair_response.text[:1200]}")
            repaired_payload = repair_response.json()
            repaired = repaired_payload.get("notice") or {}
            audio_path = str(repaired.get("audio_path") or repaired.get("audioPath") or "")
            audio_file = isolated.SERVER_DATA_ROOT / audio_path
            if not repaired_payload.get("audio_ready") or not audio_path or not audio_file.is_file() or audio_file.stat().st_size <= 0:
                raise RuntimeError(f"learner repair did not create a durable audio file: {repaired_payload}")

            repeat_started = time.perf_counter()
            repeat_response = requests.post(
                f"{isolated.BASE}/space-pdf/ai-region-notices",
                headers=learner_headers,
                json={"path": path, "mode": mode, "page": 1, "id": saved.get("id"), "action": "ensure_audio"},
                timeout=30,
            )
            repeat_wall_ms = (time.perf_counter() - repeat_started) * 1000
            repeat_response.raise_for_status()
            repeat_payload = repeat_response.json()
            if repeat_payload.get("audio_repaired") or str((repeat_payload.get("notice") or {}).get("audio_path") or (repeat_payload.get("notice") or {}).get("audioPath") or "") != audio_path:
                raise RuntimeError(f"ready audio was rebuilt instead of reused: {repeat_payload}")
            rows.append({
                "mode": mode,
                "id": saved.get("id"),
                "path": path,
                "audio_path": audio_path,
                "index_key": sound_index_key(audio_path),
                "audio_bytes": audio_file.stat().st_size,
                "repair_wall_ms": round(repair_wall_ms, 3),
                "server_cpu_ms": round(repair_cpu_ms, 3),
                "ready_reuse_wall_ms": round(repeat_wall_ms, 3),
            })

        isolated.stop_server(server)
        server = None
        stop_processes_holding_run_files()
        index_after_create = sound_index_assets()
        for row in rows:
            if index_after_create.get(row["index_key"]) != row["audio_path"]:
                raise RuntimeError(f"created audio missing from sound index: {row}")
        picture_row = next(row for row in rows if row["mode"] == "picture")
        index_count_before_remove, index_count_after_remove = remove_exact_sound_index_entry(picture_row["index_key"])
        if picture_row["index_key"] in sound_index_assets() or not (isolated.SERVER_DATA_ROOT / picture_row["audio_path"]).is_file():
            raise RuntimeError("failed to create physical-file/index-missing fixture")

        server = isolated.start_server(no_preload=True, extra_env=ISOLATED_SERVER_ENV)
        restart_health = isolated.wait_health(server)
        learner_headers_by_user = {username: auth_headers(username) for username in LEARNER_USERS}
        learner_headers = learner_headers_by_user[LEARNER_USERS[1]]
        index_repair_response = requests.post(
            f"{isolated.BASE}/space-pdf/ai-region-notices",
            headers=learner_headers,
            json={"path": picture_row["path"], "mode": "picture", "page": 1, "id": picture_row["id"], "action": "ensure_audio"},
            timeout=30,
        )
        index_repair_response.raise_for_status()
        index_repair_payload = index_repair_response.json()
        if index_repair_payload.get("audio_repaired") or not index_repair_payload.get("sound_index_repaired"):
            raise RuntimeError(f"existing file did not receive exact index-only repair: {index_repair_payload}")

        pdf_row = next(row for row in rows if row["mode"] == "pdf")
        pdf_audio_file = isolated.SERVER_DATA_ROOT / pdf_row["audio_path"]
        pdf_audio_file.unlink()
        if pdf_audio_file.exists():
            raise RuntimeError("failed to create audioPath-present/file-missing fixture")
        process = psutil.Process(server.pid)
        concurrent_cpu_before = sum(process.cpu_times()[:2])
        concurrent_started = time.perf_counter()

        def click_missing_pdf(user_index: int) -> dict:
            response = requests.post(
                f"{isolated.BASE}/space-pdf/ai-region-notices",
                headers=learner_headers_by_user[LEARNER_USERS[user_index]],
                json={"path": pdf_row["path"], "mode": "pdf", "page": 1, "id": pdf_row["id"], "action": "ensure_audio"},
                timeout=180,
            )
            if not response.ok:
                raise RuntimeError(f"concurrent repair HTTP {response.status_code}: {response.text[:800]}")
            return response.json()

        with ThreadPoolExecutor(max_workers=8) as executor:
            concurrent_payloads = list(executor.map(click_missing_pdf, range(8)))
        concurrent_wall_ms = (time.perf_counter() - concurrent_started) * 1000
        concurrent_cpu_ms = (sum(process.cpu_times()[:2]) - concurrent_cpu_before) * 1000
        concurrent_tts_winners = sum(1 for payload in concurrent_payloads if payload.get("audio_repaired"))
        if concurrent_tts_winners != 1 or not pdf_audio_file.is_file():
            raise RuntimeError(f"concurrent missing-file repair was not single-flight: winners={concurrent_tts_winners}")

        second_pdf = requests.post(
            f"{isolated.BASE}/space-pdf/ai-region-notices",
            headers=learner_headers_by_user[LEARNER_USERS[0]],
            json={"path": pdf_row["path"], "mode": "pdf", "page": 1, "id": pdf_row["id"], "action": "ensure_audio"},
            timeout=30,
        ).json()
        if second_pdf.get("audio_repaired"):
            raise RuntimeError(f"second PDF click rebuilt ready audio: {second_pdf}")

        isolated.stop_server(server)
        server = None
        stop_processes_holding_run_files()
        server = isolated.start_server(no_preload=True, extra_env=ISOLATED_SERVER_ENV)
        final_restart_health = isolated.wait_health(server)
        learner_headers = auth_headers(LEARNER_USERS[0])
        restart_ready = {}
        for path, mode in (("common/proof.pdf", "pdf"), ("common/proof.png", "picture")):
            payload = requests.get(
                f"{isolated.BASE}/space-pdf/ai-region-notices",
                headers=learner_headers,
                params={"path": path, "mode": mode, "page": 1},
                timeout=30,
            ).json()
            notice = (payload.get("notices") or [{}])[0]
            audio_path = str(notice.get("audio_path") or notice.get("audioPath") or "")
            key = sound_index_key(audio_path) if audio_path else ""
            restart_ready[mode] = bool(audio_path and (isolated.SERVER_DATA_ROOT / audio_path).is_file() and sound_index_assets().get(key) == audio_path)

        production_after = {str(path) for path in production_pattern_root.rglob("chat-kokoro-af_jessica-Audio-repair-*")} if production_pattern_root.is_dir() else set()

        result = {
            "ok": restart_ready == {"pdf": True, "picture": True} and production_after == production_before,
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "resources": {"http": isolated.BASE, "postgres": isolated.PG_PORT, "production_mutated": False},
            "health": {"ready": health.get("ready"), "index_restart_ready": restart_health.get("ready"), "final_restart_ready": final_restart_health.get("ready")},
            "repair": rows,
            "index_missing": {
                "entries_before": index_count_before_remove,
                "entries_after_fixture": index_count_after_remove,
                "tts_calls": 0,
                "sound_index_repaired": index_repair_payload.get("sound_index_repaired"),
            },
            "file_missing_concurrency": {
                "clicks": 8,
                "tts_winners": concurrent_tts_winners,
                "wall_ms": round(concurrent_wall_ms, 3),
                "server_cpu_ms": round(concurrent_cpu_ms, 3),
                "second_click_reused": not bool(second_pdf.get("audio_repaired")),
            },
            "restart_audio_ready": restart_ready,
            "sound_index": {"full_rebuild_requested": False, "exact_entry_repairs_only": True},
            "production_sound_files_changed": sorted(production_after.symmetric_difference(production_before)),
        }
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        if RUN_ROOT.exists():
            stop_processes_holding_run_files()
            shutil.rmtree(RUN_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
