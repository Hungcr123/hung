import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def record(saved_at: str, index: int, complete: bool = False) -> dict:
    state = {"savedAt": saved_at, "index": index, "nodeCount": 10}
    if complete:
        state.update({"complete": True, "completedAt": saved_at})
    return {
        "identity": "probe",
        "savedAt": saved_at,
        "nodeIndex": index,
        "nodeCount": 10,
        "complete": complete,
        "state": state,
    }


newer = record("2026-07-19T10:05:00Z", 7)
older = record("2026-07-19T10:00:00Z", 2)
picked = app.merge_space_progress_newest(newer, older, "Space_W")
assert picked["nodeIndex"] == 7
assert picked["savedAt"] == newer["savedAt"]

picked = app.merge_space_progress_newest(older, newer, "Space_Q")
assert picked["nodeIndex"] == 7
assert picked["savedAt"] == newer["savedAt"]

older_complete = record("2026-07-19T09:55:00Z", 9, complete=True)
picked = app.merge_space_progress_newest(newer, older_complete, "Space_P")
assert picked["nodeIndex"] == 7
assert picked["savedAt"] == newer["savedAt"]
assert picked.get("completedRuns", 0) >= 1

assert app.space_progress_clear_is_stale(newer, {"savedAt": older["savedAt"]}) is True
assert app.space_progress_clear_is_stale(older, {"savedAt": newer["savedAt"]}) is False

completed_v = {
    **record("2026-07-19T10:00:00Z", 10, complete=True),
    "learnedCount": 10,
    "completedRuns": 7,
    "state": {"savedAt": "2026-07-19T10:00:00Z", "learned": [str(i) for i in range(10)], "complete": True},
}
new_run_v = {
    **record("2026-07-19T10:05:00Z", 0, complete=False),
    "learnedCount": 0,
    "action": "new_run",
    "state": {"savedAt": "2026-07-19T10:05:00Z", "learned": [], "activeRun": True, "complete": False, "newRun": True},
}
picked = app.merge_space_v_progress_record(completed_v, new_run_v, True)
assert picked["nodeIndex"] == 0
assert picked["learnedCount"] == 0
assert picked.get("complete") is False
assert picked["state"]["activeRun"] is True
assert picked.get("completedRuns", 0) >= 7

new_run_same_id_late = {
    **new_run_v,
    "savedAt": "2026-07-19T10:06:00Z",
    "runId": "run-new",
    "state": {**new_run_v["state"], "savedAt": "2026-07-19T10:06:00Z", "runId": "run-new"},
}
same_run_answer = {
    **new_run_same_id_late,
    "learnedCount": 1,
    "state": {**new_run_same_id_late["state"], "learned": ["one"], "learnedCount": 1},
}
picked_same_run = app.merge_space_v_progress_record(same_run_answer, new_run_same_id_late, True)
assert picked_same_run["learnedCount"] == 1
assert picked_same_run["state"]["learned"] == ["one"]

stale_new_run = {
    **new_run_v,
    "savedAt": "2026-07-19T09:00:00Z",
    "runId": "run-stale-device",
    "state": {**new_run_v["state"], "savedAt": "2026-07-19T09:00:00Z", "runId": "run-stale-device"},
}
picked_stale_new_run = app.merge_space_v_progress_record(same_run_answer, stale_new_run, True)
assert picked_stale_new_run["runId"] == "run-new"
assert picked_stale_new_run["learnedCount"] == 1

contradictory_state = {"activeRun": True, "learned": [], "complete": True, "lessonComplete": True}
active_run, learned_count = app.normalize_space_v_active_run_state(
    {"activeRun": True, "learnedCount": 10, "complete": True},
    contradictory_state,
    10,
)
assert active_run is True
assert learned_count == 0
assert contradictory_state["complete"] is False
assert contradictory_state["lessonComplete"] is False

empty_active_state = {"activeRun": True, "learned": [], "learnedWords": [{"key": str(i)} for i in range(10)]}
active_run, learned_count = app.normalize_space_v_active_run_state(
    {"activeRun": True, "learnedCount": 0},
    empty_active_state,
    0,
)
assert active_run is True
assert learned_count == 0
assert empty_active_state["learnedWords"] == []

new_run_summary = app.build_lesson_progress_summary({
    **picked,
    "runId": "new-run-0",
    "activeRun": True,
    "completedRuns": 7,
    "state": {
        **picked["state"],
        "runId": "new-run-0",
        "activeRun": True,
        "learned": [],
    },
}, "Space_V", 10)
assert (new_run_summary["done"], new_run_summary["total"], new_run_summary["percent"]) == (0, 10, 0)
assert new_run_summary["completed"] is False
assert new_run_summary["previously_completed"] is True
hot_summary = app.space_v_progress_summary_from_record({
    **picked,
    "runId": "new-run-0",
    "activeRun": True,
    "completedRuns": 7,
    "state": {**picked["state"], "runId": "new-run-0", "activeRun": True, "learned": []},
})
assert (hot_summary["done"], hot_summary["total"], hot_summary["percent"]) == (0, 10, 0)
assert hot_summary["activeRun"] is True
assert hot_summary["runId"] == "new-run-0"
assert hot_summary["previously_completed"] is True
assert app.lesson_progress_active_run_overrides_completion(
    new_run_summary,
    "Space_V",
    10,
    "2026-07-19T17:30:00+07:00",
) is True

legacy_without_run_id = {**new_run_summary, "runId": "", "updatedAt": "2026-07-19T09:00:00Z"}
assert app.lesson_progress_active_run_overrides_completion(
    legacy_without_run_id,
    "Space_V",
    10,
    "2026-07-19T10:00:00Z",
) is False

print("progress_newest_smoke=ok cases=older,newer,completion-history,stale-clear,space-v-new-run,active-zero-chart")
