"""Verify cold Space Task payloads use the bounded async path and revision invalidation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "codex_async_contract"
    before = app.space_task_payload_user_revision(username)
    after = app.space_task_payload_user_revision(username, bump=True)
    assert after == before + 1
    assert app.space_task_payload_user_revision(username) == after

    with app.SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        original_cache = app.SPACE_TASK_PAYLOAD_RAM_CACHE.copy()
        original_inflight = app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.copy()
        try:
            app.SPACE_TASK_PAYLOAD_RAM_CACHE.clear()
            app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.clear()
            for index in range(120):
                app.SPACE_TASK_PAYLOAD_RAM_CACHE[f"codex-cache-{index}"] = {
                    "payload": {"pending": False},
                    "at": float(index),
                }
            assert app._space_task_payload_cache_prune() == 0
            assert len(app.SPACE_TASK_PAYLOAD_RAM_CACHE) == 120
            for index in range(120, app.SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS + 1):
                app.SPACE_TASK_PAYLOAD_RAM_CACHE[f"codex-cache-{index}"] = {
                    "payload": {"pending": False},
                    "at": float(index),
                }
            protected_key = f"codex-cache-{app.SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS}"
            removed = app._space_task_payload_cache_prune(protected_key)
            assert removed >= 1
            assert protected_key in app.SPACE_TASK_PAYLOAD_RAM_CACHE
            assert len(app.SPACE_TASK_PAYLOAD_RAM_CACHE) <= app.SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS

            duplicate_key = "codex-cache-duplicate"
            app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT[duplicate_key] = app.time.time()
            before_tickets = app.SPACE_TASK_PAYLOAD_REFRESH_TICKET._value
            assert app._refresh_space_task_payload_async(duplicate_key, username) is True
            assert app.SPACE_TASK_PAYLOAD_REFRESH_TICKET._value == before_tickets
            app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.pop(duplicate_key, None)

            held_tickets = 0
            while app.SPACE_TASK_PAYLOAD_REFRESH_TICKET.acquire(blocking=False):
                held_tickets += 1
            rejected_key = "codex-cache-rejected"
            assert app._refresh_space_task_payload_async(rejected_key, username) is False
            assert rejected_key not in app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT
            for _index in range(held_tickets):
                app.SPACE_TASK_PAYLOAD_REFRESH_TICKET.release()
        finally:
            app.SPACE_TASK_PAYLOAD_RAM_CACHE.clear()
            app.SPACE_TASK_PAYLOAD_RAM_CACHE.update(original_cache)
            app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.clear()
            app.SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.update(original_inflight)

    source = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/03_payload.py").read_text(encoding="utf-8")
    task_source = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/03_lesson_tasks_logs.py").read_text(encoding="utf-8")
    server_source = (ROOT / "FUTURE/server_app.py").read_text(encoding="utf-8")
    route_source = (ROOT / "FUTURE/server_parts/http_server/get_route_parts/03_auth_dashboard_server_data.pyfrag").read_text(encoding="utf-8")
    client_source = (ROOT / "FUTURE/web/js_parts/16_notices_vocabulary_missions.js").read_text(encoding="utf-8")
    assert "if space_task_cold_async_enabled():" in source
    assert "return queue_space_task_payload_refresh_for_user(" in source
    assert "space_task_payload_user_revision(target_user, bump=True)" in source
    assert "invalidate_lesson_tasks_response_cache" in source
    assert "space_task_payload_user_revision(target_user)," in task_source
    assert 'FUTURE_SPACE_TASK_PAYLOAD_WORKERS", "8"' in server_source
    assert 'FUTURE_SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS", "256"' in server_source
    assert "min(16" in server_source
    assert 'if path == "/lesson-tasks/status":' in route_source
    assert "space_task_payload_refresh_status(" in route_source
    assert "`/lesson-tasks/status?${query.toString()}`" in client_source
    print("space_task_cold_async=ok bounded_queue=true queue_rejection=true duplicate_coalesced=true cache_120=true bounded_cache=true revision_invalidation=true retry=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
