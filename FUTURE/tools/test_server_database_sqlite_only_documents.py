import json
import sys
import tempfile
import time
import atexit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def reset_database(root: Path) -> None:
    app.SERVER_DATA_ROOT = root / "server-data"
    app.USER_ROOT = root / "users"
    app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
    app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
    app.SERVER_DATABASE_READY = False
    app.SERVER_DATABASE_READY_STATUS = {}
    app.SERVER_DATABASE_DOCUMENT_CACHE.clear()
    app.INVENTORY_RAM_CACHE.clear()
    app.initialize_server_database()


def store(path: Path, payload: dict) -> None:
    assert app.server_database_store_document_now(path, json.dumps(payload, ensure_ascii=False), authoritative=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="future-sqlite-only-") as temp:
        root = Path(temp)
        reset_database(root)

        inventory = app.inventory_path("codexsqlite")
        store(inventory, {"version": 1, "items": {"crystal": {"id": "crystal", "quantity": 2}}, "events": []})
        assert app.read_inventory_file("codexsqlite")["items"]["crystal"]["quantity"] == 2
        app.write_inventory_file("codexsqlite", {"items": {"crystal": {"id": "crystal", "quantity": 3}}})
        assert not inventory.exists()
        assert app.server_database_read_document_json(inventory, {})["items"]["crystal"]["quantity"] == 3

        app.VOCAB_LEADERBOARD_NPC_TOP_FILE = app.SERVER_DATA_ROOT / "_future_vocab_leaderboard_npc_top.json"
        app.VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE = {"stamp": (), "state": {}}
        store(app.VOCAB_LEADERBOARD_NPC_TOP_FILE, {"version": 1, "npcs": {"npc1": {"score": 9}}})
        assert app.load_vocab_leaderboard_npc_top_state()["npcs"]["npc1"]["score"] == 9
        app.write_vocab_leaderboard_npc_top_state({"npcs": {"npc1": {"score": 10}}})
        assert not app.VOCAB_LEADERBOARD_NPC_TOP_FILE.exists()

        app.VOCAB_LEADERBOARD_RANK_FILE = app.SERVER_DATA_ROOT / "_future_vocab_leaderboard_ranks.json"
        app.VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE = {"stamp": (), "state": None}
        store(app.VOCAB_LEADERBOARD_RANK_FILE, {"version": 1, "boards": {"total": {"ranks": {"codexsqlite": 1}}}})
        assert app.load_vocab_leaderboard_rank_state()["boards"]["total"]["ranks"]["codexsqlite"] == 1
        app.write_vocab_leaderboard_rank_state({"boards": {"total": {"ranks": {"codexsqlite": 2}}}})
        assert not app.VOCAB_LEADERBOARD_RANK_FILE.exists()

        user_file = app.user_file_path("codexsqlite")
        store(user_file, {"unused": True})
        app.server_database_store_document_now(user_file, "codexsqlite:hash\n", authoritative=True)
        app.server_database_upsert_user("codexsqlite", {"full_name": "Codex SQLite"})
        assert app.read_user_lines("codexsqlite") == ["codexsqlite:hash"]
        app.write_user_lines("codexsqlite", ["codexsqlite:hash2"])
        assert not user_file.exists()
        assert app.server_database_user_exists("codexsqlite")

        app.ADMINS_FILE = app.USER_ROOT / "_future_admins.json"
        store(app.ADMINS_FILE, {"admins": ["codexsqlite"]})
        app.ADMINS_RAM_CACHE = {"signature": None, "admins": set(), "checked_at": 0.0}
        assert "codexsqlite" in app.read_admins_locked()
        app.write_admins_locked({"codexsqlite"})
        assert not app.ADMINS_FILE.exists()

        app.SETTINGS_FILE = app.USER_ROOT / "_future_settings.json"
        store(app.SETTINGS_FILE, {"cpu_guard_enabled": True, "cpu_queue_threshold_percent": 88})
        assert app.load_server_settings()["cpu_queue_threshold_percent"] == 88
        app.save_server_settings({"cpu_queue_threshold_percent": 87})
        assert app.server_database_read_document_json(app.SETTINGS_FILE, {})["cpu_queue_threshold_percent"] == 87
        assert not app.SETTINGS_FILE.exists()

        lesson_time = app.lesson_time_path("codexsqlite")
        store(lesson_time, {"version": 1, "states": {"abc": {"seconds": 12}}})
        assert app.read_lesson_time_file("codexsqlite")["states"]["abc"]["seconds"] == 12
        app.write_lesson_time_file("codexsqlite", {"states": {"abc": {"seconds": 13}}})
        assert not lesson_time.exists()

        lesson_last = app.lesson_last_file_path("codexsqlite")
        store(lesson_last, {"version": 1, "file": {"path": "common/test.Space_V"}, "recentFiles": []})
        assert app.read_lesson_last_file_disk("codexsqlite")["file"]["path"] == "common/test.Space_V"
        assert not lesson_last.exists()

        app.LESSON_TASKS_FILE = app.SERVER_DATA_ROOT / "_future_lesson_tasks.json"
        store(app.LESSON_TASKS_FILE, {"version": 1, "by_user": {"codexsqlite": {"items": []}}})
        app.LESSON_TASKS_RAM_CACHE = {"store": None, "version": 0}
        assert "codexsqlite" in app.read_lesson_tasks_locked()["by_user"]
        assert not app.LESSON_TASKS_FILE.exists()

        app.CHAT_FILE = app.USER_ROOT / "_future_chat_messages.json"
        store(app.CHAT_FILE, {"messages": [{"id": "m1", "text": "hello"}]})
        app.CHAT_STATE_CACHE = {"state": None, "mtime_ns": -1, "dirty": False, "timer": None}
        assert app.load_chat_state_locked()["messages"][0]["id"] == "m1"
        assert not app.CHAT_FILE.exists()

        ai_history = app.ai_agent_history_path("codexsqlite")
        store(ai_history, {"version": 1, "history": [{"id": "a1", "title": "Test"}]})
        assert app.read_ai_agent_history("codexsqlite")["history"][0]["id"] == "a1"
        assert not ai_history.exists()

        app.SHARED_WORLD_FILE = app.SERVER_DATA_ROOT / "_future_shared_world.json"
        store(app.SHARED_WORLD_FILE, {"version": 1, "players": {"codexsqlite": {"x": 1}}})
        app.SHARED_WORLD_STATE_CACHE = {"state": None, "mtime": 0.0, "dirty": False, "last_flush": 0.0}
        assert app.load_shared_world_state()["players"]["codexsqlite"]["x"] == 1
        assert not app.SHARED_WORLD_FILE.exists()

        app.SPACE_PDF_DRAWINGS_FILE = app.SERVER_DATA_ROOT / "_future_space_pdf_drawings.json"
        store(app.SPACE_PDF_DRAWINGS_FILE, {"version": 1, "users": {"codexsqlite": {"doc": {}}}})
        app.SPACE_PDF_AI_JSON_STORE_CACHE.clear()
        assert "codexsqlite" in app._read_space_pdf_drawing_store_locked()["users"]
        assert not app.SPACE_PDF_DRAWINGS_FILE.exists()

        connection = app.server_database_connect()
        try:
            connection.execute(
                "INSERT INTO database_meta(key,value,updated_at_utc) VALUES('legacy_migration_v1','complete',?) "
                "ON CONFLICT(key) DO UPDATE SET value='complete',updated_at_utc=excluded.updated_at_utc",
                (app.utc_timestamp(),),
            )
        finally:
            connection.close()
        inventory.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text(json.dumps({"items": {"crystal": {"id": "crystal", "quantity": 999}}}), encoding="utf-8")
        app.migrate_server_database_from_legacy()
        assert app.server_database_read_document_json(inventory, {})["items"]["crystal"]["quantity"] == 3
        inventory.unlink()

        print("server_database_sqlite_only_documents=ok inventory=true npc_top=true rank=true users=true settings=true lesson_state=true chat_ai_world_pdf=true no_legacy_fallback=true physical_json=false")
        atexit.unregister(app.flush_auth_sessions_to_disk)
        app.SERVER_DATABASE_WRITE_QUEUE.put(None)
        app.SERVER_DATABASE_WRITE_QUEUE.join()
        time.sleep(0.05)


if __name__ == "__main__":
    main()
