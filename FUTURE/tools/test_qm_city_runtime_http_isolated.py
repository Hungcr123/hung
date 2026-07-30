"""Exercise QM City PostgreSQL reads/writes/restart on a fresh isolated snapshot."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools import test_lesson_complete_isolated_harness as isolated


RUN_ROOT = ROOT / "programe_cache" / "qm_city_runtime_isolated_18877"
EVIDENCE = Path(r"C:\Users\Admin\.codex\plans\qm_city_runtime_http_isolated_20260730.json")
USER_A = "codexqmcity001"
USER_B = "codexqmcity002"


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    isolated.TEST_USER = USER_A
    isolated.RECOVERY_USER = USER_B
    isolated.PASSWORD = "IsolatedQmCity9"


def request(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    response = requests.request(
        method,
        f"{isolated.BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path}: HTTP {response.status_code} {response.text[:500]}")
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"{method} {path}: {body}")
    return body


def document_payload(name: str) -> dict:
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT content,encoding FROM future_server2.documents WHERE lower(path)=lower(%s)",
            (str(isolated.SERVER_DATA_ROOT / name),),
        )
        row = cursor.fetchone()
    if row is None:
        return {}
    return json.loads(bytes(row[0] or b"").decode(str(row[1] or "utf-8"), errors="replace"))


def legacy_files() -> list[str]:
    names = (
        "_future_qm_city_training.json",
        "_future_shared_world.json",
        "_future_shared_world_keyboard_passes.json",
        "_future_shared_world_battles.json",
        "_future_shared_world_battle_word_history.json",
        "_future_vocab_leaderboard_periods.wal.jsonl",
        "server2.db",
    )
    return [str(isolated.SERVER_DATA_ROOT / name) for name in names if (isolated.SERVER_DATA_ROOT / name).exists()]


def main() -> int:
    configure()
    if RUN_ROOT.exists():
        shutil.rmtree(RUN_ROOT)
    server = None
    database = None
    try:
        database = isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        copied_registry_rows = isolated.provision_postgres()
        with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO future_server2.admin_users (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) "
                "VALUES (%s,true,now(),extract(epoch from now()),now(),'isolated-qm-city') "
                "ON CONFLICT (username) DO UPDATE SET enabled=true",
                (USER_A,),
            )
        server = isolated.start_server(no_preload=True)
        health_before = isolated.wait_health(server)
        token_a = isolated.login(USER_A)
        token_b = isolated.login(USER_B)

        reads = {
            path: request(token_a, "GET", path)
            for path in ("/world/state", "/world/training/state", "/world/battle/state", "/world/keyboard-pass", "/game/state")
        }
        moved = request(token_a, "POST", "/world/move", {"x": 0.37, "y": 0.61})
        keyboard = request(token_a, "POST", "/world/keyboard-pass", {})
        reset = request(token_a, "POST", "/world/training/reset", {})
        invited = request(token_a, "POST", "/world/battle/invite", {"target": USER_B, "game": "fireball_vocab"})
        invite_id = str((invited.get("invite") or {}).get("id") or "")
        if not invite_id:
            raise RuntimeError(f"battle invite missing id: {invited}")
        responded = request(token_b, "POST", "/world/battle/respond", {"invite_id": invite_id, "accept": True})
        time.sleep(3)

        before_restart = {
            "training": document_payload("_future_qm_city_training.json"),
            "world": document_payload("_future_shared_world.json"),
            "keyboard": document_payload("_future_shared_world_keyboard_passes.json"),
            "battle": document_payload("_future_shared_world_battles.json"),
            "legacy_files": legacy_files(),
        }
        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True)
        health_after = isolated.wait_health(server)
        token_after = isolated.login(USER_A)
        restored_training = request(token_after, "GET", "/world/training/state")
        restored_world = request(token_after, "GET", "/world/state")
        restored_keyboard = request(token_after, "GET", "/world/keyboard-pass")
        restored_battle = request(token_after, "GET", "/world/battle/state")
        after_restart = {
            "training": document_payload("_future_qm_city_training.json"),
            "world": document_payload("_future_shared_world.json"),
            "keyboard": document_payload("_future_shared_world_keyboard_passes.json"),
            "battle": document_payload("_future_shared_world_battles.json"),
            "legacy_files": legacy_files(),
        }

        training_users = before_restart["training"].get("users", {})
        world_players = before_restart["world"].get("players", {})
        keyboard_users = before_restart["keyboard"].get("users", {})
        battles = before_restart["battle"].get("battles", {})
        passed = bool(
            health_before.get("postgres_writer", {}).get("postgres_only")
            and USER_A in training_users
            and USER_A in world_players
            and USER_A in keyboard_users
            and battles
            and not before_restart["legacy_files"]
            and not after_restart["legacy_files"]
            and USER_A in after_restart["training"].get("users", {})
            and USER_A in after_restart["world"].get("players", {})
            and USER_A in after_restart["keyboard"].get("users", {})
            and after_restart["battle"].get("battles")
        )
        evidence = {
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump.stat().st_size,
            },
            "resources": {"http_port": isolated.HTTP_PORT, "postgres_port": isolated.PG_PORT, "database": isolated.TEST_DATABASE},
            "copied_registry_rows": copied_registry_rows,
            "health_before": {"ready": health_before.get("ready"), "warm_ready": health_before.get("warm_ready"), "postgres_writer": health_before.get("postgres_writer")},
            "health_after": {"ready": health_after.get("ready"), "warm_ready": health_after.get("warm_ready"), "postgres_writer": health_after.get("postgres_writer")},
            "route_reads": {path: body.get("ok") for path, body in reads.items()},
            "mutations": {"move": moved.get("ok"), "keyboard": keyboard.get("ok"), "reset": reset.get("ok"), "invite": invited.get("ok"), "respond": responded.get("ok")},
            "before_restart": {"training_user": USER_A in training_users, "world_player": USER_A in world_players, "keyboard_user": USER_A in keyboard_users, "battle_count": len(battles), "legacy_files": before_restart["legacy_files"]},
            "after_restart": {"training_user": USER_A in after_restart["training"].get("users", {}), "world_player": USER_A in after_restart["world"].get("players", {}), "keyboard_user": USER_A in after_restart["keyboard"].get("users", {}), "battle_count": len(after_restart["battle"].get("battles", {})), "legacy_files": after_restart["legacy_files"]},
            "dom_payload_restore": {"training": bool(restored_training.get("training")), "world": bool(restored_world.get("world")), "keyboard": bool(restored_keyboard.get("keyboard_pass", {}).get("enabled")), "battle": isinstance(restored_battle.get("battle"), (dict, type(None)))},
            "passed": passed,
        }
        EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        if not passed:
            raise AssertionError(evidence)
        print(json.dumps({"ok": True, "evidence": str(EVIDENCE), "dump_bytes": dump.stat().st_size}, ensure_ascii=False))
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())

