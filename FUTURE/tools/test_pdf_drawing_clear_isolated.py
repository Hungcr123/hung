#!/usr/bin/env python3
"""Fresh-snapshot proof that a PDF drawing clear is a durable tombstone."""

from __future__ import annotations

import json
import secrets
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import psycopg

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import test_lesson_complete_isolated_harness as isolated

isolated.RUN_ROOT = ROOT / "programe_cache" / "pdf_drawing_clear_isolated_18877"
isolated.PG_ROOT = isolated.RUN_ROOT / "postgres"
isolated.SERVER_DATA_ROOT = isolated.RUN_ROOT / "server-data"
isolated.RUNTIME_ROOT = isolated.RUN_ROOT / "runtime"
isolated.QMLEARN_ROOT = isolated.RUN_ROOT / "qml"
isolated.SERVER_LOG = isolated.RUN_ROOT / "server.log"
isolated.PG_LOG = isolated.RUN_ROOT / "postgres.log"
isolated.TEST_USER = "codexpdfclear"
isolated.PASSWORD = secrets.token_urlsafe(24)
isolated.LESSON_SOURCE = Path(r"C:\server data\common\Ngữ pháp\Ngữ pháp\Động từ khuyết thiếu\Lý thuyết\Giao_trinh_Dong_tu_khuyet_thieu_tieng_anh.pdf")
isolated.LESSON_PATH = "common/proof.pdf"


def main() -> int:
    if isolated.RUN_ROOT.exists():
        shutil.rmtree(isolated.RUN_ROOT)
    isolated.RUN_ROOT.mkdir(parents=True)
    server = None
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        isolated.provision_postgres()
        isolated.copy_lesson()
        server = isolated.start_server(no_preload=True)
        isolated.wait_health(server)
        login = requests.post(f"{isolated.BASE}/auth/login", json={"username": isolated.TEST_USER, "password": isolated.PASSWORD}, timeout=30)
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        base = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        common = {"path": isolated.LESSON_PATH, "identity": "proof-pdf", "title": "proof", "mode": "pdf", "page": 1, "clientUpdatedAt": base}
        vector = {"version": 2, "width": 1000, "height": 1000, "items": [{"kind": "pen", "points": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]}]}
        saved = requests.post(f"{isolated.BASE}/space-pdf/drawing", headers=headers, json={**common, "operationId": "proof-save", "vector": vector, "baseRevision": 0}, timeout=30).json()["drawing"]
        page2 = requests.post(f"{isolated.BASE}/space-pdf/drawing", headers=headers, json={**common, "page": 2, "operationId": "proof-save-page2", "vector": vector, "baseRevision": 0}, timeout=30).json()["drawing"]
        # Seed a legacy/path-only row to prove Clear All removes old aliases too.
        with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.pdf_drawings
                    (username,document_key,page,progress_key,path,identity,title,mode,drawing_json,content_hash,last_operation_id,server_revision,updated_at_utc,updated_epoch,updated_by,deleted,file_id,migrated_at_utc,source_sha256)
                VALUES (%s,%s,1,%s,%s,%s,'proof','pdf',%s::jsonb,'legacy-hash','legacy-save',1,%s,extract(epoch from now()),%s,false,'proof-pdf','', 'legacy-sha')
                ON CONFLICT DO NOTHING
                """,
                (isolated.TEST_USER, "legacy-proof-key", "legacy-key", isolated.LESSON_PATH, "server-proof-legacy", '{"page":1,"dataUrl":"data:image/png;base64,LEGACY","vector":{"items":[{"kind":"pen","points":[{"x":5,"y":5}]}]}}', base, isolated.TEST_USER),
            )
            connection.commit()
            cursor.execute("SELECT count(*) FROM future_server2.pdf_drawings WHERE username=%s AND path=%s AND page=1", (isolated.TEST_USER, isolated.LESSON_PATH))
            before_alias_count = int(cursor.fetchone()[0])
        cleared = requests.post(f"{isolated.BASE}/space-pdf/drawing", headers=headers, json={**common, "operationId": "proof-clear", "action": "clear", "baseRevision": saved["serverRevision"]}, timeout=30).json()["drawing"]
        read = requests.get(f"{isolated.BASE}/space-pdf/drawing", headers=headers, params={"path": isolated.LESSON_PATH, "identity": "proof-pdf", "page": 1}, timeout=30).json()["drawing"]
        before_restart = read.copy()
        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True)
        isolated.wait_health(server)
        restart = requests.get(f"{isolated.BASE}/space-pdf/drawing", headers=headers, params={"path": isolated.LESSON_PATH, "identity": "proof-pdf", "page": 1}, timeout=30).json()["drawing"]
        with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.pdf_drawings WHERE username=%s AND path=%s AND page=1 AND deleted=false", (isolated.TEST_USER, isolated.LESSON_PATH))
            after_live_rows = int(cursor.fetchone()[0])
            cursor.execute("SELECT count(*) FROM future_server2.pdf_drawings WHERE username=%s AND path=%s AND page=1", (isolated.TEST_USER, isolated.LESSON_PATH))
            after_all_rows = int(cursor.fetchone()[0])
        page2_read = requests.get(f"{isolated.BASE}/space-pdf/drawing", headers=headers, params={"path": isolated.LESSON_PATH, "identity": "proof-pdf", "page": 2}, timeout=30).json()["drawing"]
        result = {"ok": bool(saved.get("serverRevision") == 1 and page2.get("serverRevision") == 1 and cleared.get("deleted") and not (read.get("vector") or {}).get("items") and restart == before_restart and before_alias_count >= 2 and after_live_rows == 0 and after_all_rows == 1 and (page2_read.get("vector") or {}).get("items")), "database_sync": {"enabled": True, "dump_bytes": dump.stat().st_size}, "resources": {"http": isolated.BASE, "postgres": isolated.PG_PORT, "production_mutated": False}, "saved_revision": saved.get("serverRevision"), "cleared_revision": cleared.get("serverRevision"), "read_deleted": read.get("deleted"), "read_items": len((read.get("vector") or {}).get("items") or []), "restart_deleted": restart.get("deleted"), "before_alias_count": before_alias_count, "after_live_rows": after_live_rows, "after_all_rows": after_all_rows, "page2_items": len((page2_read.get("vector") or {}).get("items") or [])}
        evidence = Path(r"C:\Users\Admin\.codex\plans\pdf_drawing_clear_isolated_20260730.json")
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        if isolated.RUN_ROOT.exists():
            shutil.rmtree(isolated.RUN_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
