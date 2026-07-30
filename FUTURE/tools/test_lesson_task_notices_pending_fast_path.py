"""Regression for task-notice reads that do not require lesson completion work."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original_reader = app.read_lesson_task_notices_locked
    original_pending = app.lesson_tasks_have_pending
    pending_calls = []

    def pending(target_user: str) -> bool:
        pending_calls.append(target_user)
        return False

    try:
        app.lesson_tasks_have_pending = pending
        app.read_lesson_task_notices_locked = lambda: {"by_user": {"hung": {"notices": []}}}
        assert app.lesson_task_notices_for_user("hung") == []
        assert pending_calls == []

        normal_notice = {"id": "normal", "text": "Hello", "mode": "always", "active": True}
        app.read_lesson_task_notices_locked = lambda: {"by_user": {"hung": {"notices": [normal_notice]}}}
        assert [row["id"] for row in app.lesson_task_notices_for_user("hung")] == ["normal"]
        assert pending_calls == []

        dependent_notice = {**normal_notice, "id": "dependent", "until_tasks_complete": True}
        app.read_lesson_task_notices_locked = lambda: {"by_user": {"hung": {"notices": [dependent_notice]}}}
        assert app.lesson_task_notices_for_user("hung") == []
        assert pending_calls == ["hung"]

        pending_calls.clear()
        assert [row["id"] for row in app.lesson_task_notices_for_user("hung", pending_tasks=True)] == ["dependent"]
        assert pending_calls == []
    finally:
        app.read_lesson_task_notices_locked = original_reader
        app.lesson_tasks_have_pending = original_pending

    print("lesson_task_notices_pending_fast_path=ok empty=skip independent=skip dependent=checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
