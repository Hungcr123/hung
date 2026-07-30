"""Run the QM City newest-state merge against a fresh isolated PostgreSQL snapshot."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools import test_lesson_complete_isolated_harness as isolated


MERGE_TOOL = ROOT / "FUTURE" / "tools" / "migrate_qm_city_runtime_newest_to_postgres.py"
EVIDENCE = Path(r"C:\Users\Admin\.codex\plans\qm_city_runtime_merge_isolated_20260730.json")
BACKUP = Path(r"C:\Users\Admin\.codex\plans\qm_city_runtime_merge_isolated_before.json")


def run_merge(environment: dict[str, str], apply: bool) -> dict:
    command = [sys.executable, str(MERGE_TOOL)]
    if apply:
        command.extend(("--apply", "--backup", str(BACKUP)))
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def seed_stale_training_row() -> None:
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT path_key,content,encoding FROM future_server2.documents "
            "WHERE lower(path) LIKE %s LIMIT 1",
            ("%_future_qm_city_training.json",),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("isolated QM City training document is missing")
        payload = json.loads(bytes(row[1] or b"").decode(str(row[2] or "utf-8"), errors="replace"))
        users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
        vietanh = users.get("vietanh") if isinstance(users.get("vietanh"), dict) else {}
        vietanh["updated_at"] = "2000-01-01T00:00:00Z"
        users["vietanh"] = vietanh
        payload["users"] = users
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        cursor.execute(
            "UPDATE future_server2.documents SET content=%s,encoding='utf-8',sha256=%s,file_size=%s WHERE path_key=%s",
            (content, hashlib.sha256(content).hexdigest(), len(content), row[0]),
        )


def main() -> int:
    postgres = None
    evidence = {}
    try:
        postgres = isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        seed_stale_training_row()
        environment = isolated.app_env()
        before = run_merge(environment, False)
        applied = run_merge(environment, True)
        after = run_merge(environment, False)
        evidence = {
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {"postgres_port": isolated.PG_PORT, "database": isolated.TEST_DATABASE},
            "before": before,
            "applied": applied,
            "after": after,
            "passed": before.get("write_count") == 1 and applied.get("applied") is True and after.get("write_count") == 0,
        }
        EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        if not evidence["passed"]:
            raise AssertionError(evidence)
        print(json.dumps({"ok": True, "evidence": str(EVIDENCE), "dump_bytes": dump_path.stat().st_size}, ensure_ascii=False))
        return 0
    finally:
        isolated.stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
