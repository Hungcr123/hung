#!/usr/bin/env python3
"""Fresh-snapshot durability and CPU gate for PDF/Picture AI notices."""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "pdf_ai_notice_isolated_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\pdf_ai_notice_postgres_isolated_20260730.json")
TEST_USER = "codexpdfainotice"
PDF_SOURCE = Path(r"C:\server data\common\Ngữ pháp\Ngữ pháp\Động từ khuyết thiếu\Lý thuyết\Giao_trinh_Dong_tu_khuyet_thieu_tieng_anh.pdf")
PICTURE_SOURCE = Path(r"C:\server data\_assets\picture\fb\ftg-asset-fbec152ef488f69ad78cfe4f0081d794593652bdc4d6add141421de18741cb0a.png")


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def provision_admin() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = "2026-07-30T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,true,true,%s,%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET is_admin=true,is_test=true,profile_json=excluded.profile_json""",
            (TEST_USER, Jsonb({"source": "isolated-pdf-ai-notice"}), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.user_auth_credentials
               (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,'isolated-pdf-ai-notice',%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
            (TEST_USER, isolated.password_hash(isolated.PASSWORD), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.admin_users
               (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,true,%s,0,'','isolated-pdf-ai-notice')
               ON CONFLICT (username) DO UPDATE SET enabled=true,updated_at_utc=excluded.updated_at_utc""",
            (TEST_USER, now),
        )


def copy_media() -> None:
    for source, relative in ((PDF_SOURCE, "common/proof.pdf"), (PICTURE_SOURCE, "common/proof.png")):
        target = isolated.SERVER_DATA_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for directory in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / directory).mkdir(parents=True, exist_ok=True)


def auth_headers() -> dict[str, str]:
    response = requests.post(f"{isolated.BASE}/auth/login", json={"username": TEST_USER, "password": isolated.PASSWORD}, timeout=30)
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def save_notice(process: psutil.Process, headers: dict[str, str], path: str, mode: str, marker: str) -> tuple[dict, float, float]:
    before = sum(process.cpu_times()[:2])
    started = time.perf_counter()
    response = requests.post(
        f"{isolated.BASE}/space-pdf/ai-region-notices",
        headers=headers,
        json={
            "path": path,
            "mode": mode,
            "page": 1,
            "rect": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2},
            "text": f"AI notice {marker}",
            "audioText": f"AI notice voice {marker}",
            "voice": "kokoro:af_jessica",
        },
        timeout=30,
    )
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_ms = (sum(process.cpu_times()[:2]) - before) * 1000
    response.raise_for_status()
    return response.json(), wall_ms, cpu_ms


def save_question(headers: dict[str, str]) -> dict:
    started = time.perf_counter()
    response = requests.post(
        f"{isolated.BASE}/space-pdf/ai-region-questions",
        headers=headers,
        json={
            "path": "common/proof.pdf",
            "mode": "pdf",
            "page": 1,
            "rect": {"x": 0.2, "y": 0.2, "w": 0.25, "h": 0.15},
            "question": "Which word completes this sentence?",
            "questionType": "input",
            "answers": [{
                "text": "answer",
                "correct": True,
                "explanationMode": "text_voice",
                "explanationText": "The correct answer is answer.",
                "explanationVoice": "kokoro:af_jessica",
            }],
            "mikasaIntro": "Choose the best answer.",
            "voice": "kokoro:af_jessica",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    payload["save_wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return payload


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
        dump = isolated.sync_production_database_snapshot()
        provision_admin()
        copy_media()
        server = isolated.start_server(no_preload=True)
        health = isolated.wait_health(server)
        headers = auth_headers()
        process = psutil.Process(server.pid)

        saved_rows = []
        for path, mode in (("common/proof.pdf", "pdf"), ("common/proof.png", "picture")):
            saved, wall_ms, cpu_ms = save_notice(process, headers, path, mode, mode)
            notice = saved.get("notice") or {}
            if not notice or notice.get("audio_path") or notice.get("audioPath"):
                raise RuntimeError(f"normal save unexpectedly blocked on/generated TTS: {saved}")
            read = requests.get(f"{isolated.BASE}/space-pdf/ai-region-notices", headers=headers, params={"path": path, "page": 1, "mode": mode}, timeout=30).json()
            if len(read.get("notices") or []) != 1:
                raise RuntimeError(f"notice readback failed: {read}")
            saved_rows.append({"mode": mode, "key": saved.get("key"), "wall_ms": round(wall_ms, 3), "server_cpu_ms": round(cpu_ms, 3)})

        question_saved = save_question(headers)
        saved_question = question_saved.get("question") or {}
        saved_answers = saved_question.get("answers") or []
        if not saved_question.get("introAudioJobId") or not saved_answers or not saved_answers[0].get("audioJobId"):
            raise RuntimeError(f"AI Question did not register durable audio jobs: {question_saved}")
        if saved_question.get("introAudioPath") or saved_answers[0].get("audioPath"):
            raise RuntimeError(f"AI Question save unexpectedly waited for audio: {question_saved}")
        if float(question_saved.get("save_wall_ms", 0) or 0) > 5000:
            raise RuntimeError(f"AI Question content ACK was too slow: {question_saved}")
        question_read = requests.get(f"{isolated.BASE}/space-pdf/ai-region-questions", headers=headers, params={"path": "common/proof.pdf", "page": 1, "mode": "pdf"}, timeout=30).json()
        if len(question_read.get("questions") or []) != 1:
            raise RuntimeError(f"question readback failed: {question_read}")

        before = sum(process.cpu_times()[:2])
        started = time.perf_counter()
        for _index in range(200):
            response = requests.get(f"{isolated.BASE}/space-pdf/ai-region-notices", headers=headers, params={"path": "common/proof.pdf", "page": 1, "mode": "pdf"}, timeout=30)
            response.raise_for_status()
        get_wall_ms = (time.perf_counter() - started) * 1000
        get_cpu_ms = (sum(process.cpu_times()[:2]) - before) * 1000

        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True)
        restart_health = isolated.wait_health(server)
        headers = auth_headers()
        restart_counts = {}
        for path, mode in (("common/proof.pdf", "pdf"), ("common/proof.png", "picture")):
            payload = requests.get(f"{isolated.BASE}/space-pdf/ai-region-notices", headers=headers, params={"path": path, "page": 1, "mode": mode}, timeout=30).json()
            restart_counts[mode] = len(payload.get("notices") or [])
        question_restart = requests.get(f"{isolated.BASE}/space-pdf/ai-region-questions", headers=headers, params={"path": "common/proof.pdf", "page": 1, "mode": "pdf"}, timeout=30).json()

        result = {
            "ok": restart_counts == {"pdf": 1, "picture": 1} and len(question_restart.get("questions") or []) == 1,
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "resources": {"http": isolated.BASE, "postgres": isolated.PG_PORT, "production_mutated": False},
            "health": {"ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "normal_save_without_tts": saved_rows,
            "question_save": {
                "key": question_saved.get("key"),
                "read_count": len(question_read.get("questions") or []),
                "restart_count": len(question_restart.get("questions") or []),
                "save_wall_ms": question_saved.get("save_wall_ms"),
                "intro_job_id": saved_question.get("introAudioJobId"),
                "answer_job_id": saved_answers[0].get("audioJobId"),
            },
            "hot_get_200": {"wall_ms": round(get_wall_ms, 3), "server_cpu_ms": round(get_cpu_ms, 3), "cpu_ms_per_request": round(get_cpu_ms / 200, 4)},
            "restart": {"ready": restart_health.get("ready"), "counts": restart_counts},
        }
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        if RUN_ROOT.exists():
            shutil.rmtree(RUN_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
