"""Verify task/notice cache revisions are isolated per user."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


def main() -> int:
    user_a = "codex_revision_a"
    user_b = "codex_revision_b"
    task_a_before = app.lesson_tasks_runtime_signature(user_a)
    task_b_before = app.lesson_tasks_runtime_signature(user_b)
    notice_a_before = app.lesson_task_notices_runtime_signature(user_a)
    notice_b_before = app.lesson_task_notices_runtime_signature(user_b)
    app.lesson_tasks_user_revision(user_a, bump=True)
    app.lesson_task_notices_user_revision(user_a, bump=True)
    assert app.lesson_tasks_runtime_signature(user_a) != task_a_before
    assert app.lesson_tasks_runtime_signature(user_b) == task_b_before
    assert app.lesson_task_notices_runtime_signature(user_a) != notice_a_before
    assert app.lesson_task_notices_runtime_signature(user_b) == notice_b_before
    manifest = {"updated_at": "revision-test", "signature": "revision-test"}
    list_b_before = app.server_data_list_cache_signature(manifest, study_user=user_b, task_owner=user_b, stats_user=user_b, viewer_user=user_b)
    app.lesson_tasks_user_revision(user_a, bump=True)
    app.lesson_task_notices_user_revision(user_a, bump=True)
    assert app.server_data_list_cache_signature(manifest, study_user=user_b, task_owner=user_b, stats_user=user_b, viewer_user=user_b) == list_b_before
    print("lesson_tasks_user_revision=ok task=true notice=true list_cache=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
