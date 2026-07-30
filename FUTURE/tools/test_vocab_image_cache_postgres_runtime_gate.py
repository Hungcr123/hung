#!/usr/bin/env python3
"""Process runtime gate for vocab_image_cache with PostgreSQL routing."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
TEST_PREFIX = "codex-runtime-image-"

def cleanup_sqlite() -> int:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        cur = con.execute("DELETE FROM vocab_image_cache WHERE word_key LIKE ?", (f"{TEST_PREFIX}%",))
        con.commit()
        return int(cur.rowcount or 0)
    finally:
        con.close()

def cleanup_postgres() -> int:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.vocab_image_cache WHERE word_key LIKE %s", (f"{TEST_PREFIX}%",))
            return int(cursor.rowcount or 0)
    return app.postgres_execute(_write)

def subprocess_gate() -> dict:
    code = r'''
import json, time
import FUTURE.server_app as app
prefix = "codex-runtime-image-"
rows = [
    {"word_key": prefix + "alpha", "image": {"ok": True, "slot": "alpha"}, "expires_epoch": time.time() + 86400},
    {"word_key": prefix + "beta", "image": {"ok": True, "slot": "beta"}, "expires_epoch": time.time() + 86400},
]
stored_first = app.server_database_store_vocab_image_cache_batch(rows)
stored_retry = app.server_database_store_vocab_image_cache_batch(rows)
loaded = app.server_database_load_vocab_image_cache(prefix + "alpha") or {}
listed = app.server_database_load_vocab_image_cache_rows(10000)
print(json.dumps({
    "stored_first": stored_first,
    "stored_retry": stored_retry,
    "loaded_ok": bool((loaded.get("image") or {}).get("ok")),
    "listed_count": sum(1 for row in listed if str(row.get("word_key", "")).startswith(prefix)),
    "backend": app.postgres_backend_mode("VOCAB_IMAGE_CACHE"),
}, ensure_ascii=True))
'''
    env = dict(os.environ)
    env["FUTURE_DB_VOCAB_IMAGE_CACHE_BACKEND"] = "postgres"
    raw = subprocess.check_output([sys.executable, "-c", code], cwd=ROOT, env=env, text=True)
    return json.loads(raw)

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running vocab image cache PostgreSQL runtime gate.")
    cleanup_sqlite()
    cleanup_postgres()
    copy = json.loads(subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_vocab_image_cache_to_postgres.py")], cwd=ROOT, text=True))
    if not copy.get("parity"):
        raise RuntimeError(f"copy parity failed: {copy}")
    first = subprocess_gate()
    second = subprocess_gate()
    if first.get("backend") != "postgres" or second.get("backend") != "postgres":
        raise RuntimeError(f"runtime backend was not postgres: {first} {second}")
    if not first.get("loaded_ok") or int(first.get("listed_count", 0) or 0) < 2:
        raise RuntimeError(f"first runtime gate failed: {first}")
    if not second.get("loaded_ok") or int(second.get("listed_count", 0) or 0) < 2:
        raise RuntimeError(f"restart/subprocess readback failed: {second}")
    cleanup_pg = cleanup_postgres()
    cleanup_sq = cleanup_sqlite()
    final_verify = json.loads(subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_vocab_image_cache_to_postgres.py"), "--verify-only"], cwd=ROOT, text=True))
    result = {
        "ok": bool(final_verify.get("parity")),
        "copy": copy,
        "first_process": first,
        "second_process": second,
        "cleanup": {"postgres": cleanup_pg, "sqlite": cleanup_sq},
        "final_verify_only": final_verify,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
