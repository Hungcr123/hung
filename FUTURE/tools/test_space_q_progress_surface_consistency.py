"""Space_Q checkpoint position must not leak into completed-question progress."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def record(question_done: int) -> dict:
    return {
        "identity": "ftg-lesson-probe",
        "lesson_id": "ftg-lesson-probe",
        "path": "common/probe.Space_Q",
        "nodeIndex": 2,
        "nodeCount": 8,
        "activeRun": True,
        "runId": "space-q-probe-run",
        "savedAt": "2026-08-03T00:00:00Z",
        "updatedAt": "2026-08-03T00:00:01Z",
        "state": {
            "currentIndex": 2,
            "questionIndex": question_done,
            "questionDone": question_done,
            "questionTotal": 48,
            "completedNodes": 0,
            "totalNodes": 8,
            "activeRun": True,
            "runId": "space-q-probe-run",
        },
    }


def main() -> int:
    zero = record(0)
    zero_vault = app.space_progress_lesson_vault_study_patch(zero, "Space_Q")["progress"]
    zero_task = app.build_lesson_progress_summary(zero, "Space_Q", 48)
    assert (zero_vault["done"], zero_vault["total"], zero_vault["text"]) == (0, 48, "0/48")
    assert (zero_task["done"], zero_task["total"], zero_task["text"]) == (0, 48, "0/48")
    assert zero_vault["activeRun"] and zero_vault["in_progress"] and zero_vault["runId"] == "space-q-probe-run"
    assert zero_vault["nodes_text"] == "0/8"
    assert zero_task["nodes_text"] == "0/8"

    partial = record(2)
    partial_vault = app.space_progress_lesson_vault_study_patch(partial, "Space_Q")["progress"]
    partial_task = app.build_lesson_progress_summary(partial, "Space_Q", 48)
    assert (partial_vault["done"], partial_vault["total"]) == (2, 48)
    assert (partial_task["done"], partial_task["total"]) == (2, 48)
    print("space_q_progress_surface_consistency=ok checkpoint=2 progress_zero=0/48 partial=2/48")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
