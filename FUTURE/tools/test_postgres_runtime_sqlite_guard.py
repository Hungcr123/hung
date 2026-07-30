"""Regression guard for PostgreSQL-only helpers that previously reached SQLite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["FUTURE_POSTGRES_ONLY"] = "1"
for _domain in (
    "APPEND_EVENTS", "AUTH", "INVENTORY", "LEADERBOARD_DOCUMENTS", "LEARNING_SUMMARY_DOCUMENTS",
    "LESSON_PROGRESS", "LESSON_TASK", "LESSON_TIME", "QM_CITY_DOCUMENTS", "QMDICT_DOCUMENTS",
    "USER_AUTH_DOCS", "USER_PREFERENCES", "VOCABULARY",
):
    os.environ[f"FUTURE_DB_{_domain}_BACKEND"] = "postgres"

from FUTURE import server_app as app
from FUTURE.postgres.repositories import inventory as pg_inventory
from FUTURE.postgres.repositories import lesson_identity as pg_lesson_identity
from FUTURE.postgres.repositories import lesson_time as pg_lesson_time
from FUTURE.postgres.repositories import vault as pg_vault
from FUTURE.postgres.repositories import vocabulary as pg_vocabulary


def main() -> int:
    runtime_sources = [ROOT / "FUTURE_SERVER_2.py", ROOT / "FUTURE/server_app.py"]
    runtime_sources.extend((ROOT / "FUTURE/server_parts").rglob("*.py"))
    runtime_sources.extend((ROOT / "FUTURE/postgres/repositories").rglob("*.py"))
    direct_connects = [
        str(path.relative_to(ROOT))
        for path in runtime_sources
        if "sqlite3.connect(" in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert not direct_connects, f"Runtime SQLite connectors remain: {direct_connects}"

    original_mode = app.postgres_backend_mode
    original_lesson_replace = pg_lesson_time.replace_lesson_time_payload
    original_inventory_replace = pg_inventory.replace_inventory_payload
    original_vault_resolve = pg_vault.resolved_source_path
    original_vault_load = pg_vault.load_cache_rows
    original_period_reset = pg_vocabulary.reset_periods
    calls = []

    try:
        app.postgres_backend_mode = lambda _domain="": "postgres"
        pg_lesson_time.replace_lesson_time_payload = lambda username, payload: calls.append(("lesson", username)) or True
        pg_inventory.replace_inventory_payload = lambda username, payload: calls.append(("inventory", username)) or True
        pg_vault.resolved_source_path = lambda replica_id, lesson_id="": calls.append(("resolve", int(replica_id))) or "common/a.Space_W"
        pg_vault.load_cache_rows = lambda username="": {
            "folders": [], "entries": [], "revisions": {}, "link_paths": [],
        }
        pg_vocabulary.reset_periods = lambda scopes: calls.append(("reset", tuple(scopes))) or {scope: 0 for scope in scopes}

        assert app.server_database_replace_lesson_time_payload("hung", {"states": {}})
        assert app.initialize_server_database().get("legacy_backend") == "retired"
        assert app.server_database_load_document_cache() == 0
        assert app.server_database_replace_inventory_payload("hung", {"items": {}, "events": []})
        assert app.server_database_vault_resolved_source_path({
            "lesson_id": "ftg-lesson-1", "physical_replica_id": 7, "source_path": "stale.Space_W",
        }) == "common/a.Space_W"
        assert app.server_database_vault_reload_cache() == 0
        assert app.server_database_reset_periods(["day", "week"]) == {"day": 0, "week": 0}
        app.SERVER_DATABASE_DOCUMENT_STATE["pending"] = {"retired.json": {"text": "{}", "encoding": "utf-8"}}
        app._flush_server_database_document_worker()
        assert app.SERVER_DATABASE_DOCUMENT_STATE["pending"] == {}
        app._server_database_writer_loop()
        assert not hasattr(pg_vault, "_sqlite_connect")
        assert not hasattr(pg_lesson_identity, "_sqlite_connect")
        for legacy_call in (app.restore_server_database_documents_to_legacy, app.audit_server_database_document_coverage, app.migrate_server_database_from_legacy):
            try:
                legacy_call()
            except RuntimeError as exc:
                assert "removed" in str(exc).lower()
            else:
                raise AssertionError("Legacy SQLite entry point remained enabled")
        assert calls == [
            ("lesson", "hung"),
            ("inventory", "hung"),
            ("resolve", 7),
            ("reset", ("day", "week")),
        ]
    finally:
        app.postgres_backend_mode = original_mode
        pg_lesson_time.replace_lesson_time_payload = original_lesson_replace
        pg_inventory.replace_inventory_payload = original_inventory_replace
        pg_vault.resolved_source_path = original_vault_resolve
        pg_vault.load_cache_rows = original_vault_load
        pg_vocabulary.reset_periods = original_period_reset

    print("postgres_runtime_sqlite_guard=ok routes=6 direct_connectors=0 migration_connectors_removed=2 sqlite_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
